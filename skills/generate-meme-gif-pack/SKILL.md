---
name: generate-meme-gif-pack
description: Use when the user wants to turn a reference person, mascot, avatar, or character image into a WeChat-ready animated Chinese meme GIF sticker pack, especially with persona labels, workplace/student/research humor, or strict platform-size constraints.
---

# Generate Meme GIF Pack

Create animated Chinese meme GIF packs from one reference image. The core design rule is: a sticker nobody sends is waste. Prioritize repeatable chat-use cases, clear reaction value, and fast readability over decorative polish.

## Inputs

Infer or ask only when blocked:

- `reference_image`: required uploaded person, mascot, avatar, or character image.
- `style`: `clean-sticker` default; also `pixel-art`, `chibi`, `retro-msn`, `office-cartoon`, `hand-drawn`.
- `persona`: `科研打工人` default; also `都市丽人`, `打工仔`, `码农`, `学生`, `研究僧`, `早八特困生`, `甲方幸存者`, `会议受害者`, `ddl祭司`.
- `pack_size`: WeChat mode only allows 16 or 24. Default to 24.
- `mode`: `wechat` default, or `self_use`.
- `tone`: default `职场发疯但安全`.

If the user asks for 18 and wants WeChat upload, explain that WeChat albums use 16 or 24, then default to 24 unless they explicitly switch to `self_use`.

## Agent Rules

- Make the character stylized but recognizable: preserve hair, face shape, posture, vibe, and signature details; avoid photorealistic face swaps.
- Require the user to own or have permission for the reference image when the image depicts a real person.
- Keep humor safe for public WeChat review: no politics, hate, sexual content, slurs, doxxing, medical claims, or direct harassment.
- Do not ask the image model to draw Chinese text. The visual prompt must say **no text**, no captions, no speech bubbles, no UI.
- Write meme copy yourself. Every item needs a concrete sending scenario.
- Use built-in `image_gen` for raw visual frames or frame sheets. Use `scripts/meme_pack.py` only for deterministic processing.
- WeChat output must include numbered upload files and readable named GIF files.

## Workflow

1. Read references:
   - `references/wechat-spec.md` for output constraints.
   - `references/personas.md` and `references/meme-library.md` for pack planning.
   - `references/styles.md` and `references/prompt-rules.md` for visual prompts.
2. Create a character card from the reference image:
   - identity traits, silhouette, hair/clothing cues, expression range, forbidden drift.
3. Plan 24 entries:
   - 12 common high-frequency chat reactions.
   - 8 persona-specific jokes.
   - 4 reusable filler reactions.
4. Generate raw images:
   - Prefer one clean no-text pose image per sticker, or a short 4-6 frame no-text sequence when the model can keep consistency.
   - Use transparent or solid simple background if possible; avoid clutter because the final canvas is 240x240.
5. Build the pack:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-pack \
  --source-dir path/to/raw-frames \
  --output-dir output/my-pack \
  --persona 科研打工人 \
  --style clean-sticker \
  --pack-size 24 \
  --mode wechat \
  --pack-name 我的表情包
```

6. QC before returning:
   - Open several GIFs and verify the face/character still reads at 240px.
   - Check every main GIF is 240x240 and below 500KB.
   - Check thumbnails are 120x120 and below 50KB.
   - Check the text is readable and not clipped.
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
```

Use `named-gifs/` for human sharing. Use `wechat-submit/` for WeChat upload.

## Pressure Scenarios

- User gives only one photo and says “做科研打工人表情包”: infer 24 entries, do not ask for all captions.
- User asks “18 个上传微信”: explain 18 is `self_use`; switch to 24 for WeChat.
- User asks for “更疯更毒舌”: keep it funny but safe; use workplace meltdown humor instead of insults or review-risk content.
- User asks for pixel style: use `pixel-art` visual prompts, but still output WeChat 240x240 GIFs.
