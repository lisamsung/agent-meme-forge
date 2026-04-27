#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
PROVIDER_NAME = "google-ai-studio-web"


def load_plan(plan_path: Path) -> dict[str, Any]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    prompts = plan.get("image_prompts")
    if not isinstance(prompts, list) or not prompts:
        raise ValueError("plan must contain a non-empty image_prompts list")
    for index, prompt in enumerate(prompts, start=1):
        if not prompt.get("raw_image_filename"):
            raise ValueError(f"image_prompts[{index}] is missing raw_image_filename")
        if not prompt.get("prompt"):
            raise ValueError(f"image_prompts[{index}] is missing prompt")
    return plan


def write_prompt_board(
    *,
    plan_path: Path,
    output_path: Path,
    download_dir: Path,
    model: str = "Nano Banana Pro",
    background: str = "#00FF00",
    image_size: str = "2K",
) -> dict[str, Any]:
    plan = load_plan(plan_path)
    prompts = plan["image_prompts"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    download_dir.mkdir(parents=True, exist_ok=True)

    cards = []
    for index, item in enumerate(prompts, start=1):
        prompt = str(item["prompt"])
        target = str(item["raw_image_filename"])
        name = str(item.get("name") or item.get("meme_name") or target)
        caption = str(item.get("caption") or item.get("text") or "")
        scene = str(item.get("send_scene") or item.get("scene") or "")
        template = str(item.get("motion_template") or item.get("motion_type") or "")
        cards.append(
            f"""
      <section class="card" id="item-{index:02d}">
        <div class="card-head">
          <span class="index">{index:02d}</span>
          <div>
            <h2>{html.escape(name)}</h2>
            <p>{html.escape(scene)}</p>
          </div>
        </div>
        <dl>
          <dt>caption</dt><dd>{html.escape(caption)}</dd>
          <dt>motion template</dt><dd>{html.escape(template)}</dd>
          <dt>target filename</dt><dd><code>{html.escape(target)}</code></dd>
        </dl>
        <textarea id="prompt-{index:02d}" spellcheck="false">{html.escape(prompt)}</textarea>
        <button type="button" onclick="copyPrompt('prompt-{index:02d}', this)">Copy prompt</button>
      </section>
"""
        )

    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(str(plan.get("pack_name") or "AI Studio Prompt Board"))}</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f6f7f9; color: #16181d; }}
    header {{ padding: 28px; background: #16181d; color: white; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 24px; }}
    .notice, .card {{ background: white; border: 1px solid #d9dde5; border-radius: 8px; padding: 18px; margin-bottom: 16px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; }}
    .card-head {{ display: flex; gap: 12px; align-items: flex-start; }}
    .index {{ font-weight: 700; background: #00c853; color: #06140a; border-radius: 6px; padding: 6px 8px; }}
    h1, h2, p {{ margin-top: 0; }}
    dl {{ display: grid; grid-template-columns: 120px 1fr; gap: 8px 12px; }}
    dt {{ color: #657085; }}
    dd {{ margin: 0; }}
    code {{ background: #eef1f6; border-radius: 4px; padding: 2px 5px; }}
    textarea {{ width: 100%; min-height: 230px; box-sizing: border-box; resize: vertical; margin: 12px 0; font: 13px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace; }}
    button {{ height: 36px; border: 0; border-radius: 6px; background: #1a73e8; color: white; padding: 0 14px; cursor: pointer; }}
  </style>
</head>
<body>
  <header>
    <h1>Google AI Studio Web Prompt Board</h1>
    <p>Provider: {PROVIDER_NAME}. Use this board with Hermes or a human operator in AI Studio Web.</p>
  </header>
  <main>
    <section class="notice">
      <h2>Operator Settings</h2>
      <p>Model: <strong>{html.escape(model)}</strong>. Use Nano Banana Pro for the first accepted pass; Nano Banana 2 can be used for cheaper previews.</p>
      <p>Recommended parameters: aspect ratio: 1:1; image size: {html.escape(image_size)}; output: PNG; background: flat {html.escape(background)}; generate one 2x2 keypose sheet per prompt.</p>
      <p>Download folder: <code>{html.escape(str(download_dir))}</code></p>
      <p>Do not ask AI Studio to add Chinese text. Captions are added locally by meme_pack.py.</p>
    </section>
    <section class="grid">
      {''.join(cards)}
    </section>
  </main>
  <script>
    async function copyPrompt(id, button) {{
      const el = document.getElementById(id);
      await navigator.clipboard.writeText(el.value);
      const old = button.textContent;
      button.textContent = "Copied";
      setTimeout(() => button.textContent = old, 1200);
    }}
  </script>
</body>
</html>
"""
    output_path.write_text(document, encoding="utf-8")
    return {
        "provider": PROVIDER_NAME,
        "card_count": len(prompts),
        "prompt_board": str(output_path),
        "download_dir": str(download_dir),
    }


def list_download_images(download_dir: Path) -> list[Path]:
    if not download_dir.exists():
        raise ValueError(f"download directory does not exist: {download_dir}")
    return sorted(
        [path for path in download_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS],
        key=lambda path: path.name.lower(),
    )


def _match_strict(downloads: list[Path], prompts: list[dict[str, Any]]) -> list[tuple[Path, str, int]]:
    by_name = {path.name: path for path in downloads}
    matches: list[tuple[Path, str, int]] = []
    missing = []
    for index, item in enumerate(prompts, start=1):
        target = str(item["raw_image_filename"])
        source = by_name.get(target)
        if source is None:
            missing.append(target)
        else:
            matches.append((source, target, index))
    if missing:
        raise ValueError("missing expected AI Studio downloads: " + ", ".join(missing))
    return matches


def _match_ordered(downloads: list[Path], prompts: list[dict[str, Any]]) -> list[tuple[Path, str, int]]:
    expected = len(prompts)
    if len(downloads) != expected:
        raise ValueError(f"expected {expected} image downloads, found {len(downloads)} in ordered mode")
    return [
        (source, str(item["raw_image_filename"]), index)
        for index, (source, item) in enumerate(zip(downloads, prompts, strict=True), start=1)
    ]


def import_downloads(
    *,
    plan_path: Path,
    download_dir: Path,
    source_dir: Path,
    mode: str = "strict",
    limit: int | None = None,
) -> dict[str, Any]:
    plan = load_plan(plan_path)
    prompts = plan["image_prompts"]
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        prompts = prompts[:limit]
    downloads = list_download_images(download_dir)
    if mode == "strict":
        matches = _match_strict(downloads, prompts)
    elif mode == "ordered":
        matches = _match_ordered(downloads, prompts)
    else:
        raise ValueError("mode must be strict or ordered")

    source_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for source, target, index in matches:
        destination = source_dir / target
        shutil.copy2(source, destination)
        items.append(
            {
                "index": index,
                "provider": PROVIDER_NAME,
                "source_file": str(source),
                "target_filename": target,
                "target_file": str(destination),
            }
        )

    index_data = {
        "provider": PROVIDER_NAME,
        "plan": str(plan_path),
        "download_dir": str(download_dir),
        "source_dir": str(source_dir),
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
    (source_dir / "generated-index.json").write_text(
        json.dumps(index_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "provider": PROVIDER_NAME,
        "imported": len(items),
        "planned_prompt_count": len(plan["image_prompts"]),
        "limited_to": limit or len(plan["image_prompts"]),
        "source_dir": str(source_dir),
        "index_file": str(source_dir / "generated-index.json"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Google AI Studio Web handoff helpers for Agent Meme Forge.")
    sub = parser.add_subparsers(dest="command", required=True)

    board = sub.add_parser("prompt-board", help="Write a local HTML prompt board for AI Studio Web operators.")
    board.add_argument("--plan", required=True, type=Path)
    board.add_argument("--output", required=True, type=Path)
    board.add_argument("--download-dir", required=True, type=Path)
    board.add_argument("--model", default="Nano Banana Pro")
    board.add_argument("--background", default="#00FF00")
    board.add_argument("--image-size", default="2K")

    imports = sub.add_parser("import-downloads", help="Copy AI Studio downloads into planned raw-frame filenames.")
    imports.add_argument("--plan", required=True, type=Path)
    imports.add_argument("--download-dir", required=True, type=Path)
    imports.add_argument("--source-dir", required=True, type=Path)
    imports.add_argument("--mode", choices=["strict", "ordered"], default="strict")
    imports.add_argument("--limit", type=int, help="Import only the first N planned prompts, useful for first-3 preview QC.")

    args = parser.parse_args(argv)
    if args.command == "prompt-board":
        result = write_prompt_board(
            plan_path=args.plan,
            output_path=args.output,
            download_dir=args.download_dir,
            model=args.model,
            background=args.background,
            image_size=args.image_size,
        )
    else:
        result = import_downloads(
            plan_path=args.plan,
            download_dir=args.download_dir,
            source_dir=args.source_dir,
            mode=args.mode,
            limit=args.limit,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
