# agent-meme-forge

A Codex skill and local processor for generating WeChat-ready animated Chinese meme GIF packs from one reference person, mascot, avatar, character image, or text-only character concept.

Core skill: `generate-meme-gif-pack`.

The product rule is simple: if nobody would send the sticker in chat, it is not good enough.

## What It Builds

- A prompt plan with a character card, sendable meme list, and per-sticker no-text `2x4` 8-frame motion-sheet `image_gen` prompts.
- A `qc-sheet` gate for fake checkerboards, edge touch, empty frames, bbox drift, background mode, and frame count.
- A 16/24 item animated GIF sticker album for WeChat Sticker Open Platform.
- Human-readable GIF names in `named-gifs/`.
- Upload-safe numbered files in `wechat-submit/`.
- Thumbnails, cover, icon, banner, `manifest.json`, and `manifest.csv`.

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

To install the skill locally:

```bash
cp -R skills/generate-meme-gif-pack ~/.codex/skills/
```

Restart the Codex session after installing a skill.

## Build a Pack

For a guided intake that asks whether to use a reference image or text concept, plus scene/persona, style, pack size, and quality mode:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py plan-wizard
```

Or create a prompt plan directly, then call Codex `image_gen` with the generated no-text prompts.

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py plan-pack \
  --subject "warm geometric AI assistant mascot with cream body and coral accents, original character, no official logo" \
  --persona 科研打工人 \
  --style clean-sticker \
  --pack-size 24 \
  --mode wechat \
  --animation-layout 2x4 \
  --quality-mode submission \
  --output output/ai-research-plan.json
```

Generate and QC the first 3 sheets before making all 24. Save accepted transparent-background raw `2x4` motion sheets into `raw-frames/`. If transparency is unavailable, use a solid `#FF00FF` fallback background. Static 4x6 contact sheets are useful only for previews; split them first if you use that lower-quality path:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py qc-sheet \
  --input raw-frames/01-收到离线-2x4.png \
  --source-layout 2x4 \
  --quality-mode submission \
  --output output/qc/01-qc.json
```

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py split-sheet \
  --input output/raw-sheets/ai-research-sheet.png \
  --output-dir raw-frames \
  --rows 6 \
  --cols 4
```

Then build the package:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-pack \
  --source-dir raw-frames \
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

## Test

```bash
. .venv/bin/activate
pytest -q
```

See [README.zh-CN.md](README.zh-CN.md) for the full Chinese documentation.

## Docs

- [Example test report](docs/example-test-report.md)
- [WeChat public-account draft](docs/wechat-public-account-draft.md)
