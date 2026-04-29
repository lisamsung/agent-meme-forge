# agent-meme-forge

把一个人或形象的参考图，生成一套能发、好笑、符合微信表情开放平台规格的动态 GIF 表情包。

核心 skill：`generate-meme-gif-pack`。

## 设计原则

没人用的表情包就是垃圾。这个项目优先解决“聊天里到底会不会发”：

- 每个 GIF 都必须有明确发送场景。
- 梗要短、能读、能复用。
- 每个表情都要过 `sendability_gate`：复用触发场景、情绪价值、创意钩子、视觉笑点。只可爱、只漂亮、只像头像，都不算合格。
- 图片模型不负责写中文，中文文案由本地脚本统一加字。
- 默认产出 24 个动态 GIF，因为微信动态表情专辑通常要求 16 或 24 个。

## 功能

- 从一张真人、头像、IP 形象、角色参考图，或纯文字角色概念生成风格化表情包。
- 先生成角色卡、梗条目和逐条 `image_gen` keypose 提示词，再用本地脚本统一导演动作、加中文、做 GIF 和微信打包。
- 默认高质量路径是每个表情一张 `2x2` keypose sheet：image_gen 只画 4 个关键姿势，本地处理器按动作模板渲染 16 帧，避免 16 格自由生图导致跳闪。`2x4` / `4x4` motion sheet 仍保留为 legacy/expert 模式。
- 内置 `qc-sheet` 和连续性 QC：检查假透明棋盘格、主体过小、边缘出格、bbox 漂移、背景模式、相邻帧突变、面积突变、道具一帧闪现、循环首尾跳变和假动画，结果写入 `qc_report.json` 与 manifest。
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
- 选择生图 provider：默认 `codex_builtin_image_gen` 是“生成后本轮结束”的 Codex 内置生图；`openai_images_api` 适合自动化批量生成；`external_files` / `ai_studio_hermes` 适合已经能导出本地文件、可继续跑 QC 的外部流程。
- 选择源图模式：默认 `2x2` keypose / 本地 16 帧渲染；专家模式可以选 `2x4` 或 `4x4` motion sheet。
- 写出计划 JSON，下一步用里面的 `image_prompts` 做生图 handoff。

注意：`plan-wizard` 和 `plan-pack` 只会写计划和提示词，本地 Python 脚本不能自己调用 Codex 的内置生图工具。如果使用 Codex 内置 `image_gen`，它是 terminal action：调用后不要假设同一轮还能继续跑 `accept-generated`、QC 或打包。要全自动，使用 `--image-provider openai_images_api` 后运行 `generate-raw-batch`；`external_files` / `ai_studio_hermes` 适合已经有本地图片文件的路线。

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
  --source-mode keyposes \
  --keypose-layout 2x2 \
  --render-frame-count 16 \
  --quality-mode submission \
  --image-provider openai_images_api \
  --output output/ai-research-plan.json
```

自动批量生成 raw keypose 图：

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py generate-raw-batch \
  --plan output/ai-research-plan.json \
  --provider openai_images_api \
  --concurrency 3
```

如果你明确想走旧的完整 motion sheet 路线，可以手动切到 legacy/expert 模式：

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py plan-pack \
  --subject "stylized avatar with glasses and expressive office meltdown acting" \
  --persona 都市丽人 \
  --style clean-sticker \
  --pack-size 16 \
  --mode wechat \
  --source-mode motion_sheet \
  --animation-layout 4x4 \
  --quality-mode submission \
  --output output/expressive-16f-plan.json
```

打开 `output/ai-research-plan.json`，里面会有：

- `character_card`：角色设定卡。
- `items`：24 个表情名、文案、关键词、发送场景。
- `animation`：默认 `source_mode=keyposes`、`source_layout=2x2`、`rendered_frame_count=16`。
- `image_prompts`：24 条可直接交给 Codex `image_gen` 的无文字 keypose 提示词，每条都带 `motion_template`、`local_effects`、`qc_policy`、`keypose_beats`、`timeline`、`continuity_acceptance`、`visual_gag`、`qc_acceptance` 和 `regenerate_hint`。
- `meme_quality_bar` / `sendability_gate`：逐条检查“是不是真的有人想发”，弱梗先改再生图。
- `raw_output_dir`：原图落盘目录。
- `image_handoff`：记录 provider 边界、terminal action 说明、下一轮恢复方式、`accept-generated` 命令模板和 `generated-index.json` 路径。

### 3. 调用 image_gen 生成无文字原图

先用前 3 条 `image_prompts[].prompt` 做质量闸门，不要一口气做完 24 张。Codex 内置 `image_gen` 不是普通可串联命令：它应该作为当前轮的最后动作生成下一张 `2x2` keypose sheet。每张 sheet 只含 4 个关键姿势，最终 16 帧由本地处理器按动作模板渲染。

看到“四格图”是正常的：它只是中间 keypose 原图，不是最终表情包。最终给用户检查的是 `preview.html`，最终交付文件在 `named-gifs/表情名.gif` 和 `wechat-submit/main/01.gif ...`。

下一轮拿到保存/导出的本地图片后，再用 `accept-generated` 复制到计划里的标准文件名。这样后续 `qc-sheet` 和 `build-pack` 不会找错文件；同时 `generated-index.json` 会留下每张图的交接记录。

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py accept-generated \
  --plan output/ai-research-plan.json \
  --index 1 \
  --image path/to/generated-image.png \
  --source-dir output/raw-frames/AI科研打工搭子
```

