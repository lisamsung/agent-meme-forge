# Prompt Rules

The model should produce clean visual material only. Captions are added by the deterministic processor so Chinese text stays readable and consistent. The local script plans prompts and postprocesses files, but it does not replace the image model. Codex built-in `image_gen` is a terminal action, not a same-turn pipeline step: do not assume the agent can call `image_gen` and then immediately run local QC in the same turn. The product rule is strict: if it is only cute or decorative and nobody would send it in chat, reject it.

## Character Card Prompt

Create a short internal character card before generating pack frames. Two input modes are supported:

- `reference_image`: uploaded person, mascot, avatar, or character image
- `text_concept`: direct text generation from a character concept without an uploaded image
- identity source: uploaded reference image or text_concept
- recognizable traits: hair shape, head shape, face shape, glasses, clothing, posture, color accents, signature props
- style target: chosen style
- do not copy photorealistic identity; make a stylized sticker character
- for `text_concept`, create an original mascot; do not copy official logos, brand marks, or exact copyrighted characters
- keep the same silhouette, outfit cues, and facial proportions across every sticker

## Direct Text Generation

When the user gives only a phrase such as “做一个 Claude 气质的 AI 吉祥物表情包”, do not stop and ask for a photo. Convert it into an original, brand-safe subject first:

```text
warm geometric AI assistant mascot with cream body, coral accents, friendly abstract face, tiny paper-stack anxiety, original character, no official logo, no brand mark
```

Then run `meme_pack.py plan-pack` and use its `image_prompts` with the selected provider. For the default `codex_builtin_image_gen` provider, image generation is a terminal handoff and local acceptance/QC resumes in the next turn after a saved local file is available. This is the prompt-engineering loop:

1. concept -> character card
2. persona -> sendable meme list
3. meme item -> no-text keypose sheet prompt
4. sendability gate -> reuse trigger, emotional value, creative hook, visual gag
5. provider generates one semantic 4-keypose sheet per sticker
6. `accept-generated` -> copy the saved provider result to the planned `raw_image_filename` and update `generated-index.json`
7. `qc-sheet --source-mode keyposes --source-layout 2x2 --quality-mode submission` -> reject bad keypose sheets before batch generation
8. `build-pack --source-mode keyposes --keypose-layout 2x2 --render-frame-count 16 --strict-qc --strict-continuity-qc` -> local motion rendering, Chinese captions, GIF loops, WeChat package

A `2x2` source image is an intermediate raw keypose sheet, not the final deliverable. The final handoff should show `preview.html`, `named-gifs/*.gif`, and `wechat-submit/main/*.gif`; raw keypose PNGs are for QC and debugging only.

The first 3 are a QC checkpoint, not a stopping point. For a full pack, continue after the first-3 preview passes QC, then run the full pack build. With built-in Codex `image_gen`, this happens across turns; same-turn continuation is only for `external_files`, `ai_studio_hermes`, or another provider that already exposes local files.

## Raw Image Prompt Pattern

Use this structure for each sticker:

1. “Stylized sticker character based on the uploaded reference image...”
2. State style, persona, expression, and action.
3. State sendability gate: real chat trigger, emotional value, creative hook, and why the motion makes the caption funnier.
4. State source behavior: default `2x2` keypose sheet with 4 stable poses rendered locally into the 16-frame GIF (robust, any provider), or the recommended `dense_frames` path (~8 real frames in one sheet) for maximum smoothness.
5. State sprite-forge-style sheet constraints: exact grid count, no borders, same identity, same bounding box, same pixel scale, no edge crossing, clear margin.
6. State constraints: **no text**, no Chinese characters, no labels, no official logo, no brand mark, no speech bubbles, no UI, uncluttered background, full character visible, large readable face, centered composition.
7. State WeChat readability: must read clearly at 240x240.

## Sendability Gate

Before calling `image_gen`, every sticker must pass:

- reuse trigger: a real chat moment where someone would send it directly
- emotional value: what relief, sarcasm, agreement, panic, delay, or comfort it gives
- creative hook: the visual idea that makes it more than a caption pasted on a face
- visual gag: a readable action or prop that still works at 240x240

Reject or rewrite if:

- it is only cute or decorative
- it is just an abstract mood label
- it depends on private context strangers cannot reuse
- the pose is polished but does not make the caption funnier

## Source-Mode Rules

