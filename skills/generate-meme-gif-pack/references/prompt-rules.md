# Prompt Rules

The model should produce clean visual material only. Captions are added by the deterministic processor so Chinese text stays readable and consistent. The agent should actively call `image_gen`; the local script plans prompts and postprocesses files, but it does not replace the image model.

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
4. `image_gen` -> one semantic sheet per sticker
5. `build-pack --source-layout 1x4` -> Chinese captions, GIF loops, WeChat package

## Raw Image Prompt Pattern

Use this structure for each sticker:

1. “Stylized sticker character based on the uploaded reference image...”
2. State style, persona, expression, and action.
3. State sheet behavior: default `1x4` motion sheet with 4 acting beats.
4. State sprite-forge-style sheet constraints: exact grid count, no borders, same identity, same bounding box, same pixel scale, no edge crossing, clear margin.
5. State constraints: **no text**, no Chinese characters, no labels, no official logo, no brand mark, no speech bubbles, no UI, uncluttered background, full character visible, large readable face, centered composition.
6. State WeChat readability: must read clearly at 240x240.

## Motion Sheet Rules

The high-quality path uses semantic motion sheets, adapted from `generate2dsprite`:

- default sheet: `1x4`, exactly 4 equal cells in one row
- richer sheet: `2x2` for compact action/reaction, or `2x3` for bigger transformation/cast-style moments
- no borders, no separator lines, no numbered cells
- same character identity, same outfit cues, same color anchors, same bounding box, and same pixel scale across frames
- the entire character, prop, effect, sweat drop, paper stack, chart, laptop, or glow must fit fully inside each cell
- leave clear margin on all four sides; nothing may cross a cell edge
- use a 100% solid flat `#FF00FF` background when possible so local processing can remove it
- each frame should be a different acting beat, not a random new illustration

Default `1x4` acting rhythm:

1. readable starting expression
2. action starts
3. peak meme reaction
4. settle pose that loops cleanly back to frame 1

## Good Raw Prompt Example

```text
Stylized clean sticker character based on the uploaded reference image, recognizable hair shape and glasses, office worker energy, centered on a simple transparent-friendly background. The character stares blankly with a tiny forced nod, as if saying "I understand" while clearly not understanding. Large readable head, simple body pose, crisp outline, expressive eyes, no text, no Chinese characters, no labels, no speech bubbles, no UI, no clutter, designed to read at 240x240.
```

## Good Text Concept Prompt Example

```text
Create one raw no-text 1x4 motion sheet for a Chinese WeChat animated meme GIF sticker pack.
Character card: text_concept warm geometric AI assistant mascot with cream body, coral accents, friendly abstract face, tiny paper-stack anxiety, original character, no official logo. Keep the same head shape, color anchors, body proportions, line weight, and facial feature logic across every sticker.
Persona context: 科研打工人; useful visual cues: papers, literature review, group meeting pressure, charts, revision anxiety.
Meme item: 文献山. Chat send scenario: literature keeps multiplying. The final Chinese caption will be added later by a local processor; do not draw any text.
Motion sheet rules: exactly 4 equal cells in a 1x4 grid, no borders, same character identity, same bounding box, same pixel scale, clear magenta margin, nothing crosses a cell edge.
Frame 1: the mascot notices one small paper stack, worried eyes.
Frame 2: the stack grows quickly around the mascot.
Frame 3: the mascot is half buried, eyes wide and panicked.
Frame 4: the mascot pops back up exhausted, loopable return pose.
Composition: one character only, centered, full character or large bust visible, oversized readable face, crisp silhouette, simple transparent-friendly background, high contrast, designed to read at 240x240.
Hard negative rules: no text, no words, no Chinese characters, no Latin letters, no captions, no labels, no watermark, no official logo, no brand mark, no UI, no speech bubbles.
```

## Animation Guidance

- Prefer semantic tiny loops: blink, nod, shake, sweat drop, typing escalation, document hit, paper pile squash, chart droop, progress bar wobble.
- Avoid large camera moves, complex backgrounds, or multi-character scenes.
- Do not depend on tiny props for the joke; text and expression carry the meme.
- If identity drifts between frames, regenerate with stricter same bounding box / same pixel scale rules.
- If speed matters, ask `image_gen` for an exact `4 columns by 6 rows` contact sheet of static poses, then run `meme_pack.py split-sheet --rows 6 --cols 4`. Keep generous whitespace so each crop contains one centered pose. This is a preview path, not the best final-quality path.
- `build-pack` reads motion sheets with `--source-layout 1x4`, `2x2`, or `2x3`; single static sources fall back to a simple bounce loop.

## Rejection Rules

Regenerate or replace any raw image if:

- face no longer resembles the character card
- subject is too small
- model drew text
- sheet has the wrong grid count
- sheet has borders, separator lines, or numbered cells
- character scale or bounding box changes randomly between frames
- body parts, props, or effects cross cell edges
- gesture cannot be understood without explanation
- background dominates the character
- pose feels like an illustration, not a sendable reaction
