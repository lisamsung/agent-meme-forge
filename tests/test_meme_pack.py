from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "generate-meme-gif-pack" / "scripts" / "meme_pack.py"


def load_module():
    spec = importlib.util.spec_from_file_location("meme_pack", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_source_frames(tmp_path: Path, count: int = 24) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    for index in range(count):
        image = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        color = (50 + index * 7 % 180, 80 + index * 5 % 140, 160, 255)
        draw.rounded_rectangle((35, 20, 145, 150), radius=28, fill=color)
        draw.ellipse((65, 45, 80, 62), fill=(255, 255, 255, 255))
        draw.ellipse((105, 45, 120, 62), fill=(255, 255, 255, 255))
        draw.arc((70, 75, 115, 125), 20, 160, fill=(255, 255, 255, 255), width=4)
        image.save(source / f"{index + 1:02d}.png")
    return source


def test_wechat_pack_size_accepts_only_16_or_24():
    meme_pack = load_module()

    assert meme_pack.validate_pack_size(16, "wechat") == 16
    assert meme_pack.validate_pack_size(24, "wechat") == 24
    assert meme_pack.validate_pack_size(18, "self_use") == 18

    with pytest.raises(ValueError, match="16 or 24"):
        meme_pack.validate_pack_size(18, "wechat")


def test_default_entries_include_persona_specific_memes():
    meme_pack = load_module()

    entries = meme_pack.default_entries("码农", 24)

    assert len(entries) == 24
    assert any("bug" in entry.text.lower() or "BUG" in entry.text for entry in entries)
    assert any("生产" in entry.text for entry in entries)
    assert all(entry.name and entry.keyword and entry.scene for entry in entries)


def test_wrap_text_keeps_long_chinese_copy_inside_canvas():
    meme_pack = load_module()

    lines, font = meme_pack.fit_text_lines(
        "老板我真的在写了只是灵魂还没编译通过",
        font_path=meme_pack.find_default_font(),
        max_width=210,
        max_height=70,
        max_font_size=34,
        min_font_size=16,
    )

    assert len(lines) >= 2
    assert font.size >= 16
    assert all(lines)


def test_build_pack_writes_named_and_wechat_outputs(tmp_path: Path):
    meme_pack = load_module()
    source = make_source_frames(tmp_path, 24)
    output = tmp_path / "pack"
    entries = meme_pack.default_entries("科研打工人", 24)

    result = meme_pack.build_pack(
        source_dir=source,
        output_dir=output,
        entries=entries,
        mode="wechat",
        pack_name="测试表情包",
        style="clean-sticker",
        persona="科研打工人",
        author="Agent Meme Forge",
    )

    assert result["pack_size"] == 24
    assert (output / "named-gifs" / f"{entries[0].name}.gif").exists()
    assert (output / "wechat-submit" / "main" / "01.gif").exists()
    assert (output / "wechat-submit" / "thumbs" / "01.png").exists()
    assert (output / "wechat-submit" / "cover.png").exists()
    assert (output / "wechat-submit" / "icon.png").exists()
    assert (output / "wechat-submit" / "banner.png").exists()
    assert (output / "manifest.csv").exists()

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["items"]) == 24
    assert manifest["wechat"]["main"]["size"] == [240, 240]
    assert manifest["items"][0]["named_gif"].endswith(".gif")

    first_gif = Image.open(output / "wechat-submit" / "main" / "01.gif")
    assert first_gif.size == (240, 240)
    assert (output / "wechat-submit" / "main" / "01.gif").stat().st_size < 500_000

    first_thumb = Image.open(output / "wechat-submit" / "thumbs" / "01.png")
    assert first_thumb.size == (120, 120)
    assert (output / "wechat-submit" / "thumbs" / "01.png").stat().st_size < 50_000


def test_cli_reports_clean_error_for_invalid_wechat_size(tmp_path: Path, capsys):
    meme_pack = load_module()
    source = make_source_frames(tmp_path, 18)
    output = tmp_path / "invalid"

    result = meme_pack.main(
        [
            "build-pack",
            "--source-dir",
            str(source),
            "--output-dir",
            str(output),
            "--persona",
            "科研打工人",
            "--pack-size",
            "18",
            "--mode",
            "wechat",
        ]
    )

    captured = capsys.readouterr()
    assert result == 2
    assert "16 or 24" in captured.err
    assert "Traceback" not in captured.err