`keyposes` is the safe default (4 stable poses -> local 16-frame render; works with any provider). For maximum smoothness the **recommended** path is `dense_frames` (~8 real frames in one sheet, locally size- and head-normalized; see `references/dense-frames.md`) when the provider can draw 8 consistent frames. The rules below are for the keypose path:

- default source: `2x2`, exactly 4 key poses
- alternate keypose strip: `1x4`
- key poses are start, anticipation/drift, peak gag, and loopable return
- the model must not draw the final 16 frames; it should draw only stable source poses
- same character identity, same outfit cues, same bounding box, same pixel scale, same prop continuity
- no borders, separator lines, numbered cells, text, UI, speech bubbles, or fake checkerboard
- a `2x2` or `1x4` keypose sheet is intermediate source material, not a finished sticker or preview result
- do not present raw keypose PNGs to the user as the pack outcome; final handoff begins with `preview.html` and animated GIF files
- preferred background for Codex `image_gen`: pure solid `#FF00FF`, unless the exported PNG is verified real alpha
- local renderer creates deterministic holds, tiny scale/rotation changes, rebound, and loop closure
- local renderer also adds template-controlled non-text comic effects through `local_effects`, so image_gen should not invent random one-frame effect props
- default renderer output: 16 frames at about 150ms/frame
- raw `2x4`/`4x4` `motion_sheet` (pre-drawn frames with no local size/head normalization) is legacy and often drifts; for full-frame animation prefer `dense_frames`, which draws real frames AND corrects per-frame size/position drift locally

## Motion Templates

Every sticker should map to a productized motion template before prompting:

- `soul_offline`: bright received pose, hard eyelid droop, shoulder sink, local multi-frame soul puff, loopable empty smile
- `loading_loop`: laptop or task-panel start, drooping eyes, local continuous loading dots near head, awkward frozen smile, focused return
- `pretend_understand`: polite listening nod, slow blink, sideways confused-confidence eyes, local sweat drop or awkward lines, forced thumbs-up or compact hand gesture
- `typing_panic`: keyboard start, speed-up, peak panic typing, exhausted reset
- `fake_smile`: polite neutral, smile lift, mouth-corner twitch, neutral return
- `absurd_recoil`: normal, eyes widen, peak recoil, stunned settle
- `steady_breath`: tense start, inhale, shoulder drop, centered return
- `paper_overflow`: paper stack grows across beats, peak chaos, exhausted return

The prompt must include `motion_template`, `local_effects`, `qc_policy`, four `keypose_beats`, and the continuity acceptance rule. This prevents image_gen from inventing 16 unrelated frames or random one-frame props.

## Motion Sheet Rules

Legacy/expert mode still supports semantic motion sheets, adapted from `generate2dsprite`:

- default sheet: `2x4`, exactly 8 equal cells in two rows and four columns
- expressive sheet: `4x4`, exactly 16 equal cells for stickers that need bigger pose change, anticipation, overshoot, recovery, and smoother in-betweens
- lighter sheet: `1x4` for compact previews or stricter file-size budgets
- alternate 8-frame sheet: `1x8` when the model handles a wide strip better
- richer alternate sheets: `2x2`, `2x3`, `3x3`, or `4x4` only for preview or expert workflows
- no borders, no separator lines, no numbered cells
- same character identity, same outfit cues, same color anchors, same bounding box, and same pixel scale across frames
- make neighboring frames feel like in-between animation from one drawing, not separate illustrations
- for blink, nod, blank stare, loading, or other quiet reactions, use medium-readable micro-motion: clear eyelid changes, pupil movement, glasses shift, eyebrow change, shoulder sink, mouth change, or an 8 to 14 pixel head nod
- micro-motion means stable character anchor, not tiny invisible motion; no lateral drift across the cell
- for action reactions, allow visible pose and silhouette changes that match the caption: arms, shoulders, props, squash/stretch, anticipation, overshoot, and recovery
- for direct 16-frame sheets, every odd/even neighbor should act like an in-between pair; avoid making 16 unrelated drawings or 16 near-identical copies
- no camera cuts, no sudden crop changes, no random new props, and no teleporting hands
- the entire character, prop, effect, sweat drop, paper stack, chart, laptop, or glow must fit fully inside each cell
- leave clear margin on all four sides; nothing may cross a cell edge
- for Codex `image_gen` motion sheets, prefer a pure solid `#FF00FF` background unless the tool is confirmed to export real alpha transparency to a local PNG
- ChatGPT Images can be asked for transparent PNG background in the prompt, but verify that the exported file has real alpha rather than a visible checkerboard
- for API models that support transparent output, use an alpha-capable `output_format` such as `png` or `webp` together with `background: "transparent"`
- `gpt-image-2` does not support true transparent backgrounds, so use a 100% solid flat `#FF00FF` background and let local processing remove it
- reject fake checkerboard transparency patterns and separator lines; a checkerboard drawn into the pixels is not a transparent background
- each frame should be a different acting beat, not a random new illustration

