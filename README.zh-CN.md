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
- 默认高质量路径是每个表情一张 `2x4` motion sheet，处理器按 8 个真实动作帧输出更丝滑的 GIF；`submission` 模式会用 QC 拒绝单张静态图 fallback。
- 内置 `qc-sheet`：检查假透明棋盘格、主体过小、边缘出格、bbox 漂移、背景模式和帧数，结果写入 `qc_report.json` 与 manifest。
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

### 1. 新手先用交互式选择

如果你还没想清楚“要不要上传参考图、选什么场景、选什么风格”，先用 wizard：

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py plan-wizard
```

它会依次询问：

- 用参考图片，还是纯文字角色概念。
- 如果用参考图片，填写本地图片路径或 Codex 上传图标签。
- 选择人设/场景：科研打工人、码农、都市丽人、学生等。
- 选择画面风格：清爽贴纸、像素风、Q 版、办公室漫画等。
- 选择微信投稿包或自用包，以及 16/24/18 数量。
- 选择质量模式：`submission`、`standard`、`preview`。
- 写出计划 JSON，下一步用里面的 `image_prompts` 调用 `image_gen`。

注意：`plan-wizard` 和 `plan-pack` 只会写计划和提示词，本地 Python 脚本不能自己调用 Codex 的生图工具。如果你是在 Codex agent 里要求“生成表情包”，agent 应该在计划生成后继续调用内置 `image_gen` 生成前 3 张 motion sheet；只有当前会话没有生图工具时，才把 prompts 交给你手动处理。

### 2. 或者直接生成计划和 image_gen 提示词

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
  --animation-layout 2x4 \
  --quality-mode submission \
  --output output/ai-research-plan.json
```

打开 `output/ai-research-plan.json`，里面会有：

- `character_card`：角色设定卡。
- `items`：24 个表情名、文案、关键词、发送场景。
- `animation`：默认 `2x4`，每个表情 8 个动作帧。
- `image_prompts`：24 条可直接交给 Codex `image_gen` 的无文字动作 sheet 提示词，每条都带 `visual_gag`、`qc_acceptance` 和 `regenerate_hint`。
- `raw_output_dir`：原图落盘目录。
- `image_handoff`：把 `image_gen` 结果接进本地处理器的 `accept-generated` 命令模板，以及 `generated-index.json` 记录路径。

### 3. 调用 image_gen 生成无文字原图

先把前 3 条 `image_prompts[].prompt` 交给 Codex 内置 `image_gen`，不要一口气做完 24 张。默认会要求生成一张 `2x4` 动作 sheet，例如 `raw-frames/01-收到离线-2x4.png ... 24-你说得对-2x4.png`。

每次 `image_gen` 产出后，先把生成图保存/导出为本地文件，再用 `accept-generated` 复制到计划里的标准文件名。这样后续 `qc-sheet` 和 `build-pack` 不会找错文件；同时 `generated-index.json` 会留下每张图的交接记录。

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py accept-generated \
  --plan output/ai-research-plan.json \
  --index 1 \
  --image path/to/generated-image.png \
  --source-dir output/raw-frames/AI科研打工搭子
```

如果当前 `image_gen` 只在聊天里返回附件、没有本地路径，先把附件保存到本机，再运行上面的命令；本地处理器不能直接读取未保存的聊天附件。

优先要求透明 PNG 背景，但要区分工具入口：

- ChatGPT 界面的 ChatGPT Images 可以直接要求“透明背景”，优先试这条路径。
- API 侧要看具体模型。支持透明背景的 GPT image 模型需要配合 alpha 格式，例如 `background: "transparent"` 加 `output_format: "png"` 或 `webp`。
- `gpt-image-2` 目前不支持真正透明背景，不能传 `background: "transparent"`；使用它时要生成白色或纯色不透明背景，推荐纯 `#FF00FF`，再由本地处理器抠图。

注意棋盘格不等于透明背景，如果模型把棋盘格画进像素里，也要退回重生。质量不行就重生：角色太小、画了文字、像官方 logo、表情不够强、道具太细、看不出发送场景、网格数量不对、前后帧角色比例乱跳、道具出格、透明边缘有明显红/粉残留，都应该退回。

如果为了快速试效果，先让 `image_gen` 生成一张 `4x6` 静态 contact sheet，可以切成 24 张单姿态原图。注意这只是预览路径，最终质量不如每个表情单独 `2x4` motion sheet：

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py split-sheet \
  --input output/raw-sheets/ai-research-sheet.png \
  --output-dir raw-frames \
  --rows 6 \
  --cols 4
```

### 4. 先跑 QC

投稿模式先验收前 3 张，过了再继续生成剩余 21 张：

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py qc-sheet \
  --input output/raw-frames/AI科研打工搭子/01-收到离线-2x4.png \
  --source-layout 2x4 \
  --quality-mode submission \
  --output output/qc/01-qc.json
```

失败时不要硬凑，用计划里的 `regenerate_hint` 重生。常见失败原因：画了棋盘格、角色碰到格子边缘、某一帧突然变大、角色太小、背景不是透明或纯 `#FF00FF`。

### 5. 构建微信 GIF 包

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-pack \
  --source-dir output/raw-frames/AI科研打工搭子 \
  --output-dir output/my-pack \
  --persona 科研打工人 \
  --style clean-sticker \
  --pack-size 24 \
  --mode wechat \
  --pack-name 我的表情包 \
  --source-layout 2x4 \
  --quality-mode submission \
  --strict-qc
```

如果你只有单张静态姿态图，可以把 `--quality-mode` 改成 `preview`，并把 `--source-layout` 改成 `single`，处理器会退回轻微 bounce 动态；但这不是投稿质量。

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
  --animation-layout 2x4 \
  --output output/coder-mascot-plan.json
```

## 微信规格默认值

- 主图 GIF：`240x240`，小于 `500KB`，默认目标小于 `480KB`。
- 缩略图 PNG：`120x120`，小于 `50KB`。
- 图标 PNG：`50x50`，透明背景，小于 `30KB`。
- 封面 PNG：`240x240`，透明背景，小于 `80KB`。
- 横幅 PNG：`750x400`，小于 `80KB`，不放文字。

具体以微信表情开放平台当前官方说明为准。

## 投稿前检查

- `manifest.json` 里每个 item 的 `qc_status` 都应该是 `pass`。
- `qc_report.json` 不应有 `errors`。
- `animation_source` 应该是 `sheet`，不是 `single_bounce`。
- `source_layout` 投稿默认应是 `2x4`，`source_frame_count` 应是 `8`。
- `background_mode` 应是 `transparent` 或 `magenta`。
- `edge_touch` 应是 `false`，`bbox_drift.size_ratio` 不应超阈值。
- 打开 `named-gifs/` 抽查至少 3 张：动作能读、文字不挡脸、边缘没有粉色残留。

## 开发验证

```bash
. .venv/bin/activate
pytest -q
```

当前测试覆盖：微信数量约束、默认梗库、motion-sheet prompt 计划生成、sheet 切帧、QC 门禁、假透明检测、边缘出格检测、bbox 漂移检测、中文文案排版、完整投稿包结构、skill 文档和 reference 文件完整性。

## 文档产物

- [样例测试报告](docs/example-test-report.md)
- [微信公众号宣传稿](docs/wechat-public-account-draft.md)

## 肖像和审核

如果参考图是真人，请确保拥有本人授权或合法使用权。默认策略是“风格化但像本人”，不是高仿真人换脸。公开发布时应避开政治、低俗、攻击性、侵权角色和高审核风险内容。
