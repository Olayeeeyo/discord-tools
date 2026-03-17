#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord Channel Exporter
导出 Discord 频道/论坛帖子为 JSON 格式
"""

import asyncio
import json
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Any
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


def get_env(key, default=None):
    """获取环境变量"""
    return os.environ.get(key, default)


class DiscordExporter:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        self.base_url = 'https://discord.com/api/v10'

    async def get_channel_info(self, session, channel_id):
        """获取频道信息"""
        url = f'{self.base_url}/channels/{channel_id}'
        async with session.get(url, headers=self.headers) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                error = await resp.text()
                raise Exception(f'Failed to get channel info: {resp.status} - {error}')

    async def get_messages(self, session, channel_id, limit=100, before=None):
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

    async def get_active_threads(self, session, guild_id):
        """获取服务器活跃线程列表"""
        url = f'{self.base_url}/guilds/{guild_id}/threads/active'
        async with session.get(url, headers=self.headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get('threads', [])
            else:
                return []

    async def get_archived_threads(self, session, channel_id):
        """获取频道归档线程（帖子）"""
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

    async def export_channel(self, channel_id, message_limit=1000, days=30, output_file=None):
        """导出频道"""
        async with aiohttp.ClientSession() as session:
            print(f'[INFO] Getting channel info...', flush=True)
            channel_info = await self.get_channel_info(session, channel_id)
            channel_name = channel_info.get('name', 'Unknown')
            channel_type = channel_info.get('type', 0)
            guild_id = channel_info.get('guild_id')

            print(f'[INFO] Channel: {channel_name} (Type: {channel_type})', flush=True)

            # Type 15 = GUILD_FORUM (论坛频道)
            if channel_type == 15:
                print(f'[INFO] Forum channel detected, fetching threads...', flush=True)
                return await self.export_forum_channel(
                    session, channel_id, guild_id, channel_name,
                    channel_info, days, output_file
                )

            # 普通文字频道
            after_date = datetime.now() - timedelta(days=days)
            print(f'[INFO] Fetching messages (limit: {message_limit}, days: {days})...', flush=True)

            all_messages = []
            last_id = None

            while len(all_messages) < message_limit:
                messages = await self.get_messages(
                    session, channel_id,
                    limit=min(100, message_limit - len(all_messages)),
                    before=last_id
                )

                if not messages:
                    break

                filtered = []
                for msg in messages:
                    msg_time = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                    if msg_time.replace(tzinfo=None) < after_date.replace(tzinfo=None):
                        break
                    filtered.append(msg)

                all_messages.extend(filtered)
                last_id = messages[-1]['id']

                if len(filtered) < len(messages):
                    break

                print(f'[INFO] Fetched {len(all_messages)} messages...', flush=True)
                await asyncio.sleep(0.5)

            print(f'[INFO] Total messages: {len(all_messages)}', flush=True)

            processed = self.process_messages(all_messages)

            result = {
                'channel': {
                    'id': channel_id,
                    'name': channel_name,
                    'guild_id': guild_id,
                    'topic': channel_info.get('topic'),
                    'type': channel_type
                },
                'export_info': {
                    'exported_at': datetime.now().isoformat(),
                    'message_count': len(all_messages),
                    'days_back': days
                },
                'messages': processed['messages'],
                'hot_posts': processed['hot_posts']
            }

            if output_file is None:
                output_file = f'discord_channel_{channel_id}_export.json'

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            print(f'[DONE] Export completed!', flush=True)
            print(f'[DONE] File saved: {os.path.abspath(output_file)}', flush=True)
            print(f'[DONE] Total messages: {len(all_messages)}', flush=True)
            print(f'[DONE] Hot posts: {len(processed["hot_posts"])}', flush=True)

            return result

    async def export_forum_channel(self, session, channel_id, guild_id, channel_name,
                                   channel_info, days, output_file):
        """导出论坛频道"""
        after_date = datetime.now() - timedelta(days=days)

        # 获取活跃帖子
        print(f'[INFO] Fetching active threads...', flush=True)
        active_threads = await self.get_active_threads(session, guild_id)
        active_threads = [t for t in active_threads if t.get('parent_id') == channel_id]

        # 获取归档帖子
        print(f'[INFO] Fetching archived threads...', flush=True)
        archived_threads = await self.get_archived_threads(session, channel_id)

        # 合并去重
        all_threads = active_threads + archived_threads
        seen_ids = set()
        unique_threads = []
        for t in all_threads:
            if t['id'] not in seen_ids:
                seen_ids.add(t['id'])
                unique_threads.append(t)

        print(f'[INFO] Found {len(unique_threads)} unique threads', flush=True)

        # 获取每个帖子的消息
        print(f'[INFO] Fetching messages from each thread...', flush=True)
        messages_by_thread = {}

        for i, thread in enumerate(unique_threads):
            thread_id = thread['id']

            # 检查创建时间
            thread_created = thread.get('thread_metadata', {}).get('create_timestamp')
            if thread_created:
                thread_time = datetime.fromisoformat(thread_created.replace('Z', '+00:00'))
                if thread_time.replace(tzinfo=None) < after_date.replace(tzinfo=None):
                    continue

            messages = await self.get_messages(session, thread_id, limit=100)
            messages_by_thread[thread_id] = messages

            if (i + 1) % 10 == 0:
                print(f'[INFO] Processed {i + 1}/{len(unique_threads)} threads...', flush=True)

            await asyncio.sleep(0.3)

        # 处理帖子数据
        processed = self.process_forum_posts(unique_threads, messages_by_thread)

        result = {
            'channel': {
                'id': channel_id,
                'name': channel_name,
                'guild_id': guild_id,
                'type': 15,
                'topic': channel_info.get('topic'),
            },
            'export_info': {
                'exported_at': datetime.now().isoformat(),
                'total_threads': len(unique_threads),
                'threads_with_messages': len([t for t in messages_by_thread.values() if t]),
                'days_back': days
            },
            'threads': processed['posts'],
            'hot_posts': processed['hot_posts']
        }

        if output_file is None:
            output_file = f'discord_forum_{channel_id}_export.json'

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f'[DONE] Export completed!', flush=True)
        print(f'[DONE] File saved: {os.path.abspath(output_file)}', flush=True)
        print(f'[DONE] Total threads: {len(unique_threads)}', flush=True)
        print(f'[DONE] Hot posts: {len(processed["hot_posts"])}', flush=True)

        return result

    def process_messages(self, messages):
        """处理消息"""
        processed = []
        hot_posts = []

        for msg in messages:
            processed_msg = {
                'id': msg['id'],
                'content': msg['content'],
                'author': {
                    'id': msg['author']['id'],
                    'username': msg['author']['username'],
                    'display_name': msg['author'].get('global_name'),
                },
                'timestamp': msg['timestamp'],
                'edited_timestamp': msg.get('edited_timestamp'),
                'attachments': [{
                    'id': a['id'],
                    'filename': a['filename'],
                    'url': a['url'],
                    'size': a['size']
                } for a in msg.get('attachments', [])],
                'embeds': msg.get('embeds', []),
                'reactions': [{
                    'emoji': r['emoji']['name'] if not r['emoji'].get('id') else f'<:{r["emoji"]["name"]}:{r["emoji"]["id"]}>',
                    'count': r['count']
                } for r in msg.get('reactions', [])],
                'total_reactions': sum(r['count'] for r in msg.get('reactions', [])),
                'mentions': len(msg.get('mentions', [])),
                'pinned': msg.get('pinned', False),
                'reference': msg.get('message_reference'),
            }

            processed.append(processed_msg)

            if (processed_msg['total_reactions'] >= 5 or
                len(processed_msg['attachments']) > 0 or
                processed_msg['pinned']):
                hot_posts.append(processed_msg)

        hot_posts.sort(key=lambda x: x['total_reactions'], reverse=True)

        return {
            'messages': processed,
            'hot_posts': hot_posts[:50]
        }

    def process_forum_posts(self, threads, messages_by_thread):
        """处理论坛帖子"""
        processed_posts = []
        hot_posts = []

        for thread in threads:
            thread_id = thread['id']
            messages = messages_by_thread.get(thread_id, [])

            message_count = thread.get('message_count', len(messages))

            total_reactions = 0
            for msg in messages:
                total_reactions += sum(r.get('count', 0) for r in msg.get('reactions', []))

            first_message = messages[0] if messages else None
            content = first_message.get('content', '') if first_message else thread.get('name', '')

            post = {
                'id': thread_id,
                'name': thread.get('name', ''),
                'content': content,
                'author': {
                    'id': thread['owner_id'],
                    'username': 'Unknown'
                },
                'created_at': thread.get('thread_metadata', {}).get('create_timestamp'),
                'archived': thread.get('thread_metadata', {}).get('archived', False),
                'message_count': message_count,
                'total_reactions': total_reactions,
                'tags': thread.get('applied_tags', []),
                'last_message_id': thread.get('last_message_id'),
                'messages': messages
            }

            processed_posts.append(post)

            if (message_count >= 10 or total_reactions >= 5 or thread.get('pinned', False)):
                hot_posts.append(post)

        hot_posts.sort(key=lambda x: (x['message_count'], x['total_reactions']), reverse=True)

        return {
            'posts': processed_posts,
            'hot_posts': hot_posts[:50]
        }


def load_config():
    """加载配置（优先从环境变量，其次从 config.json）"""
    config = {}

    # 先加载 .env 文件
    load_env_file()

    # 尝试加载 config.json
    config_path = 'config.json'
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

    # 环境变量覆盖配置文件
    if os.environ.get('DISCORD_TOKEN'):
        config['token'] = os.environ.get('DISCORD_TOKEN')
    if os.environ.get('DEFAULT_CHANNEL'):
        config['default_channel'] = os.environ.get('DEFAULT_CHANNEL')

    return config


def save_config(config):
    """保存配置文件"""
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Discord Channel Exporter')
    parser.add_argument('-c', '--channel', help='Channel ID')
    parser.add_argument('-l', '--limit', type=int, default=1000, help='Max messages (for text channels)')
    parser.add_argument('-d', '--days', type=int, default=30, help='Days back')
    parser.add_argument('-o', '--output', help='Output file')
    parser.add_argument('--save-token', action='store_true', help='Save token to config')
    args = parser.parse_args()

    # 加载配置
    config = load_config()

    # 获取 token
    token = config.get('token')
    if not token:
        print('[ERROR] Token not found')
        print('[INFO] Please create a .env file with:')
        print('  DISCORD_TOKEN=your-token-here')
        print('  DEFAULT_CHANNEL=your-channel-id')
        sys.exit(1)

    # 获取频道 ID
    channel_id = args.channel or config.get('default_channel')
    if not channel_id:
        print('[ERROR] Channel ID not specified')
        print('[INFO] Use -c CHANNEL_ID or set default_channel in config.json')
        sys.exit(1)

    exporter = DiscordExporter(token)
    try:
        asyncio.run(exporter.export_channel(
            channel_id=channel_id,
            message_limit=args.limit,
            days=args.days,
            output_file=args.output
        ))
    except Exception as e:
        print(f'[ERROR] {e}', flush=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
