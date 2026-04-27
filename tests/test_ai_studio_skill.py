import importlib.util
import json
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "generate-meme-gif-pack-ai-studio"
SCRIPT = SKILL_DIR / "scripts" / "ai_studio_pack.py"


def load_ai_studio_module():
    spec = importlib.util.spec_from_file_location("ai_studio_pack_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_plan(path: Path, pack_size: int = 3) -> dict:
    prompts = []
    for index in range(1, pack_size + 1):
        prompts.append(
            {
                "name": f"表情{index}",
                "caption": f"文案{index}",
                "send_scene": f"发送场景{index}",
                "motion_template": "loading_loop",
                "raw_image_filename": f"{index:02d}-表情{index}-2x2.png",
                "prompt": f"Create one raw no-text 2x2 keypose sheet for sticker {index}. No text.",
            }
        )
    plan = {
        "pack_name": "AI Studio 测试包",
        "persona": "码农",
        "style": "clean-sticker",
        "pack_size": pack_size,
        "raw_output_dir": "output/raw-frames/ai-studio-test",
        "image_prompts": prompts,
    }
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan


def make_png(path: Path, color: tuple[int, int, int, int] = (0, 255, 0, 255)) -> None:
    Image.new("RGBA", (64, 64), color).save(path)


def test_ai_studio_skill_is_separate_from_image_gen_skill():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    assert "name: generate-meme-gif-pack-ai-studio" in text
    assert "Google AI Studio Web" in text
    assert "Nano Banana Pro" in text
    assert "Nano Banana 2" in text
    assert "do not use Codex image_gen" in text
    assert "do not use Gemini API" in text
    assert "prompt-board" in text
    assert "import-downloads" in text
    assert "Hermes" in text
    assert "1:1" in text
    assert "PNG" in text
    assert "do not bypass" in text
    assert "DevTools" in text


def test_prompt_board_contains_ai_studio_operator_fields(tmp_path: Path):
    module = load_ai_studio_module()
    plan_path = tmp_path / "plan.json"
    board_path = tmp_path / "prompt-board.html"
    download_dir = tmp_path / "downloads"
    write_plan(plan_path, pack_size=2)

    result = module.write_prompt_board(
        plan_path=plan_path,
        output_path=board_path,
        download_dir=download_dir,
        model="Nano Banana Pro",
        background="#00FF00",
        image_size="2K",
    )

    html = board_path.read_text(encoding="utf-8")
    assert result["card_count"] == 2
    assert "Google AI Studio Web" in html
    assert "Nano Banana Pro" in html
    assert "aspect ratio: 1:1" in html
    assert "image size: 2K" in html
    assert "#00FF00" in html
    assert "copyPrompt" in html
    assert "01-表情1-2x2.png" in html
    assert "Create one raw no-text 2x2 keypose sheet" in html
    assert str(download_dir) in html


def test_import_downloads_matches_exact_ai_studio_filenames(tmp_path: Path):
    module = load_ai_studio_module()
    plan_path = tmp_path / "plan.json"
    plan = write_plan(plan_path, pack_size=2)
    download_dir = tmp_path / "downloads"
    source_dir = tmp_path / "raw"
    download_dir.mkdir()
    make_png(download_dir / plan["image_prompts"][0]["raw_image_filename"])
    make_png(download_dir / plan["image_prompts"][1]["raw_image_filename"], (255, 0, 255, 255))

    result = module.import_downloads(
        plan_path=plan_path,
        download_dir=download_dir,
        source_dir=source_dir,
        mode="strict",
    )

    assert result["imported"] == 2
    assert (source_dir / "01-表情1-2x2.png").exists()
    assert (source_dir / "02-表情2-2x2.png").exists()
    index = json.loads((source_dir / "generated-index.json").read_text(encoding="utf-8"))
    assert index["provider"] == "google-ai-studio-web"
    assert index["items"][0]["target_filename"] == "01-表情1-2x2.png"


def test_import_downloads_ordered_mode_maps_generic_download_names(tmp_path: Path):
    module = load_ai_studio_module()
    plan_path = tmp_path / "plan.json"
    write_plan(plan_path, pack_size=2)
    download_dir = tmp_path / "downloads"
    source_dir = tmp_path / "raw"
    download_dir.mkdir()
    make_png(download_dir / "Image 1.png")
    make_png(download_dir / "Image 2.png")

    result = module.import_downloads(
        plan_path=plan_path,
        download_dir=download_dir,
        source_dir=source_dir,
        mode="ordered",
    )

    assert result["imported"] == 2
    assert (source_dir / "01-表情1-2x2.png").exists()
    assert (source_dir / "02-表情2-2x2.png").exists()


def test_import_downloads_ordered_mode_refuses_count_mismatch(tmp_path: Path):
    module = load_ai_studio_module()
    plan_path = tmp_path / "plan.json"
    write_plan(plan_path, pack_size=2)
    download_dir = tmp_path / "downloads"
    source_dir = tmp_path / "raw"
    download_dir.mkdir()
    make_png(download_dir / "Image 1.png")

    try:
        module.import_downloads(
            plan_path=plan_path,
            download_dir=download_dir,
            source_dir=source_dir,
            mode="ordered",
        )
    except ValueError as error:
        assert "expected 2 image downloads" in str(error)
    else:
        raise AssertionError("ordered import should reject missing downloads")


def test_import_downloads_can_limit_to_first_three_preview_sources(tmp_path: Path):
    module = load_ai_studio_module()
    plan_path = tmp_path / "plan.json"
    plan = write_plan(plan_path, pack_size=4)
    download_dir = tmp_path / "downloads"
    source_dir = tmp_path / "raw"
    download_dir.mkdir()
    for item in plan["image_prompts"][:3]:
        make_png(download_dir / item["raw_image_filename"])

    result = module.import_downloads(
        plan_path=plan_path,
        download_dir=download_dir,
        source_dir=source_dir,
        mode="strict",
        limit=3,
    )

    assert result["imported"] == 3
    assert (source_dir / "01-表情1-2x2.png").exists()
    assert (source_dir / "03-表情3-2x2.png").exists()
    assert not (source_dir / "04-表情4-2x2.png").exists()
