# Commands

Run commands from the repository root.

## Plan

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py plan-wizard
```

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py plan-pack \
  --subject "warm geometric AI assistant mascot, original character, no official logo" \
  --persona 科研打工人 \
  --style clean-sticker \
  --pack-size 24 \
  --mode wechat \
  --source-mode keyposes \
  --keypose-layout 2x2 \
  --render-frame-count 16 \
  --quality-mode submission \
  --image-provider openai_images_api \
  --output output/meme-plan.json
```

## Generate Raw Keypose Images Automatically

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py generate-raw-batch \
  --plan output/meme-plan.json \
  --provider openai_images_api \
  --concurrency 3 \
  --max-attempts 2
```

Use `--dry-run` to validate the generated JSONL and provider command without calling the API.

## Accept A Manually Generated Image

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py accept-generated \
  --plan output/meme-plan.json \
  --index 1 \
  --image path/to/generated-image.png
```

## QC

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py qc-sheet \
  --input output/raw-frames/PackName/01-收到离线-2x2.png \
  --source-mode keyposes \
  --source-layout 2x2 \
  --quality-mode submission \
  --output output/qc/01-qc.json
```

## Preview

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-preview \
  --source-dir output/raw-frames/PackName \
  --output-dir output/preview-first-3 \
  --preview-count 3 \
  --source-mode keyposes \
  --keypose-layout 2x2 \
  --quality-mode submission \
  --strict-qc \
  --strict-continuity-qc
```

## Full Build

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-pack \
  --source-dir output/raw-frames/PackName \
  --output-dir output/my-pack \
  --persona 科研打工人 \
  --style clean-sticker \
  --pack-size 24 \
  --mode wechat \
  --source-mode keyposes \
  --keypose-layout 2x2 \
  --quality-mode submission \
  --strict-qc \
  --strict-continuity-qc
```
