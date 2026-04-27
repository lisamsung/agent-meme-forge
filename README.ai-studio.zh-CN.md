# Agent Meme Forge - AI Studio Web 分支

这个分支新增独立 skill：`generate-meme-gif-pack-ai-studio`。

它不替代原来的 `generate-meme-gif-pack`，而是把生图 provider 换成 Google AI Studio Web / Nano Banana Pro / Nano Banana 2，适合用 Pro 会员网页额度，避免直接走昂贵 API。

## 分工

- Hermes 或人工操作者：在 AI Studio Web 里选模型、上传参考图、粘贴 prompt、生成、下载。
- Codex：生成梗和 prompt、输出 prompt board、导入下载图、跑 QC、渲染 GIF、打包微信投稿目录。

## 快速流程

1. 生成普通计划：

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py plan-pack \
  --subject "stylized reference avatar, preserve hair, glasses, outfit, and vibe" \
  --persona 码农 \
  --style clean-sticker \
  --pack-size 24 \
  --mode wechat \
  --pack-name AIStudio码农搭子 \
  --source-mode keyposes \
  --keypose-layout 2x2 \
  --render-frame-count 16 \
  --quality-mode submission \
  --output output/ai-studio-plan.json
```

2. 生成给 Hermes 用的 prompt board：

```bash
python skills/generate-meme-gif-pack-ai-studio/scripts/ai_studio_pack.py prompt-board \
  --plan output/ai-studio-plan.json \
  --output output/ai-studio-prompt-board.html \
  --download-dir "$HOME/Downloads/ai-studio-meme-sources/AIStudio码农搭子" \
  --model "Nano Banana Pro" \
  --background "#00FF00" \
  --image-size 2K
```

3. Hermes 在 AI Studio Web 里逐条生成并下载，优先按 board 里的目标文件名保存。

4. 导入下载图：

```bash
python skills/generate-meme-gif-pack-ai-studio/scripts/ai_studio_pack.py import-downloads \
  --plan output/ai-studio-plan.json \
  --download-dir "$HOME/Downloads/ai-studio-meme-sources/AIStudio码农搭子" \
  --source-dir output/raw-frames/AIStudio码农搭子 \
  --mode strict \
  --limit 3
```

前三张预览通过后，去掉 `--limit` 导入全量下载。  
如果 AI Studio 只能下载成通用文件名，并且你确认文件数量和顺序完全正确：

```bash
python skills/generate-meme-gif-pack-ai-studio/scripts/ai_studio_pack.py import-downloads \
  --plan output/ai-studio-plan.json \
  --download-dir "$HOME/Downloads/ai-studio-meme-sources/AIStudio码农搭子" \
  --source-dir output/raw-frames/AIStudio码农搭子 \
  --mode ordered
```

5. 跑预览和完整包：

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-preview \
  --source-dir output/raw-frames/AIStudio码农搭子 \
  --output-dir output/ai-studio-preview-first-3 \
  --persona 码农 \
  --style clean-sticker \
  --pack-name AIStudio码农搭子前三张 \
  --preview-count 3 \
  --source-mode keyposes \
  --keypose-layout 2x2 \
  --source-layout auto \
  --render-frame-count 16 \
  --quality-mode submission \
  --strict-qc \
  --strict-continuity-qc
```

前三张只是质量闸门，不是终点。通过后继续剩余 planned prompts，最后：

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-pack \
  --source-dir output/raw-frames/AIStudio码农搭子 \
  --output-dir output/ai-studio-pack \
  --persona 码农 \
  --style clean-sticker \
  --pack-size 24 \
  --mode wechat \
  --pack-name AIStudio码农搭子 \
  --source-mode keyposes \
  --keypose-layout 2x2 \
  --source-layout auto \
  --render-frame-count 16 \
  --quality-mode submission \
  --strict-qc \
  --strict-continuity-qc
```

## AI Studio 参数

- Model：Nano Banana Pro 优先；Nano Banana 2 用于快速预览
- Aspect ratio：`1:1`
- Output：PNG
- Image size：`2K` 或页面可选最高稳定质量
- Background：纯 `#00FF00`；如果主体含绿色，换 `#FF00FF`
- 每条 prompt 只生成一张 `2x2` keypose sheet
- 不让 AI Studio 生成中文文字，最终字幕由本地脚本添加

## 安全边界

这个分支不通过 DevTools、CDP、脚本注入或浏览器绕过来操控 AI Studio。页面操作由 Hermes 或人工完成，Codex 只做工程化交接和后处理。
