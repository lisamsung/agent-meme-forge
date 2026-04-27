---
name: generate-meme-gif-pack-ai-studio
description: Use when the user wants a WeChat-ready animated Chinese meme GIF sticker pack generated through Google AI Studio Web or Hermes using Nano Banana Pro or Nano Banana 2, especially to avoid Codex image_gen or Gemini API costs.
---

# Generate Meme GIF Pack AI Studio

Use Google AI Studio Web as the image provider and keep the existing local meme processor for deterministic captions, QC, GIF rendering, and WeChat packaging. This is a separate provider skill from `generate-meme-gif-pack`; do not mix it into the default Codex `image_gen` flow.

Core rule: use AI Studio only for raw no-text `2x2` keypose PNGs. Local scripts still do the final animation, Chinese captions, compression, manifests, and WeChat folder structure.

## Hard Boundaries

- do not use Codex image_gen as the default image provider in this skill.
- do not use Gemini API unless the user explicitly switches away from the Web/Pro-member route.
- do not bypass Google AI Studio, browser, CAPTCHA, login, account, or download protections. Do not use DevTools, injected scripts, CDP, hidden browser automation, or remote debugging to control AI Studio.
- Hermes or the human operator owns the AI Studio Web page actions: choose model, upload reference image, paste prompt, generate, download, and rename if needed.
- Codex owns planning, prompt-board generation, import-downloads, QC, `build-preview`, `build-pack`, and final handoff.
- Keep every raw AI Studio output as an intermediate keypose sheet, not final delivery. Final delivery is `preview.html`, `named-gifs/*.gif`, and `wechat-submit/main/*.gif`.

## Provider Settings

Use these defaults in Google AI Studio Web:

| Setting | Default |
| --- | --- |
| Model | Nano Banana Pro for final candidate sheets; Nano Banana 2 for fast previews |
| Mode | image generation or image editing with reference upload |
| Aspect ratio | 1:1 |
| Output | PNG |
| Image size | 2K or highest stable quality available |
| Background | pure flat `#00FF00` by default; `#FF00FF` if green conflicts with the subject |
| Quantity | one image per prompt, not a 24-image batch |

Use a reference image when the pack is based on a person or avatar. For text-only mascots, do not upload a reference image unless the user provides one.

## Workflow

1. Generate the normal meme plan with the existing processor. Keep `source_mode=keyposes`, `keypose_layout=2x2`, and `render_frame_count=16`.

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py plan-pack \
  --subject "stylized reference avatar, preserve hair, glasses, shirt, and vibe" \
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

2. Write the AI Studio operator board.

```bash
python skills/generate-meme-gif-pack-ai-studio/scripts/ai_studio_pack.py prompt-board \
  --plan output/ai-studio-plan.json \
  --output output/ai-studio-prompt-board.html \
  --download-dir "$HOME/Downloads/ai-studio-meme-sources/AIStudio码农搭子" \
  --model "Nano Banana Pro" \
  --background "#00FF00" \
  --image-size 2K
```

3. Give Hermes the board and the AI Studio Web task.

Hermes should:

- Open `output/ai-studio-prompt-board.html`.
- Open Google AI Studio Web.
- Select Nano Banana Pro, or Nano Banana 2 for a cheaper preview pass.
- Set 1:1, PNG, high quality or 2K if available.
- Upload the user reference image when the plan uses a person or avatar.
- For each card, copy the prompt, generate exactly one `2x2` keypose sheet, download it, and save/rename to the target filename shown in the board.
- Use the declared download directory.

4. Import downloaded images.

Strict mode expects exact filenames from the board:

```bash
python skills/generate-meme-gif-pack-ai-studio/scripts/ai_studio_pack.py import-downloads \
  --plan output/ai-studio-plan.json \
  --download-dir "$HOME/Downloads/ai-studio-meme-sources/AIStudio码农搭子" \
  --source-dir output/raw-frames/AIStudio码农搭子 \
  --mode strict \
  --limit 3
```

After the first three pass QC, import the full folder without `--limit`. If AI Studio downloaded generic names and Hermes preserved generation order, use ordered mode only after checking the folder contains exactly one image per prompt:

```bash
python skills/generate-meme-gif-pack-ai-studio/scripts/ai_studio_pack.py import-downloads \
  --plan output/ai-studio-plan.json \
  --download-dir "$HOME/Downloads/ai-studio-meme-sources/AIStudio码农搭子" \
  --source-dir output/raw-frames/AIStudio码农搭子 \
  --mode ordered
```

5. Run the same QC and pack build as the base skill.

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

If the first three pass, continue with the remaining planned prompts. The first three are only a QC checkpoint, not a stopping point.

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

## AI Studio Prompt Delta

Before Hermes pastes a prompt, verify it includes:

- exact `2x2` grid, four equal cells, no borders
- same character identity, outfit, crop, bbox, and scale in every cell
- start, anticipation, peak gag, loopable return
- large readable head and full subject inside each cell
- pure flat `#00FF00` or `#FF00FF` background
- no text, no speech bubbles, no UI, no watermark
- no fake checkerboard transparency
- no final Chinese caption

If Nano Banana adds text because it is good at text rendering, reject and regenerate with stronger no-text rules. The local processor adds Chinese captions.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Operator generates a finished GIF or 16 freehand frames | Regenerate one `2x2` keypose sheet; local renderer creates the GIF |
| AI Studio output contains Chinese text | Regenerate with no text/no labels/no speech bubbles emphasized |
| Downloads have generic names | Use `import-downloads --mode ordered` only if count and order are verified |
| Browser automation is blocked | Do not bypass; hand off the web action to Hermes or the user |
| First three look good | Continue remaining prompts and full build; first three are only a checkpoint |
