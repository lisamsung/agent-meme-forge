# Workflow

## 1. Intake

Collect input source, persona, style, mode/count, quality mode, and image provider. If the user asks for automation, choose `openai_images_api`. If the user explicitly asks for Google AI Studio or Hermes, use the sister skill.

## 2. Plan

Run `plan-wizard` or `plan-pack`. Review:

- `character_card`
- `items`
- `image_prompts`
- `meme_quality_bar`
- `requires_agent_tooling`
- `image_handoff`
- `workflow_contract`

## 3. Generate

Default path: one semantic `2x2` no-text keypose sheet per sticker. The processor turns 4 stable poses into a 16-frame GIF with local effects and Chinese captions. This is the robust default and works with any provider.

For maximum smoothness, the **recommended** path is dense real frames (`--source-mode dense_frames`, see `references/dense-frames.md`): the model draws ~8 genuinely different frames in one sheet and the processor size- and head-normalizes and assembles them. It needs a provider that can draw 8 consistent frames in one image (and a few stickers per pack may need regenerating), so keyposes stays the safe default.

Provider split:

- `codex_builtin_image_gen`: generate one keypose sheet as terminal action, then resume next turn.
- `openai_images_api`: run `generate-raw-batch` to generate planned raw files automatically.
- `external_files` / `ai_studio_hermes`: import already-existing local files.

## 4. First-3 Gate

QC and build a first-3 preview. This is a checkpoint, not completion. If the first 3 are technically valid but not funny or sendable, revise the plan before continuing.

## 5. Full Build

After every planned raw source exists, run `build-pack` with strict QC and strict continuity QC. Full builds require one accepted source image per sticker and must not silently loop the first three images.

## 6. Final Handoff

Return:

- `preview.html`
- `named-gifs/表情名.gif`
- `wechat-submit/main/01.gif ...`
- `manifest.json`
- `qc_report.json`

Do not present raw keypose sheets as the finished sticker pack.

## 7. Optional WeChat Upload

Only after local QC passes and the user asks to upload, follow `wechat-platform-upload.md`.
