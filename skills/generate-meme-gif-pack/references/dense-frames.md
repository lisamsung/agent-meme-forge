# Dense real frames (`--source-mode dense_frames`)

The smoothest path: the image model draws ~8 **genuinely different real animation frames** as
ONE exposure sheet, and the local processor assembles them. No faked in-betweening — every frame
is a real drawing, so motion reads as continuous instead of twitchy. This is the recommended mode
for new packs.

## When to use which source mode

| mode | what the model draws | smoothness | use when |
| --- | --- | --- | --- |
| `dense_frames` | 8 real frames in one 2x4 sheet | highest | default; most characters |
| `keyposes` | 4 stable keyposes, processor animates | medium | tight identity control, simple loops |
| `motion_sheet` | pre-drawn frames, no size fix | medium | legacy |
| `single_bounce` | one still | preview only | quick preview, never submission |

## End-to-end flow

```
plan-pack --source-mode dense_frames   # per-meme exposure-sheet prompts (+ character card)
        ↓
generate the sheets                    # automated provider OR dense_frames.py (see below)
        ↓
qc-sheet --source-mode dense_frames    # accept the first few, regenerate fails
        ↓
build-pack --source-mode dense_frames --source-layout 2x4 --strict-qc --strict-continuity-qc
        ↓
WeChat submission package + GIFs + manifest/qc_report
```

## Two ways to generate the sheets

1. **Through the plan (recommended, scriptable).** `plan-pack --source-mode dense_frames` emits one
   exposure-sheet prompt per meme (character card + expressive per-frame acting plan + the dense
   recipe). Feed those prompts to your provider, e.g. via `generate-raw-batch`.
2. **Directly, with `scripts/dense_frames.py`.** Provider-agnostic (config via `MEME_IMAGE_*` /
   `OPENAI_*` env or args). Best for reference-anchored identity:
   - `dense_frames.py canonical --character "…" --out canonical.png` — one canonical reference.
   - `dense_frames.py sheet --action "…" --reference canonical.png --out sheet.png` — a
     reference-anchored 2x4 sheet (uses the images.edit endpoint, the strongest identity lever).

## The recipe the prompt enforces (why dense works)

- **One sheet, all frames in one generation** — the cheapest cross-frame consistency lever (the
  model self-references across cells). Generating frames separately drifts worst.
- **2x4 (8 frames) is the sweet spot**; 4x4 (16) only for clean cyclic actions. `DENSE_FRAME_LAYOUTS
  = {2x4, 4x4}` at submission.
- **Anti-single-portrait** — a complex character makes the model want to redraw ONE big portrait
  and ignore the grid, so the prompt insists: "N small copies, do NOT output a single large
  portrait."
- **Engineer the loop** — last cell ≈ first cell; don't rely on GIF looping to hide a jump.
- **Reference anchoring** beats text for identity — feed a canonical character image into every call.
- **`#FF00FF` background, not transparency** — gpt-image-2 cannot export real alpha; the processor
  chroma-keys the flat magenta. A non-magenta dense sheet is rejected at submission (regenerate).
  Avoid pure `#FF00FF` *in the character palette* — it gets keyed out.

## What the local processor does (`normalize_dense_frames` → assembly)

1. **Slice** the sheet into cells; reject if any cell came back blank (the model dropped a frame).
2. **Size-register** — gpt-image-2 has ~5% per-cell size drift that reads as 忽大忽小; every subject
   is scaled to one uniform height.
3. **Head-anchor (x only)** — a swinging arm/prop changes the silhouette, and bbox-centering would
   convert that into a head sway. The processor anchors horizontally on the head so it holds still
   while the arm moves; vertical stays centered so intentional nods survive. This is gated by a
   placement comparison (adopted only if it steadies the head without adding body swing), so a
   large off-center prop falls back to plain bbox-centering instead of being shoved off-center.
   Designed for upright characters.
4. **Time** — near-uniform ~11fps with a short breath on the neutral first cell (dense frames
   already encode the easing in the drawing, so they need uniform playback, not pose-hold weighting).
5. **Caption + loop + QC + package** — Chinese caption added locally, continuity QC (first≈last,
   caption-zone clear, area/motion gates), then the WeChat submission package.

## Known limits (current)

- 4x4 (16-frame) dense GIFs can exceed the 500KB cap and lose loop closure under truncation; 2x4
  (the default) stays well under (~100KB).
- Local QC cannot verify *character identity per cell* — that is a generation-time lever (reference
  anchoring + restated traits), not something the processor can catch.
