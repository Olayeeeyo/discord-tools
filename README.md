# Discord Channel Exporter

Discord 频道导出工具，支持导出消息和下载热帖附件。

## 功能

### 1. exporter.py - 频道导出器
- 普通文字频道消息导出
- 论坛频道帖子导出
- 热帖筛选（按消息数/反应数/置顶状态）
- JSON 格式输出

### 2. preset_downloader.py - 预设下载器 ⭐
- 从热帖中自动下载附件
- 智能识别预设 JSON 和正则表达式文件
- 按帖子组织目录结构
- 保存帖子说明和元数据

## 安装

```bash
pip install -r requirements.txt
```

## 配置

创建 `.env` 文件：

```
DISCORD_TOKEN=your-discord-token
DEFAULT_CHANNEL=1134822069222264874
```

**获取 Token**：
1. Discord 桌面端按 `Ctrl+Shift+I` 打开开发者工具
2. Network 标签 → 刷新 → 任意请求 → Headers → `authorization`
3. 或 Application → Local Storage → `token` 字段

## 使用

### 导出频道消息

```bash
# 导出最近 90 天的热帖
python exporter.py -d 90
```

### 下载热帖附件 ⭐

```bash
# 下载热帖中的预设和正则文件
python preset_downloader.py -d 90 -o downloads

# 只下载高热度帖子（消息数 >= 50）
python preset_downloader.py --min-messages 50 -d 180
```

## 输出目录结构

```
downloads/
├── 20231115_一个简单的chatgpt提示词破限/
│   ├── metadata.json          # 帖子元数据（ID、标题、作者等）
│   ├── description.txt        # 首条消息说明
│   ├── preset/                # 预设 JSON 文件
│   │   └── character.json
│   ├── regex/                 # 正则表达式文件
│   │   └── replacement.json
│   ├── images/                # 图片附件
│   └── attachments/           # 其他附件
│
├── 20240725_拾梦-女性向预设/
│   ├── metadata.json
│   ├── description.txt
│   ├── preset/
│   └── regex/
│
└── ...
```

### metadata.json 结构

```json
{
  "thread_id": "123456789",
  "thread_name": "预设标题",
  "created_at": "2024-01-01T00:00:00.000000+00:00",
  "message_count": 150,
  "total_reactions": 45,
  "author_id": "987654321",
  "first_message": "这里是帖子的首条消息内容，包含详细说明...",
  "attachments": [
    {
      "filename": "preset.json",
      "type": "preset",
      "size": 12345,
      "downloaded": true
    }
  ]
}
```

## 附件识别规则

### 预设文件 (preset/)
文件名包含关键词：
- `preset`, `char`, `character`, `persona`, `setting`
- `设定`, `预设`, `角色`

或 JSON 内容包含：`name`, `description`, `personality`, `first_mes`, `mes_example`

### 正则文件 (regex/)
文件名包含关键词：
- `regex`, `regexp`, `正則`, `正则`, `替换`, `replace`, `script`

或 JSON 内容包含：`regex`, `replace`, `pattern`, `scripts`, `substitutions`

### 图片文件 (images/)
扩展名：`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp`

## 参数说明

### preset_downloader.py

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-c, --channel` | 频道 ID | .env 中的 DEFAULT_CHANNEL |
| `-d, --days` | 导出最近 N 天的帖子 | 90 |
| `-o, --output` | 输出目录 | downloads |
| `--min-messages` | 热帖最小消息数 | 10 |
| `--min-reactions` | 热帖最小反应数 | 5 |

## 注意事项

- `.env` 文件包含敏感信息，不会被提交到 Git
- 下载速度受 Discord API 速率限制影响
- 论坛频道会获取每个帖子的最近 100 条消息来查找附件
- 建议使用 `--min-messages` 筛选高质量帖子

## License

MIT
