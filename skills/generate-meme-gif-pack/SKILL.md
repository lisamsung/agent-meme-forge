---
name: generate-meme-gif-pack
description: Use when the user wants to turn a reference person, mascot, avatar, or character image into a WeChat-ready animated Chinese meme GIF sticker pack, especially with persona labels, workplace/student/research humor, or strict platform-size constraints.
---

# Generate Meme GIF Pack

Create animated Chinese meme GIF packs from either a reference image or a text-only character concept. The core design rule is: a sticker nobody sends is waste. Prioritize repeatable chat-use cases, clear reaction value, and fast readability over decorative polish.

## Inputs

Infer or ask only when blocked:

- `reference_image`: uploaded person, mascot, avatar, or character image. Use `input_mode=reference_image` when present.
- `subject`: required when no image is uploaded. Use `input_mode=text_concept` for direct text generation, e.g. “warm geometric AI assistant mascot with coral accents, original character, no official logo”.
- `style`: `clean-sticker` default; also `pixel-art`, `chibi`, `retro-msn`, `office-cartoon`, `hand-drawn`.
- `persona`: `科研打工人` default; also `都市丽人`, `打工仔`, `码农`, `学生`, `研究僧`, `早八特困生`, `甲方幸存者`, `会议受害者`, `ddl祭司`.
- `pack_size`: WeChat mode only allows 16 or 24. Default to 24.
- `mode`: `wechat` default, or `self_use`.
- `tone`: default `职场发疯但安全`.
- `animation_layout`: default `2x4` motion sheet per sticker for 8-frame smoother GIFs; also `1x4`, `1x8`, `2x2`, or `2x3`.
- `quality_mode`: default `submission`; also `standard` or `preview`. Submission requires strict QC, real `2x4` sheets, and no single-image bounce fallback.

If the user asks for 18 and wants WeChat upload, explain that WeChat albums use 16 or 24, then default to 24 unless they explicitly switch to `self_use`.

## Agent Rules

- Make the character stylized but recognizable: preserve hair, face shape, posture, vibe, and signature details when a reference image exists; for `text_concept`, create an original mascot or character from the concept without copying official logos or exact copyrighted characters.
- Require the user to own or have permission for the reference image when the image depicts a real person.
- Keep humor safe for public WeChat review: no politics, hate, sexual content, slurs, doxxing, medical claims, or direct harassment.
- Do not ask the image model to draw Chinese text. The visual prompt must say **no text**, no captions, no speech bubbles, no UI.
- Write meme copy yourself. Every item needs a concrete sending scenario.
- Use `scripts/meme_pack.py plan-pack` to write the meme entries, character card, and per-sticker `image_gen` prompts.
- Use built-in `image_gen` for raw no-text motion sheets. Use `scripts/meme_pack.py build-pack` only for deterministic processing.
- Prefer one semantic motion sheet per sticker, not one static pose. Single-pose sources are allowed only for fast previews or fallback.
- Motion sheets must use exact grid count, same character identity, same bounding box, same pixel scale, clear margins, no cell-edge crossing, and no text.
- Prefer transparent PNG background directly from the image model. If transparency is not available, use a solid flat `#FF00FF` background as fallback; the processor removes it and cleans magenta edge spill.
- Reject fake checkerboard transparency. It is just visible pixels, not alpha transparency.
- Run `qc-sheet` on the first 3 generated sheets before generating all 24. Regenerate anything that fails layout, transparency, edge-touch, bbox drift, or readability checks.
- For WeChat submission, use `--quality-mode submission --strict-qc`. Single-image `single_bounce` output is preview-only.
- WeChat output must include numbered upload files and readable named GIF files.

## Workflow

1. Read references:
   - `references/wechat-spec.md` for output constraints.
   - `references/personas.md` and `references/meme-library.md` for pack planning.
   - `references/styles.md` and `references/prompt-rules.md` for visual prompts.
2. Create a plan. For a text-only concept:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py plan-pack \
  --subject "warm geometric AI assistant mascot with cream body and coral accents, original character, no official logo" \
  --persona 科研打工人 \
  --style clean-sticker \
  --pack-size 24 \
  --mode wechat \
  --pack-name AI科研打工搭子 \
  --animation-layout 2x4 \
  --quality-mode submission \
  --output output/ai-research-plan.json
```

For a reference image, add `--reference-image path/to/reference.png` and describe the key traits in `--subject`.
3. Review the generated plan:
   - `character_card`: identity traits, silhouette, color anchors, expression range, forbidden drift.
   - `items`: meme names, captions, keywords, use scenes, motion hints.
   - `animation`: sheet layout and frame count, default `2x4` / 8 frames.
   - `image_prompts`: one motion-sheet prompt per sticker for `image_gen`.
4. Plan 24 entries:
   - 12 common high-frequency chat reactions.
   - 8 persona-specific jokes.
   - 4 reusable filler reactions.
5. Generate and QC raw images:
   - Call built-in `image_gen` for the first 3 generated `image_prompts`, not all 24 at once.
   - Default quality path: one `2x4` no-text motion sheet per sticker.
   - Each sheet frame should be a real acting beat: start, anticipation, action, escalation, peak reaction, rebound, settle, loopable return.
   - For a fast first pass only, one 4x6 contact sheet of static poses is acceptable; split it with `split-sheet` before `build-pack`.
   - Ask for transparent PNG background first. If the model/tool cannot output transparency, use a solid flat `#FF00FF` background; the processor removes it locally.
   - Run `qc-sheet` on those first 3 motion sheets. If a sheet fails, use its `regenerate_hint` from the plan and generate again.
   - Continue to the remaining 21 sheets only after the first 3 pass QC.

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py qc-sheet \
  --input output/raw-frames/01-收到离线-2x4.png \
  --source-layout 2x4 \
  --quality-mode submission \
  --output output/qc/01-qc.json
```
6. Build the pack:

Optional static contact-sheet split for previews:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py split-sheet \
  --input output/raw-sheets/ai-research-sheet.png \
  --output-dir raw-frames \
  --rows 6 \
  --cols 4
```

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-pack \
  --source-dir path/to/raw-frames \
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

7. QC before returning:
   - For motion-sheet packs, inspect `manifest.json`: `animation_source` should be `sheet`, `source_layout` should match the plan, and `source_frame_count` should be greater than 1.
   - Open several GIFs and verify the face/character still reads at 240px.
   - Check every main GIF is 240x240 and below 500KB.
   - Check thumbnails are 120x120 and below 50KB.
   - Check the text is readable and not clipped.
   - Inspect `qc_report.json`: every item should be `pass` for submission.
   - Reject weak jokes. Replace any entry that is only decorative or has no obvious send scenario.

## Output

Expected folder:

```text
output/my-pack/
  named-gifs/表情名.gif
  wechat-submit/main/01.gif
  wechat-submit/thumbs/01.png
  wechat-submit/cover.png
  wechat-submit/icon.png
  wechat-submit/banner.png
  manifest.json
  manifest.csv
  qc_report.json
```

Use `named-gifs/` for human sharing. Use `wechat-submit/` for WeChat upload.

## Pressure Scenarios

- User gives only one photo and says “做科研打工人表情包”: infer 24 entries, do not ask for all captions.
- User asks “18 个上传微信”: explain 18 is `self_use`; switch to 24 for WeChat.
- User asks for “更疯更毒舌”: keep it funny but safe; use workplace meltdown humor instead of insults or review-risk content.
- User asks for pixel style: use `pixel-art` visual prompts, but still output WeChat 240x240 GIFs.
