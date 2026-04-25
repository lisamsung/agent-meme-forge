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

- 从一张真人、头像、IP 形象、角色参考图，或纯文字角色概念生成风格化表情包。
- 先生成角色卡、梗条目和逐条 `image_gen` 动作 sheet 提示词，再用本地脚本统一加中文、做 GIF 和微信打包。
- 默认高质量路径是每个表情一张 `1x4` motion sheet，处理器按真实动作帧输出 GIF；单张静态图只作为快速预览 fallback。
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
mkdir -p ~/.codex-switcher/skills
cp -R skills/generate-meme-gif-pack ~/.codex-switcher/skills/
```

重新打开 Codex session 后，skill 会出现在可用 skill 列表中。

## 使用

### 1. 先生成计划和 image_gen 提示词

有参考图时，把参考图路径放到 `--reference-image`，并用 `--subject` 描述关键特征。

没有参考图时，也可以直接用文字概念生成，例如做一个 Claude 气质启发、但不复制官方标识的原创 AI 吉祥物：

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py plan-pack \
  --subject "warm geometric AI assistant mascot with cream body and coral accents, friendly abstract face, tiny paper-stack anxiety, original character, no official logo" \
  --persona 科研打工人 \
  --style clean-sticker \
  --pack-size 24 \
  --mode wechat \
  --pack-name AI科研打工搭子 \
  --animation-layout 1x4 \
  --output output/ai-research-plan.json
```

打开 `output/ai-research-plan.json`，里面会有：

- `character_card`：角色设定卡。
- `items`：24 个表情名、文案、关键词、发送场景。
- `animation`：默认 `1x4`，每个表情 4 个动作帧。
- `image_prompts`：24 条可直接交给 Codex `image_gen` 的无文字动作 sheet 提示词。

### 2. 调用 image_gen 生成无文字原图

把每条 `image_prompts[].prompt` 交给 Codex 内置 `image_gen`。默认会要求生成一张 `1x4` 动作 sheet，例如 `raw-frames/01-收到离线-1x4.png ... 24-你说得对-1x4.png`。

质量不行就重生：角色太小、画了文字、像官方 logo、表情不够强、道具太细、看不出发送场景、网格数量不对、前后帧角色比例乱跳、道具出格，都应该退回。

如果为了快速试效果，先让 `image_gen` 生成一张 `4x6` 静态 contact sheet，可以切成 24 张单姿态原图。注意这只是预览路径，最终质量不如每个表情单独 `1x4` motion sheet：

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py split-sheet \
  --input output/raw-sheets/ai-research-sheet.png \
  --output-dir raw-frames \
  --rows 6 \
  --cols 4
```

### 3. 构建微信 GIF 包

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-pack \
  --source-dir raw-frames \
  --output-dir output/my-pack \
  --persona 科研打工人 \
  --style clean-sticker \
  --pack-size 24 \
  --mode wechat \
  --pack-name 我的表情包 \
  --source-layout 1x4
```

如果你只有单张静态姿态图，可以把 `--source-layout` 改成 `single`，处理器会退回轻微 bounce 动态；但这不是推荐的最终效果。

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

只生成 prompt 计划，不打包：

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py plan-pack \
  --subject "round coral AI helper mascot with paper-stack anxiety" \
  --persona 码农 \
  --style pixel-art \
  --pack-size 16 \
  --mode wechat \
  --animation-layout 1x4 \
  --output output/coder-mascot-plan.json
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

当前测试覆盖：微信数量约束、默认梗库、motion-sheet prompt 计划生成、sheet 切帧、中文文案排版、完整投稿包结构、skill 文档和 reference 文件完整性。

## 文档产物

- [样例测试报告](docs/example-test-report.md)
- [微信公众号宣传稿](docs/wechat-public-account-draft.md)

## 肖像和审核

如果参考图是真人，请确保拥有本人授权或合法使用权。默认策略是“风格化但像本人”，不是高仿真人换脸。公开发布时应避开政治、低俗、攻击性、侵权角色和高审核风险内容。