如果当前 `image_gen` 只在聊天里返回附件、没有本地路径，先把附件保存到本机，再运行上面的命令；本地处理器不能直接读取未保存的聊天附件。

背景策略要区分工具入口，不能只写“透明背景”就相信它是真的透明：

- Codex `image_gen` 生成 motion sheet 时，默认要求纯色 `#FF00FF` 背景，除非你确认导出的本地 PNG 真有 alpha 通道。这样最稳，避免模型把棋盘格画进像素里。
- ChatGPT 界面的 ChatGPT Images 可以直接要求“透明背景”，但保存后仍然要跑 QC 确认真 alpha。
- API 侧要看具体模型。支持透明背景的 GPT image 模型需要配合 alpha 格式，例如 `background: "transparent"` 加 `output_format: "png"` 或 `webp`。
- `gpt-image-2` 目前不支持真正透明背景，不能传 `background: "transparent"`；使用它时要生成白色或纯色不透明背景，推荐纯 `#FF00FF`，再由本地处理器抠图。

注意棋盘格不等于透明背景，如果模型把棋盘格画进像素里，或者 motion sheet 出现可见分隔线，也要退回重生。质量不行就重生：角色太小、画了文字、像官方 logo、表情不够强、道具太细、看不出发送场景、网格数量不对、前后帧角色比例乱跳、道具出格、透明边缘有明显红/粉残留，都应该退回。

如果为了快速试效果，先让 `image_gen` 生成一张 `4x6` 静态 contact sheet，可以切成 24 张单姿态原图。注意这只是预览路径，最终质量不如每个表情单独 `2x2` keypose sheet：

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py split-sheet \
  --input output/raw-sheets/ai-research-sheet.png \
  --output-dir raw-frames \
  --rows 6 \
  --cols 4
```

### 4. 先跑 QC

投稿模式先验收前 3 张，过了再继续生成剩余计划图片：

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py qc-sheet \
  --input output/raw-frames/AI科研打工搭子/01-收到离线-2x2.png \
  --source-mode keyposes \
  --source-layout 2x2 \
  --quality-mode submission \
  --output output/qc/01-qc.json
```

失败时不要硬凑，用计划里的 `regenerate_hint` 重生。常见失败原因：画了棋盘格或棋盘格残留、出现 sheet 分隔线、角色碰到格子边缘、关键姿势比例差太多、角色太小、背景不是透明或纯 `#FF00FF`。

### 5. 构建前三张预览

前 3 张通过单张 `qc-sheet` 后，用显式预览命令生成小包和 `preview.html`。这个命令只会使用前 3 张源图，不会把 3 张图循环凑成 24 张：

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-preview \
  --source-dir output/raw-frames/AI科研打工搭子 \
  --output-dir output/preview-first-3 \
  --persona 科研打工人 \
  --style clean-sticker \
  --pack-name AI科研打工搭子前三张 \
  --preview-count 3 \
  --source-mode keyposes \
  --keypose-layout 2x2 \
  --source-layout auto \
  --render-frame-count 16 \
  --quality-mode submission \
  --strict-qc \
  --strict-continuity-qc
```

打开 `output/preview-first-3/preview.html`，重点看动作是否连贯、角色是否漂移、文案是否想发。前三张只是质量闸门，不是交付终点；如果用户要完整包，通过后必须继续生成剩余计划图片并跑完整 `build-pack`。

### 6. 构建微信 GIF 包

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-pack \
  --source-dir output/raw-frames/AI科研打工搭子 \
  --output-dir output/my-pack \
  --persona 科研打工人 \
  --style clean-sticker \
  --pack-size 24 \
  --mode wechat \
  --pack-name 我的表情包 \
  --source-mode keyposes \
  --keypose-layout 2x2 \
  --source-layout auto \
  --render-frame-count 16 \
  --quality-mode submission \
  --strict-qc \
  --strict-continuity-qc
```