## Motion and Continuity QC Rules

The processor now treats QC as a gate, not a suggestion. A raw sheet should pass these checks before it is allowed into a WeChat submission pack:

- exact declared layout: `2x2`/`1x4` for keyposes, `2x4`/`4x2`/`4x4` for `dense_frames`, or `2x4`/`4x4` for legacy `motion_sheet`
- every cell has a readable subject
- no visible checkerboard background
- true alpha background, or a clean solid `#FF00FF` chroma key fallback
- no fake checkerboard residue near the subject after cleanup
- no sheet separator line residue after cleanup
- no subject, prop, paper, glow, sweat drop, or effect touches a cell edge
- bbox center, width, height, and alpha area stay within a stable range across frames
- final rendered animation has no excessive RGB/alpha jump between neighboring frames
- final rendered animation has no sudden subject-area jump, center jump, one-frame-only prop, or bad loop closure
- final rendered animation has no prop position jump, prop area jump, or too-short prop lifecycle
- final rendered animation has no face/head shape drift; the QC reports `face_shape_drift_score` and `max_head_center_step_px`
- `soul_offline`, `loading_loop`, and `pretend_understand` allow stronger local acting than generic micro-motion, but only under their template-level `qc_policy`
- final rendered animation has enough motion energy to avoid fake static GIFs
- no isolated edge debris or tiny leftover color noise after background removal
- the final subject leaves the bottom caption zone clear

Use the first three generated sheets as the quality probe:

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
  --quality-mode submission \
  --output output/qc/01-qc.json
```

Build the first three as an explicit preview before generating the rest:

```bash
python skills/generate-meme-gif-pack/scripts/meme_pack.py build-preview \
  --source-dir output/raw-frames/AI科研打工搭子 \
  --output-dir output/preview-first-3 \
  --preview-count 3 \
  --source-mode keyposes \
  --keypose-layout 2x2 \
  --quality-mode submission \
  --strict-qc \
  --strict-continuity-qc
```

If built-in Codex `image_gen` is used, treat the call as terminal action: generate the next keypose sheet as the final action, then resume in the next turn after the image is saved/exported to a local file. QC and build commands cannot read an unsaved attachment. If QC fails, regenerate with a stricter prompt: larger face, fewer props, more margin, same bounding box, same pixel scale, no checkerboard, no separator lines, pure `#FF00FF` background or verified real-alpha transparent PNG only.

If the user requested a complete 16/24-pack, do not end the task after the first-3 preview. The preview only decides whether to continue, regenerate, or revise the plan; it is not the full pack deliverable.

Transparency note:

- Codex `image_gen` should default to pure solid `#FF00FF` for motion sheets unless the exported file is known to contain real alpha.
- ChatGPT Images can be prompted to make the background transparent, but the saved file still needs QC verification because visible checkerboard pixels are not alpha.
- API behavior is model-specific. For API models with transparent-background support, request `background: "transparent"` and an alpha-capable `output_format`, normally `png` or `webp`.
- `gpt-image-2` does not support `background: "transparent"`; for that model, generate a pure white or pure color background, preferably solid `#FF00FF`, then let the local processor remove it.
- Do not accept visible checkerboard pixels as a transparency substitute.

Default keypose rhythm:

1. readable starting expression
2. anticipation, droop, drift, or pre-reaction
3. peak meme gag
4. loopable return pose

## Good Raw Prompt Example

```text
Stylized clean sticker character based on the uploaded reference image, recognizable hair shape and glasses, office worker energy, centered on a simple transparent-friendly background. The character stares blankly with a tiny forced nod, as if saying "I understand" while clearly not understanding. Large readable head, simple body pose, crisp outline, expressive eyes, no text, no Chinese characters, no labels, no speech bubbles, no UI, no clutter, designed to read at 240x240.
```

## Good Text Concept Prompt Example

