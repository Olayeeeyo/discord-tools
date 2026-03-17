#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord Preset Downloader
从 Discord 热帖中下载预设 JSON 和正则表达式文件
"""

import asyncio
import json
import aiohttp
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple
import sys
import os


def load_env_file():
    """加载 .env 文件"""
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value


def sanitize_filename(name: str) -> str:
    """清理文件名，移除非法字符"""
    # 移除或替换 Windows 不允许的字符
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # 限制长度
    if len(name) > 100:
        name = name[:100]
    return name.strip()


def categorize_attachment(filename: str) -> str:
    """
    识别附件类型
    Returns: 'preset', 'regex', 'image', 'other'
    """
    filename_lower = filename.lower()

    # 预设文件特征
    preset_keywords = ['preset', 'char', 'character', 'persona', 'setting', '设定', '预设', '角色']
    if any(kw in filename_lower for kw in preset_keywords):
        return 'preset'

    # 正则文件特征
    regex_keywords = ['regex', 'regexp', '正則', '正则', '替换', 'replace', 'script']
    if any(kw in filename_lower for kw in regex_keywords):
        return 'regex'

    # 图片文件
    image_exts = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']
    if any(filename_lower.endswith(ext) for ext in image_exts):
        return 'image'

    # 尝试通过 JSON 内容判断（下载后）
    if filename_lower.endswith('.json'):
        return 'json_unknown'

    return 'other'


class PresetDownloader:
    def __init__(self, token: str, output_dir: str = "downloads"):
        self.token = token
        self.headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        self.base_url = 'https://discord.com/api/v10'
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # 统计
        self.stats = {
            'threads_processed': 0,
            'attachments_found': 0,
            'attachments_downloaded': 0,
            'presets_found': 0,
            'regex_found': 0,
            'errors': []
        }

    async def get_channel_info(self, session, channel_id: str) -> Dict:
        """获取频道信息"""
        url = f'{self.base_url}/channels/{channel_id}'
        async with session.get(url, headers=self.headers) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                error = await resp.text()
                raise Exception(f'Failed to get channel info: {resp.status} - {error}')

    async def get_messages(self, session, channel_id: str, limit: int = 100, before: str = None) -> List[Dict]:
        """获取频道消息"""
        url = f'{self.base_url}/channels/{channel_id}/messages'
        params = {'limit': min(limit, 100)}
        if before:
            params['before'] = before

        async with session.get(url, headers=self.headers, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                error = await resp.text()
                raise Exception(f'Failed to get messages: {resp.status} - {error}')

    async def get_active_threads(self, session, guild_id: str) -> List[Dict]:
        """获取活跃帖子"""
        url = f'{self.base_url}/guilds/{guild_id}/threads/active'
        async with session.get(url, headers=self.headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get('threads', [])
            return []

    async def get_archived_threads(self, session, channel_id: str) -> List[Dict]:
        """获取归档帖子"""
        url = f'{self.base_url}/channels/{channel_id}/threads/archived/public'
        all_threads = []
        before = None

        while True:
            params = {'limit': 100}
            if before:
                params['before'] = before

            async with session.get(url, headers=self.headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    threads = data.get('threads', [])
                    all_threads.extend(threads)

                    if not data.get('has_more'):
                        break

                    if threads:
                        before = threads[-1]['thread_metadata']['archive_timestamp']
                else:
                    break

            await asyncio.sleep(0.5)

        return all_threads

    async def download_attachment(self, session, url: str, filepath: Path) -> bool:
        """下载附件"""
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    with open(filepath, 'wb') as f:
                        f.write(await resp.read())
                    return True
                else:
                    self.stats['errors'].append(f'Download failed {resp.status}: {url}')
                    return False
        except Exception as e:
            self.stats['errors'].append(f'Download error: {str(e)}')
            return False

    async def analyze_json_content(self, session, url: str) -> str:
        """分析 JSON 文件内容，判断是 preset 还是 regex"""
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    data = json.loads(content)

                    # 预设文件特征
                    preset_keys = ['name', 'description', 'personality', 'first_mes', 'mes_example', 'char_persona']
                    if any(key in data for key in preset_keys):
                        return 'preset'

                    # 正则文件特征
                    regex_keys = ['regex', 'replace', 'pattern', 'scripts', 'substitutions']
                    if any(key in data for key in regex_keys):
                        return 'regex'

                    return 'unknown'
        except:
            pass
        return 'unknown'

    async def process_hot_threads(self, channel_id: str, days: int = 90, min_reactions: int = 5, min_messages: int = 10):
        """处理热帖并下载附件"""
        async with aiohttp.ClientSession() as session:
            print(f'[INFO] Getting channel info...')
            channel_info = await self.get_channel_info(session, channel_id)
            channel_name = channel_info.get('name', 'Unknown')
            guild_id = channel_info.get('guild_id')

            print(f'[INFO] Channel: {channel_name}')

            if channel_info.get('type') != 15:
                print('[ERROR] This tool is designed for forum channels only')
                return

            after_date = datetime.now() - timedelta(days=days)

            # 获取所有帖子
            print(f'[INFO] Fetching threads...')
            active_threads = await self.get_active_threads(session, guild_id)
            active_threads = [t for t in active_threads if t.get('parent_id') == channel_id]

            archived_threads = await self.get_archived_threads(session, channel_id)

            # 合并去重
            all_threads = active_threads + archived_threads
            seen_ids = set()
            unique_threads = []
            for t in all_threads:
                if t['id'] not in seen_ids:
                    seen_ids.add(t['id'])
                    unique_threads.append(t)

            print(f'[INFO] Found {len(unique_threads)} threads total')

            # 筛选热帖
            hot_threads = []
            for thread in unique_threads:
                # 检查创建时间
                thread_created = thread.get('thread_metadata', {}).get('create_timestamp')
                if thread_created:
                    thread_time = datetime.fromisoformat(thread_created.replace('Z', '+00:00'))
                    if thread_time.replace(tzinfo=None) < after_date.replace(tzinfo=None):
                        continue

                # 获取消息统计
                message_count = thread.get('message_count', 0)
                total_reactions = 0

                # 简化的热度判断
                if message_count >= min_messages or thread.get('pinned'):
                    hot_threads.append({
                        'thread': thread,
                        'message_count': message_count,
                        'total_reactions': total_reactions
                    })

            print(f'[INFO] Found {len(hot_threads)} hot threads')

            # 处理每个热帖
            for idx, hot_thread in enumerate(hot_threads, 1):
                thread = hot_thread['thread']
                thread_id = thread['id']
                thread_name = thread.get('name', 'Unknown')

                print(f'\n[{idx}/{len(hot_threads)}] Processing: {thread_name}')

                # 创建目录
                created_time = thread.get('thread_metadata', {}).get('create_timestamp', '')
                date_prefix = ''
                if created_time:
                    try:
                        dt = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                        date_prefix = dt.strftime('%Y%m%d') + '_'
                    except:
                        pass

                safe_name = sanitize_filename(thread_name)
                thread_dir = self.output_dir / f"{date_prefix}{safe_name}"
                thread_dir.mkdir(exist_ok=True)

                # 获取帖子消息
                messages = await self.get_messages(session, thread_id, limit=100)

                # 收集所有附件
                all_attachments = []
                first_message_content = ""

                for msg_idx, msg in enumerate(messages):
                    # 保存首条消息内容（说明）
                    if msg_idx == 0:
                        first_message_content = msg.get('content', '')

                    # 收集附件
                    for attachment in msg.get('attachments', []):
                        all_attachments.append({
                            'id': attachment['id'],
                            'filename': attachment['filename'],
                            'url': attachment['url'],
                            'size': attachment['size'],
                            'message_id': msg['id']
                        })

                self.stats['attachments_found'] += len(all_attachments)

                if not all_attachments:
                    print(f'  No attachments found')
                    continue

                print(f'  Found {len(all_attachments)} attachments')

                # 下载附件
                attachments_info = []

                for att in all_attachments:
                    # 识别文件类型
                    file_type = categorize_attachment(att['filename'])

                    # 如果是未知 JSON，下载后分析
                    if file_type == 'json_unknown':
                        print(f'  Analyzing JSON: {att["filename"]}')
                        detected_type = await self.analyze_json_content(session, att['url'])
                        if detected_type != 'unknown':
                            file_type = detected_type

                    # 确定保存路径
                    if file_type == 'preset':
                        save_dir = thread_dir / 'preset'
                        self.stats['presets_found'] += 1
                    elif file_type == 'regex':
                        save_dir = thread_dir / 'regex'
                        self.stats['regex_found'] += 1
                    elif file_type == 'image':
                        save_dir = thread_dir / 'images'
                    else:
                        save_dir = thread_dir / 'attachments'

                    save_dir.mkdir(exist_ok=True)
                    filepath = save_dir / att['filename']

                    # 下载
                    print(f'  Downloading: {att["filename"]} ({att["size"]} bytes) -> {file_type}')
                    success = await self.download_attachment(session, att['url'], filepath)

                    if success:
                        self.stats['attachments_downloaded'] += 1
                        attachments_info.append({
                            'filename': att['filename'],
                            'type': file_type,
                            'size': att['size'],
                            'downloaded': True
                        })
                    else:
                        attachments_info.append({
                            'filename': att['filename'],
                            'type': file_type,
                            'size': att['size'],
                            'downloaded': False
                        })

                # 保存元数据
                metadata = {
                    'thread_id': thread_id,
                    'thread_name': thread_name,
                    'created_at': thread.get('thread_metadata', {}).get('create_timestamp'),
                    'message_count': hot_thread['message_count'],
                    'total_reactions': hot_thread['total_reactions'],
                    'author_id': thread.get('owner_id'),
                    'first_message': first_message_content,
                    'attachments': attachments_info
                }

                with open(thread_dir / 'metadata.json', 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)

                # 保存说明为文本文件（便于阅读）
                if first_message_content:
                    with open(thread_dir / 'description.txt', 'w', encoding='utf-8') as f:
                        f.write(f"标题: {thread_name}\n")
                        f.write(f"帖子ID: {thread_id}\n")
                        f.write(f"消息数: {hot_thread['message_count']}\n")
                        f.write("=" * 50 + "\n\n")
                        f.write(first_message_content)

                self.stats['threads_processed'] += 1
                await asyncio.sleep(0.5)

            # 打印统计
            print("\n" + "=" * 50)
            print("下载完成！")
            print(f"处理帖子数: {self.stats['threads_processed']}")
            print(f"发现附件数: {self.stats['attachments_found']}")
            print(f"下载成功: {self.stats['attachments_downloaded']}")
            print(f"预设文件: {self.stats['presets_found']}")
            print(f"正则文件: {self.stats['regex_found']}")
            print(f"输出目录: {self.output_dir.absolute()}")

            if self.stats['errors']:
                print(f"\n错误 ({len(self.stats['errors'])}):")
                for err in self.stats['errors'][:5]:
                    print(f"  - {err}")


def load_config():
    """加载配置"""
    load_env_file()

    config = {}
    if os.path.exists('config.json'):
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)

    if os.environ.get('DISCORD_TOKEN'):
        config['token'] = os.environ.get('DISCORD_TOKEN')
    if os.environ.get('DEFAULT_CHANNEL'):
        config['default_channel'] = os.environ.get('DEFAULT_CHANNEL')

    return config


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Discord Preset Downloader')
    parser.add_argument('-c', '--channel', help='Channel ID')
    parser.add_argument('-d', '--days', type=int, default=90, help='Days back')
    parser.add_argument('-o', '--output', default='downloads', help='Output directory')
    parser.add_argument('--min-reactions', type=int, default=5, help='Minimum reactions for hot post')
    parser.add_argument('--min-messages', type=int, default=10, help='Minimum messages for hot post')
    args = parser.parse_args()

    config = load_config()

    token = config.get('token')
    if not token:
        print('[ERROR] Token not found in .env')
        print('[INFO] Create .env file with: DISCORD_TOKEN=your-token')
        sys.exit(1)

    channel_id = args.channel or config.get('default_channel')
    if not channel_id:
        print('[ERROR] Channel ID not specified')
        sys.exit(1)

    downloader = PresetDownloader(token, output_dir=args.output)

    try:
        asyncio.run(downloader.process_hot_threads(
            channel_id=channel_id,
            days=args.days,
            min_reactions=args.min_reactions,
            min_messages=args.min_messages
        ))
    except Exception as e:
        print(f'[ERROR] {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
