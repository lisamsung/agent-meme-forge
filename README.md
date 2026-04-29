# agent-meme-forge

A Codex skill and local processor for generating WeChat-ready animated Chinese meme GIF packs from one reference person, mascot, avatar, character image, or text-only character concept.

Core skill: `generate-meme-gif-pack`.

The product rule is simple: if nobody would send the sticker in chat, it is not good enough.
Every planned sticker now carries a sendability gate: reuse trigger, emotional value, creative hook, and reject criteria for anything that is only cute or decorative.

## What It Builds

- A prompt plan with a character card, sendable meme list, and per-sticker no-text `2x2` keypose `image_gen` prompts.
- A local deterministic motion renderer that turns 4 key poses into a 16-frame GIF using productized templates such as `soul_offline`, `loading_loop`, and `pretend_understand`, with local non-text effects like soul puffs, loading dots, sweat drops, and awkward lines.
- A `qc-sheet` and continuity gate for fake checkerboards, edge touch, empty frames, bbox drift, background mode, frame count, frame jumps, area jumps, one-frame props, prop position/area jumps, face/head shape drift, loop closure, and low motion energy.
- A 16/24 item animated GIF sticker album for WeChat Sticker Open Platform.
- Human-readable GIF names in `named-gifs/`.
- Upload-safe numbered files in `wechat-submit/`.
- Thumbnails, cover, icon, banner, `manifest.json`, and `manifest.csv`.
- A Playwright + Microsoft Edge runbook for optional last-mile submission to WeChat Sticker Open Platform.

## WeChat Platform Upload

The skill builds a local upload package first. If the user explicitly asks to submit it to WeChat, use `skills/generate-meme-gif-pack/references/wechat-platform-upload.md`:

- Open `sticker.weixin.qq.com` with Playwright CLI, headed Microsoft Edge, and a persistent profile.
- Let the user scan the QR code; stop for CAPTCHA, real-name, payment, or unexpected legal prompts.
- Upload files with Playwright `setInputFiles`, not OS file-picker automation.
- Save, verify metadata, then click `提交` only after the user authorizes submission.
- If review rejects the pack, follow the rejection page exactly, save the corrected metadata, and resubmit.

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

To install the skill locally:

```bash
mkdir -p /Users/shanxingjun/.codex-switcher/skills
cp -R skills/generate-meme-gif-pack /Users/shanxingjun/.codex-switcher/skills/
```

Restart the Codex session after installing a skill.

## Build a Pack

For a guided intake that asks whether to use a reference image or text concept, plus scene/persona, style, pack size, quality mode, and image provider:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py plan-wizard
```

Or create a prompt plan directly, then use the generated no-text prompts with your selected image provider. The default `codex_builtin_image_gen` provider is a terminal action in Codex: call it as the final action for the current turn, then resume local acceptance/QC in the next turn after the image has been saved/exported. Use `external_files` or `ai_studio_hermes` only when a provider already gives you local files for same-workflow processing.

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py plan-pack \
  --subject "warm geometric AI assistant mascot with cream body and coral accents, original character, no official logo" \
  --persona 科研打工人 \
  --style clean-sticker \
  --pack-size 24 \
  --mode wechat \
  --source-mode keyposes \
  --keypose-layout 2x2 \
  --render-frame-count 16 \
  --quality-mode submission \
  --output output/ai-research-plan.json
```

Generate and QC the first 3 sheets before making the full pack. With built-in Codex `image_gen`, generate one keypose sheet as a handoff, then in the next turn save/export it to a local file and accept it into the planned raw filename:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py accept-generated \
  --plan output/ai-research-plan.json \
  --index 1 \
  --image path/to/generated-image.png \
  --source-dir output/raw-frames/AgentMemePack
```

Save accepted raw `2x2` keypose sheets into `raw-frames/`. The processor renders the final 16-frame GIF locally, which is more stable than asking image_gen to freely draw 16 frames. Legacy `2x4`/`4x4` motion sheets still work with `--source-mode motion_sheet`, but they are no longer the default submission path. For Codex `image_gen`, prefer a pure solid `#FF00FF` background unless you have verified that the exported PNG has real alpha. In ChatGPT Images, transparent background is fine after QC verifies it is real alpha. In the API, use transparent output only with models and alpha formats that support it, such as PNG/WebP via `output_format`; for `gpt-image-2`, use a solid `#FF00FF` fallback background and let the processor remove it. Static 4x6 contact sheets are useful only for previews; split them first if you use that lower-quality path:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py qc-sheet \
  --input output/raw-frames/AgentMemePack/01-收到离线-2x2.png \
  --source-mode keyposes \
  --source-layout 2x2 \
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

Build an explicit first-3 preview before continuing the remaining planned images. This path writes `preview.html` and never loops 3 source sheets into a fake full package:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-preview \
  --source-dir output/raw-frames/AgentMemePack \
  --output-dir output/preview-first-3 \
  --persona 科研打工人 \
  --style clean-sticker \
  --pack-name AgentMemePackPreview \
  --preview-count 3 \
  --source-mode keyposes \
  --keypose-layout 2x2 \
  --source-layout auto \
  --render-frame-count 16 \
  --quality-mode submission \
  --strict-qc \
  --strict-continuity-qc
```

Then build the full package after every planned source sheet exists:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-pack \
  --source-dir output/raw-frames/AgentMemePack \
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

Full submission builds require one accepted source image per entry. If you have only the first 3 sheets, use `build-preview`.

## Test

```bash
. .venv/bin/activate
pytest -q
```

See [README.zh-CN.md](README.zh-CN.md) for the full Chinese documentation.

## Docs

- [Example test report](docs/example-test-report.md)
- [WeChat public-account draft](docs/wechat-public-account-draft.md)