```text
Create one raw no-text 2x2 keypose sheet for a Chinese WeChat animated meme GIF sticker pack.
Character card: text_concept warm geometric AI assistant mascot with cream body, coral accents, friendly abstract face, tiny paper-stack anxiety, original character, no official logo. Keep the same head shape, color anchors, body proportions, line weight, and facial feature logic across every sticker.
Persona context: 科研打工人; useful visual cues: papers, literature review, group meeting pressure, charts, revision anxiety.
Meme item: 文献山. Chat send scenario: literature keeps multiplying. The final Chinese caption will be added later by a local processor; do not draw any text.
Motion template: paper_overflow. Keypose sheet rules: exactly 4 key poses in a 2x2 grid, no borders, same character identity, same bounding box, same pixel scale. Do not generate the final 16 animation frames; the local processor will render the 16-frame GIF. For Codex image_gen use a pure solid #FF00FF background unless verified real-alpha PNG export is available; no fake checkerboard pattern, no separator lines, nothing crosses a cell edge.
Key pose 1: the mascot notices one small paper stack, worried eyes.
Key pose 2: the paper stack grows but stays near the mascot.
Key pose 3: papers surround the mascot at peak chaos, no edge crossing.
Key pose 4: the mascot pops back exhausted, papers settle for loop.
Composition: one character only, centered, full character or large bust visible, oversized readable face, crisp silhouette, simple transparent-friendly background, high contrast, designed to read at 240x240.
Hard negative rules: no text, no words, no Chinese characters, no Latin letters, no captions, no labels, no watermark, no official logo, no brand mark, no UI, no speech bubbles.
```

## Animation Guidance

- Prefer semantic tiny loops: blink, nod, shake, sweat drop, typing escalation, document hit, paper pile squash, chart droop, progress bar wobble.
- Prefer four stable key poses plus local rendering over asking image_gen for 16 final frames.
- Quiet reaction loops should be slow enough to read. The processor defaults to 170ms frame timing for 8-frame GIFs and 150ms for 16-frame GIFs, so longer sheets smooth the motion without rushing the loop.
- Quiet reactions use `motion_profile=micro` during QC/build. This rejects visible center drift and uses stable alignment so the character does not slide across the GIF.
- Avoid large camera moves, complex backgrounds, or multi-character scenes.
- Do not depend on tiny props for the joke; text and expression carry the meme.
- If identity drifts between frames, regenerate with stricter same bounding box / same pixel scale rules.
- Push the key poses into an acting arc: start, anticipation, peak gag, loopable recovery. A stable but boring four-pose sheet should be regenerated.
- Effects or props must persist across adjacent key poses or local timeline frames. A prop that appears in exactly one final frame is a continuity failure.
- Template effects should be local renderer responsibilities: `soul_puff`, `loading_dots`, `sweat_drop`, and `awkward_lines` are added after keypose cleanup, then checked for prop lifecycle, prop position jump, prop area jump, and face/head shape drift.
- If speed matters, ask `image_gen` for an exact `4 columns by 6 rows` contact sheet of static poses, then run `meme_pack.py split-sheet --rows 6 --cols 4`. Keep generous whitespace so each crop contains one centered pose. This is a preview path, not the best final-quality path.
- `build-preview` is the only intended path for the first 3 sheets; it writes `preview.html` and does not pretend 3 sources are a full pack.
- `build-pack` reads keypose sheets with `--source-mode keyposes --keypose-layout 2x2`; legacy motion sheets use `--source-mode motion_sheet --source-layout 2x4` or `4x4`; single static sources fall back to a simple bounce loop only in `preview` mode.
- Full `build-pack` runs require one accepted source image per entry and should fail if the source directory is incomplete.
- WeChat submission should use `build-pack --source-mode keyposes --quality-mode submission --strict-qc --strict-continuity-qc`; this rejects `single_bounce`, fake checkerboard backgrounds or residue, separator line residue, edge touch, excessive bbox drift, jumpy frames, bad loop closure, and weak frame sheets.

## Rejection Rules

Regenerate or replace any raw image if:

- face no longer resembles the character card
- subject is too small
- model drew text
- sheet has the wrong grid count
- sheet has borders, separator lines, or numbered cells
- character scale or bounding box changes randomly between frames
- body parts, props, or effects cross cell edges
- transparent output has colored halos, or magenta fallback leaves visible red/pink edge spill after processing
- the image shows a checkerboard background as visible pixels instead of real alpha transparency
- gesture cannot be understood without explanation
- background dominates the character
- pose feels like an illustration, not a sendable reaction
