# Prompt Rules

The model should produce clean visual material only. Captions are added by the deterministic processor so Chinese text stays readable and consistent. The agent MUST actively call `image_gen` when the user asked for actual sticker generation; the local script plans prompts and postprocesses files, but it does not replace the image model. Do not stop after plan generation unless image tooling is unavailable. The product rule is strict: if it is only cute or decorative and nobody would send it in chat, reject it.

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

Then run `meme_pack.py plan-pack` and use its `image_prompts` with built-in `image_gen`. This is the prompt-engineering loop:

1. concept -> character card
2. persona -> sendable meme list
3. meme item -> no-text motion sheet prompt
4. sendability gate -> reuse trigger, emotional value, creative hook, visual gag
5. `image_gen` -> one semantic sheet per sticker
6. `accept-generated` -> copy the saved image_gen result to the planned `raw_image_filename` and update `generated-index.json`
7. `qc-sheet --source-layout 2x4 --quality-mode submission` -> reject bad sheets before batch generation; use `4x4` for selected 16-frame expressive stickers
8. `build-pack --source-layout 2x4 --quality-mode submission --strict-qc` -> Chinese captions, GIF loops, WeChat package; use `--source-layout 4x4` when the accepted raw sheets are 16-frame sheets

## Raw Image Prompt Pattern

Use this structure for each sticker:

1. “Stylized sticker character based on the uploaded reference image...”
2. State style, persona, expression, and action.
3. State sendability gate: real chat trigger, emotional value, creative hook, and why the motion makes the caption funnier.
4. State sheet behavior: default `2x4` motion sheet with 8 acting beats, or `4x4` with 16 beats when the meme needs stronger pose performance or smoother continuity.
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

## Motion Sheet Rules

The high-quality path uses semantic motion sheets, adapted from `generate2dsprite`:

- default sheet: `2x4`, exactly 8 equal cells in two rows and four columns
- expressive sheet: `4x4`, exactly 16 equal cells for stickers that need bigger pose change, anticipation, overshoot, recovery, and smoother in-betweens
- lighter sheet: `1x4` for compact previews or stricter file-size budgets
- alternate 8-frame sheet: `1x8` when the model handles a wide strip better
- richer alternate sheets: `2x2`, `2x3`, `3x3`, or `4x4` when the user needs a special animation structure
- no borders, no separator lines, no numbered cells
- same character identity, same outfit cues, same color anchors, same bounding box, and same pixel scale across frames
- make neighboring frames feel like in-between animation from one drawing, not separate illustrations
- for blink, nod, blank stare, loading, or other quiet reactions, use medium-readable micro-motion: clear eyelid changes, pupil movement, glasses shift, eyebrow change, shoulder sink, mouth change, or an 8 to 14 pixel head nod
- micro-motion means stable character anchor, not tiny invisible motion; no lateral drift across the cell
- for action reactions, allow visible pose and silhouette changes that match the caption: arms, shoulders, props, squash/stretch, anticipation, overshoot, and recovery
- for 16-frame sheets, every odd/even neighbor should act like an in-between pair; avoid making 16 unrelated drawings or 16 near-identical copies
- no camera cuts, no sudden crop changes, no random new props, and no teleporting hands
- the entire character, prop, effect, sweat drop, paper stack, chart, laptop, or glow must fit fully inside each cell
- leave clear margin on all four sides; nothing may cross a cell edge
- for Codex `image_gen` motion sheets, prefer a pure solid `#FF00FF` background unless the tool is confirmed to export real alpha transparency to a local PNG
- ChatGPT Images can be asked for transparent PNG background in the prompt, but verify that the exported file has real alpha rather than a visible checkerboard
- for API models that support transparent output, use an alpha-capable `output_format` such as `png` or `webp` together with `background: "transparent"`
- `gpt-image-2` does not support true transparent backgrounds, so use a 100% solid flat `#FF00FF` background and let local processing remove it
- reject fake checkerboard transparency patterns and separator lines; a checkerboard drawn into the pixels is not a transparent background
- each frame should be a different acting beat, not a random new illustration

## Motion Sheet QC Rules

The processor now treats QC as a gate, not a suggestion. A raw sheet should pass these checks before it is allowed into a WeChat submission pack:

- exact declared layout, especially `2x4` or `4x4` for `submission`
- every cell has a readable subject
- no visible checkerboard background
- true alpha background, or a clean solid `#FF00FF` chroma key fallback
- no fake checkerboard residue near the subject after cleanup
- no sheet separator line residue after cleanup
- no subject, prop, paper, glow, sweat drop, or effect touches a cell edge
- bbox center, width, height, and alpha area stay within a stable range across frames
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
  --input output/raw-frames/AI科研打工搭子/01-收到离线-2x4.png \
  --source-layout 2x4 \
  --quality-mode submission \
  --output output/qc/01-qc.json
