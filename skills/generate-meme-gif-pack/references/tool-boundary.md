# Tool Boundary

Use this file whenever the workflow involves image generation.

## Provider Decision

| Provider | Use When | Same-Turn Postprocess |
|---|---|---|
| `codex_builtin_image_gen` | Interactive Codex preview or manual per-image generation. | No. Built-in `image_gen` is a terminal action; resume next turn after the image is saved locally. |
| `openai_images_api` | Full automation, concurrency, or API-driven batch generation. | Yes. Use `generate-raw-batch` to produce local raw PNGs. |
| `external_files` | User or another provider already produced local image files. | Yes, after files exist locally. |
| `ai_studio_hermes` | Local files come from the separate AI Studio/Hermes route. | Yes, after files exist locally. Prefer the sister skill for that route. |

## Codex Built-In `image_gen`

- Treat built-in `image_gen` as the final action of the current turn.
- Before calling it, identify `image_prompts[index]`, `raw_image_filename`, and the exact no-text prompt.
- Do not run `accept-generated`, `qc-sheet`, `build-preview`, or `build-pack` in the same turn after calling built-in `image_gen`.
- In the next turn, after the generated image has been saved/exported as a local file, run `accept-generated`.

## Scriptable Automation

For full automation, use:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py generate-raw-batch \
  --plan output/meme-plan.json \
  --provider openai_images_api \
  --concurrency 3
```

This reads the plan's `image_prompts`, calls the system image generation CLI/API, writes the planned raw filenames, and records `generated-index.json`. Then run the normal QC/build flow.
