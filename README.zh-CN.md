# agent-meme-forge

把一个人或形象的参考图，生成一套能发、好笑、符合微信表情开放平台规格的动态 GIF 表情包。

核心 skill：`generate-meme-gif-pack`。

## 设计原则

没人用的表情包就是垃圾。这个项目优先解决“聊天里到底会不会发”：

- 每个 GIF 都必须有明确发送场景。
- 梗要短、能读、能复用。
- 图片模型不负责写中文，中文文案由本地脚本统一加字。
- 默认产出 24 个动态 GIF，因为微信动态表情专辑通常要求 16 或 24 个。

## 功能

- 从一张真人、头像、IP 形象或角色参考图生成风格化表情包。
- 可选风格：`clean-sticker`、`pixel-art`、`chibi`、`retro-msn`、`office-cartoon`、`hand-drawn`。
- 可选人设：`科研打工人`、`都市丽人`、`打工仔`、`码农`、`学生`、`研究僧`、`早八特困生`、`甲方幸存者`、`会议受害者`、`ddl祭司`。
- 自动规划 24 个表情：12 个高频聊天通用梗、8 个垂直人设梗、4 个补位万能梗。
- 导出：
  - `named-gifs/表情名.gif`
  - `wechat-submit/main/01.gif ... 24.gif`
  - `wechat-submit/thumbs/01.png ... 24.png`
  - `cover.png`、`icon.png`、`banner.png`
  - `manifest.json`、`manifest.csv`

## 安装

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

安装到 Codex skill 目录时，复制整个目录：

```bash
cp -R skills/generate-meme-gif-pack ~/.codex/skills/
```

重新打开 Codex session 后，skill 会出现在可用 skill 列表中。

## 使用

先准备一组无文字角色图或分镜图，放入一个目录，例如 `raw-frames/01.png ... 24.png`。这些图可以由 Codex `image_gen` 根据 skill 的 prompt 规则生成。

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-pack \
  --source-dir raw-frames \
  --output-dir output/my-pack \
  --persona 科研打工人 \
  --style clean-sticker \
  --pack-size 24 \
  --mode wechat \
  --pack-name 我的表情包
```

列出可用选项：

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py list-options
```

写出默认梗条目：

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py write-default-entries \
  --persona 码农 \
  --pack-size 24 \
  --output entries.json
```

## 微信规格默认值

- 主图 GIF：`240x240`，小于 `500KB`，默认目标小于 `480KB`。
- 缩略图 PNG：`120x120`，小于 `50KB`。
- 图标 PNG：`50x50`，透明背景，小于 `30KB`。
- 封面 PNG：`240x240`，透明背景，小于 `80KB`。
- 横幅 PNG：`750x400`，小于 `80KB`，不放文字。

具体以微信表情开放平台当前官方说明为准。

## 开发验证

```bash
. .venv/bin/activate
pytest -q
```

当前测试覆盖：微信数量约束、默认梗库、中文文案排版、完整投稿包结构、skill 文档和 reference 文件完整性。

## 肖像和审核

如果参考图是真人，请确保拥有本人授权或合法使用权。默认策略是“风格化但像本人”，不是高仿真人换脸。公开发布时应避开政治、低俗、攻击性、侵权角色和高审核风险内容。