```

If `image_gen` only returns a chat attachment, save/export it to a local file before running `accept-generated`; QC and build commands cannot read an unsaved attachment. If QC fails, regenerate with a stricter prompt: larger face, fewer props, more margin, same bounding box, same pixel scale, no checkerboard, no separator lines, pure `#FF00FF` background or verified real-alpha transparent PNG only.

Transparency note:

- Codex `image_gen` should default to pure solid `#FF00FF` for motion sheets unless the exported file is known to contain real alpha.
- ChatGPT Images can be prompted to make the background transparent, but the saved file still needs QC verification because visible checkerboard pixels are not alpha.
- API behavior is model-specific. For API models with transparent-background support, request `background: "transparent"` and an alpha-capable `output_format`, normally `png` or `webp`.
- `gpt-image-2` does not support `background: "transparent"`; for that model, generate a pure white or pure color background, preferably solid `#FF00FF`, then let the local processor remove it.
- Do not accept visible checkerboard pixels as a transparency substitute.

Default `2x4` acting rhythm:

1. readable starting expression
2. anticipation beat
3. action starts
4. action escalates
5. peak meme reaction
6. rebound from peak reaction
7. settle pose
8. loopable return pose

## Good Raw Prompt Example

```text
Stylized clean sticker character based on the uploaded reference image, recognizable hair shape and glasses, office worker energy, centered on a simple transparent-friendly background. The character stares blankly with a tiny forced nod, as if saying "I understand" while clearly not understanding. Large readable head, simple body pose, crisp outline, expressive eyes, no text, no Chinese characters, no labels, no speech bubbles, no UI, no clutter, designed to read at 240x240.
```

## Good Text Concept Prompt Example

```text
Create one raw no-text 2x4 motion sheet for a Chinese WeChat animated meme GIF sticker pack.
Character card: text_concept warm geometric AI assistant mascot with cream body, coral accents, friendly abstract face, tiny paper-stack anxiety, original character, no official logo. Keep the same head shape, color anchors, body proportions, line weight, and facial feature logic across every sticker.
Persona context: 科研打工人; useful visual cues: papers, literature review, group meeting pressure, charts, revision anxiety.
Meme item: 文献山. Chat send scenario: literature keeps multiplying. The final Chinese caption will be added later by a local processor; do not draw any text.
Motion sheet rules: exactly 8 equal cells in a 2x4 grid, no borders, same character identity, same bounding box, same pixel scale. For Codex image_gen use a pure solid #FF00FF background unless verified real-alpha PNG export is available; no fake checkerboard pattern, no separator lines, nothing crosses a cell edge.
Frame 1: the mascot notices one small paper stack, worried eyes.
Frame 2: the mascot reaches toward the stack with hesitation.
Frame 3: the stack grows quickly around the mascot.
Frame 4: papers start flying around the mascot.
Frame 5: the mascot is half buried, eyes wide and panicked.
Frame 6: paper pile reaches peak chaos around the mascot.
Frame 7: the mascot pops back up exhausted.
Frame 8: the mascot settles with a tiny defeated sigh, loopable return pose.
Composition: one character only, centered, full character or large bust visible, oversized readable face, crisp silhouette, simple transparent-friendly background, high contrast, designed to read at 240x240.
Hard negative rules: no text, no words, no Chinese characters, no Latin letters, no captions, no labels, no watermark, no official logo, no brand mark, no UI, no speech bubbles.
```

## Animation Guidance

- Prefer semantic tiny loops: blink, nod, shake, sweat drop, typing escalation, document hit, paper pile squash, chart droop, progress bar wobble.
- Quiet reaction loops should be slow enough to read. The processor defaults to 170ms frame timing for 8-frame GIFs and 150ms for 16-frame GIFs, so longer sheets smooth the motion without rushing the loop.
- Quiet reactions use `motion_profile=micro` during QC/build. This rejects visible center drift and uses stable alignment so the character does not slide across the GIF.
- Avoid large camera moves, complex backgrounds, or multi-character scenes.
- Do not depend on tiny props for the joke; text and expression carry the meme.
- If identity drifts between frames, regenerate with stricter same bounding box / same pixel scale rules.
- If speed matters, ask `image_gen` for an exact `4 columns by 6 rows` contact sheet of static poses, then run `meme_pack.py split-sheet --rows 6 --cols 4`. Keep generous whitespace so each crop contains one centered pose. This is a preview path, not the best final-quality path.
- `build-pack` reads motion sheets with `--source-layout 2x4`, `4x4`, `1x8`, `1x4`, `2x2`, or `2x3`; single static sources fall back to a simple bounce loop only in `preview` mode.
- WeChat submission should use `build-pack --quality-mode submission --strict-qc`; this rejects `single_bounce`, fake checkerboard backgrounds or residue, separator line residue, edge touch, excessive bbox drift, and weak frame sheets.

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
