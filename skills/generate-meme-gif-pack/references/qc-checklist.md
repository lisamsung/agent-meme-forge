# QC Checklist

## Raw Sheet QC

Reject or regenerate when:

- layout does not match declared `2x2`, `1x4`, `2x4`, or `4x4`
- cell is blank or subject is too small
- fake checkerboard transparency appears
- background is not true alpha or clean chroma-key color
- subject touches cell edge
- bbox center, area, or size drift exceeds threshold
- character identity, face, outfit, or scale drifts
- text, watermark, logo, speech bubble, or UI appears

## Continuity QC

Reject or regenerate when:

- adjacent frame RGB/alpha change is too high
- subject area jumps
- bbox center jumps
- loop closure is visibly broken
- prop appears for only one frame
- prop position or area jumps without template allowance
- face/head proxy shape drift is too high
- motion energy is too low for the declared template
- subject or props obscure caption readability

## Final WeChat QC

- Main GIFs: `240x240`, under `500KB`.
- Thumbnails: `120x120`, under `50KB`.
- Cover: `240x240`, under `80KB`.
- Icon: `50x50`, under `30KB`.
- Banner: `750x400`, under `80KB`, no text.
- `manifest.json` and `qc_report.json` show pass for submission.
- Captions are readable at 240px and not clipped.
- Each sticker passes sendability: concrete scenario, short caption, emotional value, visual gag.