完整投稿包不会自动复用源图。`--pack-size 24` 就必须有 24 张已接受的源图；如果目录里只有 3 张，请用上面的 `build-preview`。

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
  --source-mode keyposes \
  --keypose-layout 2x2 \
  --output output/coder-mascot-plan.json
```

## 微信规格默认值

- 主图 GIF：`240x240`，小于 `500KB`，默认目标小于 `480KB`。
- 缩略图 PNG：`120x120`，小于 `50KB`。
- 图标 PNG：`50x50`，透明背景，小于 `30KB`。
- 封面 PNG：`240x240`，透明背景，小于 `80KB`。
- 横幅 PNG：`750x400`，小于 `80KB`，不放文字。
- 接受赞赏时还需要用户提供或单独准备：`750x560` 赞赏引导图、`750x750` 赞赏致谢图，以及 5-15 字赞赏引导语；当前打包器不会自动生成赞赏图。

具体以微信表情开放平台当前官方说明为准。

## 微信后台提交

本 skill 默认先产出本地上传包。只有用户明确要求“提交到微信表情开放平台”时，才走浏览器自动化提交。

- runbook：`skills/generate-meme-gif-pack/references/wechat-platform-upload.md`
- 工具：Playwright CLI + headed Microsoft Edge + persistent profile。
- 登录：用户扫码；遇到 CAPTCHA、实名、支付账户、法律确认等边界时停下来让用户处理。
- 上传：用 Playwright `setInputFiles` 上传 `wechat-submit/main/*.gif`、`banner.png`、`cover.png`、`icon.png`，不要操作系统文件选择器。
- 字段：`版权归属` 填主体名，不要只写 `原创`；真人/照片参考女性形象选 `人物角色 - 女人`。
- 赞赏：勾选 `接受赞赏` 前先确认赞赏引导语、赞赏引导图、赞赏致谢图都已经存在；当前打包器不会自动生成这些图。
- 驳回：按审核驳回页面原文修字段，保存确认预览更新后再重新提交。

## 投稿前检查

- `manifest.json` 里每个 item 的 `qc_status` 都应该是 `pass`。
- `manifest.json` 里每个 item 的 `continuity_qc_status` 都应该是 `pass`。
- `qc_report.json` 不应有 `errors`。
- `source_mode` 应该是 `keyposes`，`animation_source` 应该是 `keyposes`，不是 `single_bounce`。
- `source_layout` 投稿默认应是 `2x2`，`source_frame_count` 应是 `4`，`rendered_frame_count` 应是 `16`。
- 高频模板会在本地补 `local_effects`：`收到离线` 的灵魂泡泡、`加载中` 的 loading 点、`先装懂` 的汗滴/尴尬线；这些不应该交给 image_gen 随机画。
- `prop_lifecycle_errors` 应为空，`prop_position_jump` 和 `prop_area_jump` 不应超阈值；道具或特效不能只闪一帧，也不能跨区域瞬移。
- `face_shape_drift_score` 和 `max_head_center_step_px` 不应超阈值；动作可以夸张，但脸型和头部不能随机变成另一个人。
- `gif_frame_count` 应尽量等于 `rendered_frame_count`。如果 GIF 太大，处理器会降到 12/8/6/4 帧以满足微信大小限制，manifest 会记录最终帧数。
- 默认帧时长：16 帧约 `150ms/帧`。如果看起来仍然跳，优先重生更稳定的 keypose sheet 或换动作模板，而不是只继续放慢。
- `background_mode` 应是 `transparent` 或 `magenta`，且 `qc_warnings`/`qc_errors` 里不能有 `checkerboard residue` 或 `separator line residue`。
- `edge_touch` 应是 `false`，`bbox_drift.size_ratio` 不应超阈值。
- 打开 `named-gifs/` 抽查至少 3 张：动作能读、文字不挡脸、边缘没有粉色残留。

## 开发验证

```bash
. .venv/bin/activate
pytest -q
```

当前测试覆盖：微信数量约束、默认梗库、keypose-first prompt 计划生成、motion template 渲染、本地特效层、连续性 QC、道具闪现/瞬移拦截、脸型漂移拦截、legacy motion-sheet 兼容、sheet 切帧、QC 门禁、假透明检测、边缘出格检测、bbox 漂移检测、中文文案排版、完整投稿包结构、skill 文档和 reference 文件完整性。

## 文档产物

- [样例测试报告](docs/example-test-report.md)
- [微信公众号宣传稿](docs/wechat-public-account-draft.md)

## 肖像和审核

如果参考图是真人，请确保拥有本人授权或合法使用权。默认策略是“风格化但像本人”，不是高仿真人换脸。公开发布时应避开政治、低俗、攻击性、侵权角色和高审核风险内容。
