---
name: generate-meme-gif-pack
description: Use when the user wants to turn a reference image or text concept into a WeChat-ready animated Chinese meme GIF sticker pack: 16/24 entries, 240x240 GIFs, Chinese captions, sendability-gated humor. TRIGGER: 做表情包, meme包, 微信表情, WeChat sticker, 人物/头像/吉祥物动图. SKIP: single static image, pure logo design, non-Chinese sticker workflows. If the user explicitly asks for Google AI Studio or Hermes, use generate-meme-gif-pack-ai-studio instead.
---

# Generate Meme GIF Pack

Core rule: 没人用的表情包就是垃圾表情包. Every sticker must pass the sendability gate: real chat-use trigger, readable gag, and concrete send scenario.

## Quick Decision

| User request | Route |
|---|---|
| Reference image or text concept -> Chinese meme GIF pack | Run intake, then `plan-pack` or `plan-wizard`. |
| Wants full automation / concurrency / API generation | Use `image_provider=openai_images_api`, then `generate-raw-batch`, then QC/build. |
| Wants Codex built-in image generation | Use `image_provider=codex_builtin_image_gen`; this is interactive and split across turns. |
| Already has raw PNG/GIF files | Use `external_files`, then `accept-generated`/QC/build. |
| Explicit Google AI Studio / Hermes / Nano Banana route | Switch to `generate-meme-gif-pack-ai-studio`. |
| Wants WeChat platform upload | First build and QC locally, then read `references/wechat-platform-upload.md`. |

## Required Intake

Ask these unless the user already answered or explicitly said to use defaults:

- input: reference image or `text_concept`
- persona: e.g. `科研打工人`, `都市丽人`, `码农`, `学生`, `研究僧`
- style: `clean-sticker`, `pixel-art`, `chibi`, `retro-msn`, `office-cartoon`, `hand-drawn`
- mode and count: WeChat uses 16 or 24; 18 is `self_use`
- quality mode: `submission`, `standard`, or `preview`
- image provider: `codex_builtin_image_gen`, `openai_images_api`, `external_files`, or `ai_studio_hermes`

Use `scripts/meme_pack.py plan-wizard` when the user wants command-line guidance.

## Tool Boundary

Codex built-in `image_gen` is a terminal action in this environment: call it only as the final action of the current turn, then resume next turn after the image has been saved/exported locally. Do not run `accept-generated`, `qc-sheet`, or `build-preview` in the same turn after built-in `image_gen`.

For full automation, do not use built-in `image_gen`; use the scriptable `openai_images_api` provider. Details: `references/tool-boundary.md`.

## Required References

Read only what the situation needs:

- `references/workflow.md`: production workflow and command sequence.
- `references/commands.md`: CLI subcommands and examples.
- `references/agent-rules.md`: full agent rules and safety gates.
- `references/qc-checklist.md`: QC, continuity, and final inspection.
- `references/tool-boundary.md`: provider split and automation boundaries.
- `references/wechat-spec.md`: size, naming, and WeChat asset constraints.
- `references/wechat-platform-upload.md`: optional browser upload runbook.
- `references/personas.md`, `styles.md`, `meme-library.md`: content planning.
- `references/prompt-rules.md`: image prompt rules and keypose requirements.
- `references/dense-frames.md`: dense real-frame mode (`--source-mode dense_frames`), the recommended smoothest path.
- `references/pressure-scenarios.md`: common user input -> expected response.

## Output Contract

Final handoff points to the finished preview and GIFs, not raw keypose sheets:

```text
output/my-pack/
  preview.html
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

Raw `2x2`/`1x4` keyposes / keypose sheets are intermediate QC/debug material, not the final deliverable.
Raw image prompts must require no text; Chinese captions are added locally.
