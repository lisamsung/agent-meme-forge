"""Dense real frames: build reference-anchored exposure-sheet prompts and generate them.

Why this exists: an image model can keep a character consistent and draw a whole
animation as ONE sprite sheet, but only if the prompt fights its default to "just
redraw the reference as a single portrait". This module encodes the hard-won prompt
rules (anti-single-portrait, reference anchoring, a smooth motion arc, a clean chroma
background, grid discipline) so callers don't reinvent them per sticker.

Provider-agnostic: all generation goes through ``imagegen_client`` (config-driven
endpoint), so the recipe here is identical whether the painter is jmrai, OpenAI, or a
future backend.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Sibling-script import that works from any cwd / import style (guarded so a long-lived
# host process is not polluted with duplicate sys.path entries).
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
import imagegen_client  # noqa: E402

DEFAULT_ROWS = 2
DEFAULT_COLS = 4
CHROMA_BACKGROUND = "#FF00FF"
DEFAULT_SHEET_SIZE = "1536x1024"  # landscape favours a left-to-right read order for cells
DEFAULT_CANONICAL_SIZE = "1024x1024"


def build_exposure_sheet_prompt(
    action: str,
    *,
    character: str = "the exact character in the provided reference image",
    traits: str = "",
    rows: int = DEFAULT_ROWS,
    cols: int = DEFAULT_COLS,
    background: str = CHROMA_BACKGROUND,
) -> str:
    """Build the sprite-sheet prompt for one sticker's looping animation.

    ``action`` is the meme's motion in plain words (e.g. "a knowing nod, pretending to
    understand"). ``traits`` optionally restates locked details ("same glasses, same
    cap, same gown") for extra identity hold on top of the reference image.
    """
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must each be >= 1")
    count = rows * cols
    trait_line = f" {traits.strip()}" if traits.strip() else ""
    return (
        f"Output a SPRITE SHEET: ONE image that is exactly a {rows}-row by {cols}-column grid of "
        f"{count} EQUAL-sized cells filling the whole image edge to edge with no outer margin, "
        f"read left-to-right then top-to-bottom. Any separation between cells must be the same "
        f"solid {background} as the background, with no visible lines. In EACH of the {count} cells, "
        f"draw {character} at SMALL size with clear empty margin inside the cell so the character "
        f"never touches a cell edge.{trait_line} "
        f"The {count} cells are consecutive frames of ONE short looping animation: {action}. "
        f"Use a smooth motion arc: start neutral, build a small anticipation, reach the peak of "
        f"the action, then settle so the last cell loops cleanly back to the first. Neighboring "
        f"cells differ only SLIGHTLY (continuous motion, not {count} separate drawings). "
        f"Keep the SAME character, same colors, same line style, same scale, and same centered "
        f"position in every cell; only the pose/expression changes. "
        f"CRITICAL: the result MUST be {count} small copies of the character arranged in the "
        f"{rows}x{cols} grid. Do NOT output a single large portrait. "
        f"Solid pure {background} background. No text, no numbers, no borders, no grid lines, "
        f"no mirroring."
    )


def build_canonical_prompt(character: str, *, traits: str = "", background: str = CHROMA_BACKGROUND) -> str:
    """Prompt for the one-per-pack canonical character reference (text -> image)."""
    trait_line = f" {traits.strip()}" if traits.strip() else ""
    return (
        f"A single, front-facing, centered character: {character}.{trait_line} "
        f"Flat sticker illustration style, clean outline, neutral friendly expression, full "
        f"head and upper body visible with clear margin. Solid pure {background} background. "
        f"No text, no border, no grid. One character only."
    )


def generate_canonical(
    character: str,
    out_path: str | Path,
    *,
    config: imagegen_client.ImageProviderConfig,
    traits: str = "",
    size: str = DEFAULT_CANONICAL_SIZE,
) -> Path:
    """Generate the canonical character reference image (text -> image)."""
    prompt = build_canonical_prompt(character, traits=traits)
    return imagegen_client.generate(prompt, out_path, config=config, size=size, extra={"background": "opaque"})


def generate_sheet(
    action: str,
    reference_image: str | Path,
    out_path: str | Path,
    *,
    config: imagegen_client.ImageProviderConfig,
    traits: str = "",
    rows: int = DEFAULT_ROWS,
    cols: int = DEFAULT_COLS,
    size: str = DEFAULT_SHEET_SIZE,
) -> Path:
    """Generate one reference-anchored exposure sheet for a sticker's animation.

    Uses the edits endpoint so the canonical reference holds the character identity.
    ``background=opaque`` because gpt-image-2 has no transparent output; the local
    pipeline chroma-keys the flat background afterwards.
    """
    prompt = build_exposure_sheet_prompt(action, traits=traits, rows=rows, cols=cols)
    return imagegen_client.edit(
        prompt, reference_image, out_path, config=config, size=size, extra={"background": "opaque"}
    )


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate reference-anchored dense-frame sheets.")
    sub = parser.add_subparsers(dest="command", required=True)

    canon = sub.add_parser("canonical", help="Generate the canonical character reference.")
    canon.add_argument("--character", required=True)
    canon.add_argument("--traits", default="")
    canon.add_argument("--out", required=True)
    canon.add_argument("--size", default=DEFAULT_CANONICAL_SIZE)

    sheet = sub.add_parser("sheet", help="Generate one exposure sheet from a reference image.")
    sheet.add_argument("--action", required=True)
    sheet.add_argument("--reference", required=True)
    sheet.add_argument("--traits", default="")
    sheet.add_argument("--out", required=True)
    sheet.add_argument("--rows", type=int, default=DEFAULT_ROWS)
    sheet.add_argument("--cols", type=int, default=DEFAULT_COLS)
    sheet.add_argument("--size", default=DEFAULT_SHEET_SIZE)

    prompt_only = sub.add_parser("prompt", help="Print the exposure-sheet prompt without generating.")
    prompt_only.add_argument("--action", required=True)
    prompt_only.add_argument("--traits", default="")
    prompt_only.add_argument("--rows", type=int, default=DEFAULT_ROWS)
    prompt_only.add_argument("--cols", type=int, default=DEFAULT_COLS)

    for name in ("canonical", "sheet"):
        sp = {"canonical": canon, "sheet": sheet}[name]
        sp.add_argument("--base-url")
        sp.add_argument("--api-key")
        sp.add_argument("--model")

    args = parser.parse_args(argv)
    if args.command == "prompt":
        print(build_exposure_sheet_prompt(args.action, traits=args.traits, rows=args.rows, cols=args.cols))
        return 0
    config = imagegen_client.ImageProviderConfig.from_env(
        base_url=args.base_url, api_key=args.api_key, model=args.model
    )
    if args.command == "canonical":
        out = generate_canonical(args.character, args.out, config=config, traits=args.traits, size=args.size)
    else:
        out = generate_sheet(
            args.action, args.reference, args.out, config=config, traits=args.traits,
            rows=args.rows, cols=args.cols, size=args.size,
        )
    print(f"SAVED {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
