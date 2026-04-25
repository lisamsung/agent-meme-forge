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

Then run `meme_pack.py plan-pack` and use its `image_prompts` with built-in `image_gen`. This is the missing prompt-engineering loop:

1. concept -> character card
2. persona -> sendable meme list
3. meme item -> no-text raw image prompt
4. `image_gen` -> raw images
5. `build-pack` -> Chinese captions, GIF loops, WeChat package

## Raw Image Prompt Pattern

Use this structure for each sticker:

1. “Stylized sticker character based on the uploaded reference image...”
2. State style, persona, expression, and action.
3. State frame behavior: one clean pose or 4-6 simple loop frames.
4. State constraints: **no text**, no Chinese characters, no labels, no official logo, no brand mark, no speech bubbles, no UI, uncluttered background, full character visible, large readable face, centered composition.
5. State WeChat readability: must read clearly at 240x240.

## Good Raw Prompt Example

```text
Stylized clean sticker character based on the uploaded reference image, recognizable hair shape and glasses, office worker energy, centered on a simple transparent-friendly background. The character stares blankly with a tiny forced nod, as if saying "I understand" while clearly not understanding. Large readable head, simple body pose, crisp outline, expressive eyes, no text, no Chinese characters, no labels, no speech bubbles, no UI, no clutter, designed to read at 240x240.
```

## Good Text Concept Prompt Example

```text
Create one raw no-text image for a Chinese WeChat animated meme GIF sticker pack.
Character card: text_concept warm geometric AI assistant mascot with cream body, coral accents, friendly abstract face, tiny paper-stack anxiety, original character, no official logo. Keep the same head shape, color anchors, body proportions, line weight, and facial feature logic across every sticker.
Persona context: 科研打工人; useful visual cues: papers, literature review, group meeting pressure, charts, revision anxiety.
Meme item: 文献山. Chat send scenario: literature keeps multiplying. The final Chinese caption will be added later by a local processor; do not draw any text.
Acting direction: the mascot is buried under a growing pile of papers, eyes wide, tiny exhausted bounce.
Composition: one character only, centered, full character or large bust visible, oversized readable face, crisp silhouette, simple transparent-friendly background, high contrast, designed to read at 240x240.
Hard negative rules: no text, no words, no Chinese characters, no Latin letters, no captions, no labels, no watermark, no official logo, no brand mark, no UI, no speech bubbles.
```

## Animation Guidance

- Prefer tiny loops: blink, nod, shake, sweat drop, keyboard bounce, document hit, progress bar wobble.
- Avoid large camera moves, complex backgrounds, or multi-character scenes.
- Do not depend on tiny props for the joke; text and expression carry the meme.
- If identity drifts between frames, generate one strong still pose and let `meme_pack.py` create the bounce loop.
- If speed matters, ask `image_gen` for an exact `4 columns by 6 rows` contact sheet, then run `meme_pack.py split-sheet --rows 6 --cols 4`. Keep generous whitespace so each crop contains one centered pose.

## Rejection Rules

Regenerate or replace any raw image if:

- face no longer resembles the character card
- subject is too small
- model drew text
- gesture cannot be understood without explanation
- background dominates the character
- pose feels like an illustration, not a sendable reaction
