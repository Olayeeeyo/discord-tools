# Discord Channel Exporter

导出 Discord 频道/论坛帖子为 JSON 格式，支持筛选热帖。

## 功能

- 支持普通文字频道导出
- 支持论坛频道（Forum）帖子导出
- 自动筛选热帖（按消息数/反应数/置顶状态）
- 导出为 JSON 格式，包含完整消息内容

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

```bash
# 使用 .env 中的配置导出
python exporter.py

# 指定频道
python exporter.py -c 1134822069222264874

# 导出最近 60 天的帖子
python exporter.py -d 60

# 指定输出文件
python exporter.py -o my_export.json
```

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-c, --channel` | 频道 ID | .env 中的 DEFAULT_CHANNEL |
| `-d, --days` | 导出最近 N 天 | 30 |
| `-l, --limit` | 消息数量限制（文字频道）| 1000 |
| `-o, --output` | 输出文件名 | 自动生成 |

## 输出格式

```json
{
  "channel": { ... },
  "export_info": { ... },
  "threads": [ ... ],
  "hot_posts": [ ... ]
}
```

- `threads` - 所有帖子
- `hot_posts` - 热帖筛选结果

## 热帖判定标准

- 消息数 ≥ 10
- 或 反应数 ≥ 5
- 或 置顶帖子

## 注意事项

- `.env` 文件包含敏感信息，不会被提交到 Git
- Token 具有账号权限，请勿分享给他人
- 导出速度受 Discord API 速率限制影响
- 论坛频道会获取每个帖子的最近 100 条消息

## License

MIT
