---
name: generate-meme-gif-pack
description: Use when the user wants to turn a reference person, mascot, avatar, or character image into a WeChat-ready animated Chinese meme GIF sticker pack, especially with persona labels, workplace/student/research humor, or strict platform-size constraints.
---

# Generate Meme GIF Pack

Create animated Chinese meme GIF packs from either a reference image or a text-only character concept. The core design rule is: 没人用的表情包就是垃圾表情包. A sticker nobody sends is waste. Prioritize repeatable chat-use cases, clear reaction value, imagination, and fast readability over decorative polish.

## Inputs

Start with a short intake when the user has not already specified the choices. Ask whether they want to upload/use a reference image or create from text, then ask for scene/persona, visual style, pack size, and quality mode. Do not silently default past these choices when the user expects interaction.

Intake-first rule: before `plan-pack`, `image_gen`, or `build-pack`, the agent must ask the user to choose these options unless the user already supplied them or explicitly said to use defaults: input mode/reference image, persona, visual style, pack size/mode, and quality mode. A request such as “做一组表情包试试” is not explicit permission to skip choices.

For terminal users, `plan-wizard` provides the same guided intake:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py plan-wizard
```

Infer only after the user gives a minimal request such as “做科研打工人表情包” and clearly wants the agent to proceed:

- `reference_image`: uploaded person, mascot, avatar, or character image. Use `input_mode=reference_image` when present.
- `subject`: required when no image is uploaded. Use `input_mode=text_concept` for direct text generation, e.g. “warm geometric AI assistant mascot with coral accents, original character, no official logo”.
- `style`: `clean-sticker` default; also `pixel-art`, `chibi`, `retro-msn`, `office-cartoon`, `hand-drawn`.
- `persona`: `科研打工人` default; also `都市丽人`, `打工仔`, `码农`, `学生`, `研究僧`, `早八特困生`, `甲方幸存者`, `会议受害者`, `ddl祭司`.
- `pack_size`: WeChat mode only allows 16 or 24. Default to 24.
- `mode`: `wechat` default, or `self_use`.
- `tone`: default `职场发疯但安全`.
- `source_mode`: default `keyposes`. `keyposes` means image_gen draws 4 stable key poses and the local processor renders the final GIF; `motion_sheet` is the legacy/expert mode for direct `2x4` or `4x4` frame sheets; `single_bounce` is preview-only.
- `keypose_layout`: default `2x2`; also supports `1x4`. This is the preferred raw image layout for submission.
- `render_frame_count`: default `16`; the local processor renders deterministic holds, anticipation, rebound, and loop closure from the key poses.
- `animation_layout`: legacy `motion_sheet` layout, default `2x4`; use `4x4` only when intentionally asking image_gen to draw every frame.
- `quality_mode`: default `submission`; also `standard` or `preview`. Submission requires strict QC, real `2x2`/`1x4` keypose sheets or explicit legacy `2x4`/`4x4` motion sheets, and no single-image bounce fallback.
- `image_provider`: default `codex_builtin_image_gen`. Use `external_files` or `ai_studio_hermes` only when an outside/scriptable provider has already produced local image files that can be accepted and QC'd in the same workflow.

If the user asks for 18 and wants WeChat upload, explain that WeChat albums use 16 or 24, then default to 24 unless they explicitly switch to `self_use`.

## Agent Rules

- Critical tool-boundary rule: Codex built-in `image_gen` is a terminal action in this environment. The agent may call it to generate the next raw keypose image, but do not try to run `accept-generated`, `qc-sheet`, or `build-preview` in the same turn after that call; do not try to run local postprocessing until the next turn has a saved local file.
- `image-2` or `gpt-image-2` is the image model/backend name in some contexts; inside Codex the callable tool is `image_gen`. The script cannot call that tool by itself, and the built-in tool does not behave like a normal shell command that returns a local file path for immediate postprocessing.
- If `image_gen` is unavailable in the session, say that generation is blocked by missing image tooling and return the plan JSON plus exact prompts to run elsewhere.
- Make the character stylized but recognizable: preserve hair, face shape, posture, vibe, and signature details when a reference image exists; for `text_concept`, create an original mascot or character from the concept without copying official logos or exact copyrighted characters.
- Require the user to own or have permission for the reference image when the image depicts a real person.
- Keep humor safe for public WeChat review: no politics, hate, sexual content, slurs, doxxing, medical claims, or direct harassment.
- Do not ask the image model to draw Chinese text. The visual prompt must say **no text**, no captions, no speech bubbles, no UI.
- Write meme copy yourself. Every item needs a concrete sending scenario.
- Treat `meme_quality_bar` and every `sendability_gate` as hard product gates. Each sticker needs a reuse trigger, emotional value, creative hook, and visual gag; if it is only cute or decorative, rewrite it before generation.
- If the user has not provided choices, ask the intake questions explicitly before generation: reference image or text concept, persona/scene, style, WeChat or self-use, count, quality mode, and image provider. Only infer defaults without asking when the user says to use defaults or gives a minimal request and clearly wants immediate automatic generation.
- Use `scripts/meme_pack.py plan-pack` to write the meme entries, character card, and per-sticker `image_gen` prompts.
- Use `scripts/meme_pack.py plan-wizard` when the user wants a command-line guided setup instead of agent chat intake.
- Use built-in `image_gen` for raw no-text keypose sheets by default, but treat each call as a handoff point. Before calling it, identify the planned prompt index and `raw_image_filename`; after it runs, resume in the next turn when the user has saved/exported a local image file.
- In the next turn, run `scripts/meme_pack.py accept-generated`; this copies the saved image to the planned `raw_image_filename` and writes `generated-index.json`.
- If `image_gen` returns only an attachment with no usable local file path, ask the user to save/export the attachment locally before QC. Do not pretend `qc-sheet` can read an unsaved chat attachment.
- Prefer one semantic keypose sheet per sticker: 4 stable poses that the local processor can turn into a 12/16-frame loop. Single-pose sources are allowed only for fast previews or fallback.
- Keypose sheets must use exact grid count, same character identity, same bounding box, same pixel scale, clear margins, no cell-edge crossing, and no text.
- A `2x2` or `1x4` source image is an intermediate raw keypose sheet, not final delivery. Do not present the four-cell sheet as the finished sticker pack unless the user is explicitly debugging raw sources.
- Final handoff must point to `preview.html`, `named-gifs/*.gif`, and `wechat-submit/main/*.gif`. The user-facing deliverable is a 240x240 animated GIF, not a four-cell sheet.
- For subtle reactions such as blink, nod, loading, or blank stare, use `motion_profile=micro`: stable character anchor, no lateral drift, but medium-readable expression and small posture changes. A blink/nod should visibly change eyelids, pupils, glasses, shoulders, mouth, or head angle; it must not become a nearly static sticker.
- For exaggerated reactions, use a stronger motion template and 16-frame local rendering first. Direct `4x4`/16-frame image_gen sheets are legacy/expert mode because they often create jumpy, unrelated frames.
- Default high-frequency templates now include local non-text effects: `soul_offline` adds a multi-frame soul puff, `loading_loop` adds continuous loading dots, and `pretend_understand` adds sweat/awkward lines. These are represented in plan output as `local_effects` and protected by `qc_policy`.
- Timing defaults: 8-frame GIFs use about 170ms per frame; 16-frame GIFs use about 150ms per frame so the full loop is readable rather than rushed.
- Micro-motion QC is stricter than normal action QC. If center drift is visible, regenerate; do not treat drifting across the cell as intentional motion.
- For Codex `image_gen` motion sheets, prefer a pure solid `#FF00FF` background unless the tool is confirmed to export real alpha transparency to a local PNG. This avoids the common failure where the model draws a visible checkerboard instead of real transparency.
- ChatGPT Images can be asked for transparent background; API model support varies, and `gpt-image-2` should use solid flat `#FF00FF` fallback plus local cleanup because it does not support true transparent background.
- For API models that support transparent output, request an alpha-capable format such as PNG or WebP, for example with `background: "transparent"` and `output_format: "png"`.
- Reject fake checkerboard transparency and visible separator lines. They are just pixels, not alpha transparency or valid motion-sheet structure.
- Run `qc-sheet` and build/continuity QC on the first 3 generated keypose sheets before generating the full planned pack. Regenerate anything that fails layout, transparency, edge-touch, bbox drift, loop closure, motion energy, prop position jump, prop lifecycle, face/head shape drift, or readability checks.
- The first 3 are a QC checkpoint, not a stopping point. If the user requested a full pack, do not end the task after the first-3 preview. With built-in `image_gen`, continue across turns after each exported file is available; only `external_files` or `ai_studio_hermes` may continue to the remaining prompts in the same workflow.
- For WeChat submission, use `--quality-mode submission --strict-qc`. Single-image `single_bounce` output is preview-only.
- WeChat output must include numbered upload files and readable named GIF files.
- WeChat platform upload is an optional last-mile workflow. When the user explicitly asks to submit to the WeChat Sticker Open Platform, read `references/wechat-platform-upload.md` and use Playwright with headed Microsoft Edge plus the user's QR-login session. Do not use unofficial WeChat APIs. If an in-app browser automation tool is blocked on `sticker.weixin.qq.com`, fall back to Playwright CLI.
- Before final platform submission, verify metadata: `版权归属` must be the actual rights-holder/account/legal subject name, not only `原创`; photo-derived or portrait-like female subjects should use `人物角色 - 女人`; if `接受赞赏` is enabled, fill the reward prompt and upload the reward guide and thanks images.

## Workflow

1. Read references:
   - `references/wechat-spec.md` for output constraints.
   - `references/wechat-platform-upload.md` for optional browser submission to WeChat.
   - `references/personas.md` and `references/meme-library.md` for pack planning.
   - `references/styles.md` and `references/prompt-rules.md` for visual prompts.
2. Choose interactively or create a plan. For a guided command-line flow:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py plan-wizard
```

For a text-only concept:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py plan-pack \
  --subject "warm geometric AI assistant mascot with cream body and coral accents, original character, no official logo" \
  --persona 科研打工人 \
  --style clean-sticker \
  --pack-size 24 \
  --mode wechat \
  --pack-name AI科研打工搭子 \
  --source-mode keyposes \
  --keypose-layout 2x2 \
  --render-frame-count 16 \
  --quality-mode submission \
  --output output/ai-research-plan.json
```

For a reference image, add `--reference-image path/to/reference.png` and describe the key traits in `--subject`.
3. Review the generated plan:
   - `character_card`: identity traits, silhouette, color anchors, expression range, forbidden drift.
   - `items`: meme names, captions, keywords, use scenes, motion hints.
   - `animation`: source mode, keypose layout, and rendered frame count; default `keyposes` / `2x2` / 16 frames.
   - `image_prompts`: one keypose prompt per sticker for `image_gen`, plus motion template, `local_effects`, `qc_policy`, and local timeline.
   - `meme_quality_bar` and each prompt's `sendability_gate`: the usefulness test for whether this sticker deserves to exist.
   - `requires_agent_tooling`: confirms the image provider and whether same-turn postprocessing is supported.
   - `image_handoff`: exact `accept-generated` command template, terminal action boundary, next turn resume note, and `generated-index.json` audit path.
4. Plan 24 entries:
   - 12 common high-frequency chat reactions.
   - 8 persona-specific jokes.
   - 4 reusable filler reactions.
5. Generate and QC raw images:
   - For built-in `image_gen`, call the tool only as the final action of the current turn for the next required `image_prompts` item. Do not batch all prompts and do not expect same-turn postprocessing.
   - Do not stop after writing the plan; the plan is only an intermediate artifact.
   - Default quality path: one `2x2` no-text keypose sheet per sticker. The local processor renders the final 16-frame loop from a motion template such as `soul_offline`, `loading_loop`, or `pretend_understand`.
   - The processor adds template-level comic effects locally rather than asking image_gen to invent them. Keep the raw keyposes clean; let local rendering add soul puff, loading dots, sweat drops, or awkward lines across multiple frames.
   - Do not let image_gen freely invent 16 final frames unless you intentionally switch to legacy `--source-mode motion_sheet`. Four stable key poses with deterministic local motion are more reliable than 16 unrelated AI drawings.
   - Label raw `2x2`/`1x4` keypose PNGs as intermediate source material when showing progress. The final user preview starts at `preview.html`; the finished files live in `named-gifs/` and `wechat-submit/main/`.
   - For a fast first pass only, one 4x6 contact sheet of static poses is acceptable; split it with `split-sheet` before `build-pack`.
   - For Codex `image_gen`, ask for a pure solid `#FF00FF` background by default. Use transparent PNG only when the current tool can prove it exports real alpha to disk. If using ChatGPT Images directly or an API model that supports transparency, transparent PNG is acceptable; if using `gpt-image-2` or another model/tool that cannot output true alpha, use a solid flat `#FF00FF` background and let the processor remove it locally.
   - After each generated image is available as a local file in a later turn, run `accept-generated` so it lands at the planned raw filename.
   - Run `qc-sheet` on those first 3 accepted keypose sheets. Then run `build-preview --strict-continuity-qc --preview-count 3` so final animation continuity is checked before batch generation. Do not use full `build-pack` with only 3 sources; full builds refuse to reuse source images automatically. If a sheet fails, use its `regenerate_hint` from the plan and generate again.
   - If the first 3 look technically correct but not worth sending, revise their captions, visual gags, or motion plans before continuing. Technical pass does not override the sendability gate.
   - Continue to the remaining planned sheets only after the first 3 pass QC. For built-in `image_gen`, this continuation is across turns; for `external_files` or `ai_studio_hermes`, it can be in the same workflow. Do not report the task as done at this checkpoint unless the user explicitly requested a first-3 preview only.

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py accept-generated \
  --plan output/ai-research-plan.json \
  --index 1 \
  --image path/to/generated-image.png \
  --source-dir output/raw-frames/AI科研打工搭子
```

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py qc-sheet \
  --input output/raw-frames/AI科研打工搭子/01-收到离线-2x2.png \
  --source-mode keyposes \
  --source-layout 2x2 \
  --motion-profile micro \
  --quality-mode submission \
  --output output/qc/01-qc.json
```
6. Build the pack:

First build the explicit first-3 preview:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-preview \
  --source-dir output/raw-frames/AI科研打工搭子 \
  --output-dir output/preview-first-3 \
  --persona 科研打工人 \
  --style clean-sticker \
  --pack-name AI科研打工搭子前三张 \
  --preview-count 3 \
  --source-mode keyposes \
  --keypose-layout 2x2 \
  --source-layout auto \
  --render-frame-count 16 \
  --quality-mode submission \
  --strict-qc \
  --strict-continuity-qc
```

Only continue after `output/preview-first-3/preview.html` looks sendable and stable. This preview is a checkpoint, not completion. For a full pack request, keep going across the project workflow until every planned prompt has an accepted source image and full `build-pack` succeeds. Do not promise same turn continuation when using built-in `image_gen`; same-turn continuation applies only to `external_files` or `ai_studio_hermes`. Full `build-pack` requires one accepted source image per sticker; it must not silently loop the first three images.

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
  --source-mode keyposes \
  --keypose-layout 2x2 \
  --source-layout auto \
  --render-frame-count 16 \
  --quality-mode submission \
  --strict-qc \
  --strict-continuity-qc
```

7. QC before returning:
   - For default packs, inspect `manifest.json`: `source_mode` should be `keyposes`, `animation_source` should be `keyposes`, `source_layout` should be `2x2`, `source_frame_count` should be `4`, and `rendered_frame_count` should be `16`.
   - Return `preview.html`, `named-gifs/表情名.gif`, and `wechat-submit/main/01.gif ...` first. Raw keypose sheets are only QC/debug evidence and must not be described as final stickers.
   - Open several GIFs and verify the face/character still reads at 240px.
   - Check every main GIF is 240x240 and below 500KB.
   - Check thumbnails are 120x120 and below 50KB.
   - Check the text is readable and not clipped.
   - Inspect `qc_report.json`: every item should be `pass` for submission, and every item’s `continuity_qc_status` should be `pass`; `prop_position_jump`, `prop_area_jump`, `face_shape_drift_score`, and `max_head_center_step_px` should stay below the template thresholds.
   - Reject weak jokes. Replace any entry that is only decorative or has no obvious send scenario.
   - Reject any GIF that is visually polished but not useful as a chat reply.
8. Optional WeChat platform upload:
   - Only do this when the user asks to submit or upload to WeChat Sticker Open Platform.
   - Use the Playwright runbook in `references/wechat-platform-upload.md`.
   - Stop for user-owned boundaries such as QR login, CAPTCHA, real-name/payment-account prompts, or any unexpected legal confirmation.
   - Save first, confirm the metadata changed in the preview, then click `提交` when the user has authorized submission.

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
  wechat-submit/reward-guide.png    # optional when accepting rewards
  wechat-submit/reward-thanks.png   # optional when accepting rewards
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
