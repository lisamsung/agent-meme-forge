# Prompt Rules

The model should produce clean visual material only. Captions are added by the deterministic processor so Chinese text stays readable and consistent.

## Character Card Prompt

Create a short internal character card before generating pack frames:

- identity source: uploaded reference image
- recognizable traits: hair shape, face shape, glasses, clothing, posture, color accents
- style target: chosen style
- do not copy photorealistic identity; make a stylized sticker character
- keep the same silhouette, outfit cues, and facial proportions across every sticker

## Raw Image Prompt Pattern

Use this structure for each sticker:

1. “Stylized sticker character based on the uploaded reference image...”
2. State style, persona, expression, and action.
3. State frame behavior: one clean pose or 4-6 simple loop frames.
4. State constraints: **no text**, no Chinese characters, no labels, no speech bubbles, no UI, uncluttered background, full character visible, large readable face, centered composition.
5. State WeChat readability: must read clearly at 240x240.

## Good Raw Prompt Example

```text
Stylized clean sticker character based on the uploaded reference image, recognizable hair shape and glasses, office worker energy, centered on a simple transparent-friendly background. The character stares blankly with a tiny forced nod, as if saying "I understand" while clearly not understanding. Large readable head, simple body pose, crisp outline, expressive eyes, no text, no Chinese characters, no labels, no speech bubble, no UI, no clutter, designed to read at 240x240.
```

## Animation Guidance

- Prefer tiny loops: blink, nod, shake, sweat drop, keyboard bounce, document hit, progress bar wobble.
- Avoid large camera moves, complex backgrounds, or multi-character scenes.
- Do not depend on tiny props for the joke; text and expression carry the meme.
- If identity drifts between frames, generate one strong still pose and let `meme_pack.py` create the bounce loop.

## Rejection Rules

Regenerate or replace any raw image if:

- face no longer resembles the character card
- subject is too small
- model drew text
- gesture cannot be understood without explanation
- background dominates the character
- pose feels like an illustration, not a sendable reaction
