from __future__ import annotations

import importlib.util
import json
import shlex
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageSequence


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


def make_motion_sheets(tmp_path: Path, count: int = 24, layout: str = "1x4") -> Path:
    meme_pack = load_module()
    rows, cols = meme_pack.parse_sheet_layout(layout)
    source = tmp_path / f"source-{layout}"
    source.mkdir()
    cell = 96
    for index in range(count):
        sheet = Image.new("RGBA", (cols * cell, rows * cell), (255, 0, 255, 255))
        draw = ImageDraw.Draw(sheet)
        for frame in range(rows * cols):
            row = frame // cols
            col = frame % cols
            x = col * cell
            y = row * cell
            color = ((70 + index * 9 + frame * 35) % 220, (90 + frame * 45) % 220, 180, 255)
            offset = (frame % 3) * 2
            draw.rounded_rectangle((x + 24 + offset // 2, y + 18, x + 72 + offset // 2, y + 72), radius=16, fill=color)
            draw.ellipse((x + 38 + offset // 2, y + 36, x + 45 + offset // 2, y + 43), fill=(255, 255, 255, 255))
            draw.ellipse((x + 56 + offset // 2, y + 36, x + 63 + offset // 2, y + 43), fill=(255, 255, 255, 255))
        sheet.save(source / f"{index + 1:02d}-{layout}.png")
    return source


def make_single_motion_sheet(
    tmp_path: Path,
    layout: str = "2x4",
    *,
    background: tuple[int, int, int, int] = (255, 0, 255, 255),
    edge_touch: bool = False,
    empty_frame: int | None = None,
    scale_jump: bool = False,
    checkerboard: bool = False,
) -> Path:
    meme_pack = load_module()
    rows, cols = meme_pack.parse_sheet_layout(layout)
    cell = 96
    sheet = Image.new("RGBA", (cols * cell, rows * cell), background)
    draw = ImageDraw.Draw(sheet)
    if checkerboard:
        colors = [(238, 238, 238, 255), (204, 204, 204, 255)]
        tile = 12
        for y in range(0, sheet.height, tile):
            for x in range(0, sheet.width, tile):
                draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill=colors[((x // tile) + (y // tile)) % 2])
    for frame in range(rows * cols):
        if empty_frame is not None and frame == empty_frame:
            continue
        row = frame // cols
        col = frame % cols
        x = col * cell
        y = row * cell
        if edge_touch and frame == 0:
            box = (x, y + 18, x + 54, y + 72)
        elif scale_jump and frame == rows * cols - 1:
            box = (x + 10, y + 8, x + 88, y + 88)
        else:
            drift = (frame % 4) * 3
            box = (x + 25 + drift, y + 18, x + 72 + drift, y + 72)
        draw.rounded_rectangle(box, radius=16, fill=(54, 116, 220, 255))
        draw.ellipse((box[0] + 14, box[1] + 17, box[0] + 21, box[1] + 24), fill=(255, 255, 255, 255))
        draw.ellipse((box[2] - 21, box[1] + 17, box[2] - 14, box[1] + 24), fill=(255, 255, 255, 255))
    path = tmp_path / f"sheet-{layout}.png"
    sheet.save(path)
    return path


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


def test_plan_pack_builds_direct_text_image_prompts():
    meme_pack = load_module()

    plan = meme_pack.plan_pack(
        subject="Claude-inspired warm geometric AI assistant mascot, original character, no official logo",
        persona="科研打工人",
        style="clean-sticker",
        pack_size=24,
        mode="wechat",
        tone="职场发疯但安全",
    )

    assert plan["subject"].startswith("Claude-inspired")
    assert plan["input_mode"] == "text_concept"
    assert plan["pack_size"] == 24
    assert "character_card" in plan
    assert len(plan["items"]) == 24
    assert len(plan["image_prompts"]) == 24
    assert any("文献" in item["text"] for item in plan["items"])
    assert plan["animation"]["source_layout"] == "2x4"
    assert plan["animation"]["frames_per_sticker"] == 8

    first_prompt = plan["image_prompts"][0]["prompt"]
    first_prompt_plan = plan["image_prompts"][0]
    assert "no text" in first_prompt.lower()
    assert "no speech bubbles" in first_prompt.lower()
    assert "240x240" in first_prompt
    assert "exactly 8 equal cells in a 2x4 grid" in first_prompt
    assert "same bounding box" in first_prompt.lower()
    assert "smooth in-between animation" in first_prompt
    assert "medium-readable micro-motion" in first_prompt
    assert "no lateral drift" in first_prompt.lower()
    assert "avoid flicker" in first_prompt.lower()
    assert "same silhouette and hand pose" in first_prompt
    assert "transparent png background" in first_prompt.lower()
    assert "Frame 1" in first_prompt and "Frame 8" in first_prompt
    assert "Claude-inspired warm geometric AI assistant mascot" in first_prompt
    assert first_prompt_plan["meme_name"] == first_prompt_plan["name"]
    assert first_prompt_plan["send_scene"] == first_prompt_plan["scene"]
    assert first_prompt_plan["motion_type"] == first_prompt_plan["motion"]
    assert first_prompt_plan["motion_profile"] == "micro"
    assert len(first_prompt_plan["8_frame_beats"]) == 8
    assert first_prompt_plan["visual_gag"]
    assert "meme_quality_bar" in plan
    assert "没人用的表情包就是垃圾表情包" in plan["meme_quality_bar"]["principle"]
    assert first_prompt_plan["sendability_gate"]["reuse_trigger"] == first_prompt_plan["send_scene"]
    assert first_prompt_plan["sendability_gate"]["creative_hook"] == first_prompt_plan["visual_gag"]
    assert "only cute or decorative" in first_prompt_plan["sendability_gate"]["reject_if"]
    assert "Sendability gate" in first_prompt
    assert "only cute or decorative" in first_prompt
    assert "no text" in first_prompt_plan["negative_prompt"]
    assert "checkerboard" in first_prompt_plan["qc_acceptance"]
    assert first_prompt_plan["regenerate_hint"]
    assert plan["quality_mode"] == "submission"
    assert "MUST call built-in image_gen" in plan["agent_instructions"][0]
    assert "Do not stop after writing the plan" in plan["agent_instructions"][0]
    assert "Replace any weak joke" in " ".join(plan["agent_instructions"])
    assert plan["requires_agent_tooling"]["image_generation_tool"] == "image_gen"
    assert plan["raw_output_dir"] == "output/raw-frames/AgentMemePack"
    assert "accept-generated" in plan["image_handoff"]["accept_generated_command"]
    assert "generated-index.json" in plan["image_handoff"]["index_file"]


def test_plan_pack_writes_shell_safe_commands_and_handoff():
    meme_pack = load_module()

    plan = meme_pack.plan_pack(
        subject="round mascot",
        persona="科研打工人",
        style="clean-sticker",
        pack_name="Agent Meme Pack",
    )

    processor_parts = shlex.split(plan["processor_command"])
    pack_name_value = processor_parts[processor_parts.index("--pack-name") + 1]

    assert pack_name_value == "Agent Meme Pack"
    assert plan["processor_command_args"] == processor_parts
    assert "--image path/to/generated.png" in plan["image_handoff"]["accept_generated_command"]
    assert "accept-generated" in " ".join(plan["agent_instructions"])


def test_plan_pack_can_request_16_frame_4x4_expressive_motion():
    meme_pack = load_module()

    plan = meme_pack.plan_pack(
        subject="stylized office avatar with glasses",
        persona="都市丽人",
        style="clean-sticker",
        pack_size=16,
        mode="wechat",
        animation_layout="4x4",
    )

    prompt_plan = plan["image_prompts"][0]
    prompt = prompt_plan["prompt"]

    assert plan["animation"]["source_layout"] == "4x4"
    assert plan["animation"]["frames_per_sticker"] == 16
    assert "exactly 16 equal cells in a 4x4 grid" in prompt
    assert "Frame 16" in prompt
    assert len(prompt_plan["frame_beats"]) == 16
    assert len(set(prompt_plan["frame_beats"])) > 10
    assert any("in-between" in beat for beat in prompt_plan["frame_beats"])
    assert prompt_plan["16_frame_beats"] == prompt_plan["frame_beats"]


def test_accept_generated_copies_image_to_planned_raw_filename(tmp_path: Path):
    meme_pack = load_module()
    plan = meme_pack.plan_pack(subject="round mascot", pack_name="Agent Meme Pack")
    plan_path = tmp_path / "plan.json"
    meme_pack.write_plan(plan_path, plan)

    generated = tmp_path / "generated.png"
    Image.new("RGBA", (16, 16), (255, 0, 255, 255)).save(generated)
    result = meme_pack.accept_generated_image(plan_path, 1, generated, tmp_path / "raw")
    expected = tmp_path / "raw" / plan["image_prompts"][0]["raw_image_filename"]
    index = json.loads((tmp_path / "raw" / "generated-index.json").read_text(encoding="utf-8"))

    assert expected.exists()
    assert result["saved_image"] == str(expected)
    assert result["raw_image_filename"] == plan["image_prompts"][0]["raw_image_filename"]
    assert index["plan"] == str(plan_path)
    assert index["source_dir"] == str(tmp_path / "raw")
    assert index["items"][0]["index"] == 1
    assert index["items"][0]["saved_image"] == str(expected)


def test_cli_accept_generated_writes_json(tmp_path: Path, capsys):
    meme_pack = load_module()
    plan = meme_pack.plan_pack(subject="round mascot")
    plan_path = tmp_path / "plan.json"
    meme_pack.write_plan(plan_path, plan)
    generated = tmp_path / "generated.png"
    Image.new("RGBA", (16, 16), (255, 0, 255, 255)).save(generated)

    result = meme_pack.main(
        [
            "accept-generated",
            "--plan",
            str(plan_path),
            "--index",
            "1",
            "--image",
            str(generated),
            "--source-dir",
            str(tmp_path / "raw"),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert result == 0
    assert payload["saved_image"].endswith(plan["image_prompts"][0]["raw_image_filename"])
    assert (tmp_path / "raw" / "generated-index.json").exists()


def test_cli_plan_pack_writes_json(tmp_path: Path):
    meme_pack = load_module()
    output = tmp_path / "plan.json"

    result = meme_pack.main(
        [
            "plan-pack",
            "--subject",
            "round coral AI helper mascot with paper-stack anxiety",
            "--persona",
            "码农",
            "--style",
            "pixel-art",
            "--pack-size",
            "16",
            "--mode",
            "wechat",
            "--output",
            str(output),
        ]
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert result == 0
    assert data["style"] == "pixel-art"
    assert data["pack_size"] == 16
    assert len(data["image_prompts"]) == 16
    assert data["animation"]["source_layout"] == "2x4"
    assert data["animation"]["frames_per_sticker"] == 8
    assert "BUG" in json.dumps(data["items"], ensure_ascii=False)


def test_plan_wizard_collects_text_concept_choices(tmp_path: Path):
    meme_pack = load_module()
    output = tmp_path / "wizard-plan.json"
    answers = iter(
        [
            "1",  # text_concept
            "warm cat scientist mascot, original character, no official logo",
            "3",  # 码农
            "2",  # pixel-art
            "1",  # wechat
            "2",  # 16
            "1",  # submission
            "",  # forced/default 2x4
            "猫猫码农包",
            "",  # default tone
            str(output),
        ]
    )
    messages: list[str] = []

    plan = meme_pack.run_plan_wizard(input_fn=lambda _prompt: next(answers), print_fn=messages.append)

    assert output.exists()
    assert plan["input_mode"] == "text_concept"
    assert plan["subject"].startswith("warm cat scientist")
    assert plan["persona"] == "码农"
    assert plan["style"] == "pixel-art"
    assert plan["pack_size"] == 16
    assert plan["quality_mode"] == "submission"
    assert plan["animation"]["source_layout"] == "2x4"
    assert any("先生成前 3 张" in message for message in messages)


def test_plan_wizard_collects_reference_image_choices(tmp_path: Path):
    meme_pack = load_module()
    output = tmp_path / "reference-plan.json"
    reference = tmp_path / "person.png"
    reference.write_bytes(b"placeholder")
    answers = iter(
        [
            "2",  # reference_image
            str(reference),
            "短发戴眼镜，笑起来很像实验室组会幸存者",
            "1",  # 科研打工人
            "1",  # clean-sticker
            "2",  # self_use
            "",  # default 18
            "3",  # preview
            "2",  # 1x4
            "我的测试包",
            "轻微发疯但安全",
            str(output),
        ]
    )

    plan = meme_pack.run_plan_wizard(input_fn=lambda _prompt: next(answers), print_fn=lambda _message: None)

    assert output.exists()
    assert plan["input_mode"] == "reference_image"
    assert plan["reference_image"] == str(reference)
    assert plan["subject"] == "短发戴眼镜，笑起来很像实验室组会幸存者"
    assert plan["mode"] == "self_use"
    assert plan["pack_size"] == 18
    assert plan["quality_mode"] == "preview"
    assert plan["animation"]["source_layout"] == "1x4"


def test_split_sheet_writes_numbered_transparent_cells(tmp_path: Path):
    meme_pack = load_module()
    sheet = Image.new("RGBA", (80, 80), (255, 255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    colors = [(255, 80, 80, 255), (80, 255, 80, 255), (80, 80, 255, 255), (255, 180, 80, 255)]
    boxes = [(10, 10, 30, 30), (50, 10, 70, 30), (10, 50, 30, 70), (50, 50, 70, 70)]
    for color, box in zip(colors, boxes):
        draw.rectangle(box, fill=color)
    sheet_path = tmp_path / "sheet.png"
    sheet.save(sheet_path)

    written = meme_pack.split_sheet(sheet_path, tmp_path / "cells", rows=2, cols=2, transparent_light=True)

    assert len(written) == 4
    assert written[0].name == "01.png"
    first = Image.open(written[0]).convert("RGBA")
    assert first.size == (40, 40)
    assert first.getpixel((0, 0))[3] == 0
    assert first.getbbox() is not None


def test_chroma_background_removes_magenta_variants():
    meme_pack = load_module()
    image = Image.new("RGBA", (2, 1), (248, 20, 240, 255))
    image.putpixel((1, 0), (255, 120, 80, 255))

    cleaned = meme_pack.remove_chroma_background(image)

    assert cleaned.getpixel((0, 0))[3] == 0
    assert cleaned.getpixel((1, 0))[3] == 255


def test_chroma_background_decontaminates_magenta_edge_spill():
    meme_pack = load_module()
    image = Image.new("RGBA", (3, 1), (255, 0, 255, 255))
    image.putpixel((1, 0), (190, 70, 178, 255))
    image.putpixel((2, 0), (255, 120, 80, 255))

    cleaned = meme_pack.remove_chroma_background(image)
    red, green, blue, alpha = cleaned.getpixel((1, 0))

    assert cleaned.getpixel((0, 0))[3] == 0
    assert alpha < 150
    assert not (red > 150 and blue > 130 and green < 90)
    assert cleaned.getpixel((2, 0)) == (255, 120, 80, 255)


def test_plan_pack_can_request_explicit_1x8_layout():
    meme_pack = load_module()

    plan = meme_pack.plan_pack(
        subject="round coral AI helper mascot",
        persona="科研打工人",
        style="clean-sticker",
        pack_size=16,
        mode="wechat",
        animation_layout="1x8",
    )

    assert plan["animation"]["source_layout"] == "1x8"
    assert plan["animation"]["frames_per_sticker"] == 8
    assert "exactly 8 equal cells in a 1x8 grid" in plan["image_prompts"][0]["prompt"]


def test_load_source_frames_splits_motion_sheet(tmp_path: Path):
    meme_pack = load_module()
    source = make_motion_sheets(tmp_path, 1, "1x4")

    frames, kind, layout = meme_pack.load_source_frames(source / "01-1x4.png", source_layout="auto")

    assert len(frames) == 4
    assert kind == "sheet"
    assert layout == "1x4"
    assert frames[0].size == (96, 96)


def test_build_pack_uses_motion_sheet_frames_instead_of_bounce(tmp_path: Path):
    meme_pack = load_module()
    source = make_motion_sheets(tmp_path, 24, "1x4")
    output = tmp_path / "pack"
    entries = meme_pack.default_entries("科研打工人", 24)

    result = meme_pack.build_pack(
        source_dir=source,
        output_dir=output,
        entries=entries,
        mode="wechat",
        pack_name="测试多帧表情包",
        style="clean-sticker",
        persona="科研打工人",
        author="Agent Meme Forge",
        source_layout="auto",
        quality_mode="preview",
    )

    first_item = result["items"][0]
    assert first_item["animation_source"] == "sheet"
    assert first_item["source_layout"] == "1x4"
    assert first_item["source_frame_count"] == 4

    gif = Image.open(output / "wechat-submit" / "main" / "01.gif")
    assert getattr(gif, "is_animated", False)
    assert gif.n_frames == 4


def test_build_pack_uses_8_frame_motion_sheet(tmp_path: Path):
    meme_pack = load_module()
    source = make_motion_sheets(tmp_path, 24, "2x4")
    output = tmp_path / "pack"

    result = meme_pack.build_pack(
        source_dir=source,
        output_dir=output,
        entries=meme_pack.default_entries("科研打工人", 24),
        mode="wechat",
        source_layout="2x4",
    )

    first_item = result["items"][0]
    gif = Image.open(output / "wechat-submit" / "main" / "01.gif")

    assert first_item["animation_source"] == "sheet"
    assert first_item["source_layout"] == "2x4"
    assert first_item["source_frame_count"] == 8
    assert first_item["motion_profile"] == "micro"
    assert first_item["alignment_mode"] == "stable"
    assert gif.n_frames == 8
    assert gif.info["duration"] >= 160
    first_frame = next(ImageSequence.Iterator(gif)).convert("RGBA")
    assert sum(1 for pixel in meme_pack.pixel_data(first_frame.getchannel("A")) if pixel == 0) > 0


def test_build_pack_uses_16_frame_4x4_motion_sheet_when_under_limit(tmp_path: Path):
    meme_pack = load_module()
    source = make_motion_sheets(tmp_path, 16, "4x4")
    output = tmp_path / "pack"

    result = meme_pack.build_pack(
        source_dir=source,
        output_dir=output,
        entries=meme_pack.default_entries("都市丽人", 16),
        mode="wechat",
        source_layout="4x4",
    )

    first_item = result["items"][0]
    gif = Image.open(output / "wechat-submit" / "main" / "01.gif")

    assert first_item["animation_source"] == "sheet"
    assert first_item["source_layout"] == "4x4"
    assert first_item["source_frame_count"] == 16
    assert first_item["gif_frame_count"] == 16
    assert 95 <= first_item["gif_duration_ms"] <= 120
    assert gif.n_frames == 16


def test_qc_sheet_passes_clean_magenta_2x4_motion_sheet(tmp_path: Path):
    meme_pack = load_module()
    sheet = make_single_motion_sheet(tmp_path, "2x4")

    report = meme_pack.qc_sheet(sheet, source_layout="2x4", quality_mode="submission", strict=True)

    assert report["status"] == "pass"
    assert report["frame_count"] == 8
    assert report["background_mode"] == "magenta"
    assert report["edge_touch"] is False
    assert report["bbox_drift"]["center_ratio"] < 0.2


def test_qc_sheet_allows_clean_4x4_submission_motion_sheet(tmp_path: Path):
    meme_pack = load_module()
    sheet = make_single_motion_sheet(tmp_path, "4x4")

    report = meme_pack.qc_sheet(sheet, source_layout="4x4", quality_mode="submission", strict=True)

    assert report["status"] == "pass"
    assert report["source_layout"] == "4x4"
    assert report["frame_count"] == 16


def test_qc_sheet_passes_true_alpha_motion_sheet(tmp_path: Path):
    meme_pack = load_module()
    sheet = make_single_motion_sheet(tmp_path, "2x4", background=(0, 0, 0, 0))

    report = meme_pack.qc_sheet(sheet, source_layout="2x4", quality_mode="submission", strict=True)

    assert report["status"] == "pass"
    assert report["background_mode"] == "transparent"


def test_qc_sheet_warns_on_solid_light_background_for_submission(tmp_path: Path):
    meme_pack = load_module()
    sheet = make_single_motion_sheet(tmp_path, "2x4", background=(255, 255, 255, 255))

    report = meme_pack.qc_sheet(sheet, source_layout="2x4", quality_mode="submission", strict=True)

    assert report["status"] == "fail"
    assert report["background_mode"] == "solid_light"
    assert any("true alpha or pure #FF00FF" in error for error in report["errors"])


def test_component_filter_removes_isolated_noise(tmp_path: Path):
    meme_pack = load_module()
    image = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((24, 20, 56, 58), radius=10, fill=(20, 120, 220, 255))
    draw.rectangle((2, 2, 3, 3), fill=(255, 0, 0, 255))

    cleaned, info = meme_pack.filter_subject_components(image, min_component_area=5)

    assert info["removed_component_count"] == 1
    assert cleaned.getpixel((2, 2))[3] == 0
    assert cleaned.getbbox() == (24, 20, 57, 59)


def test_normalize_motion_frames_uses_common_scale(tmp_path: Path):
    meme_pack = load_module()
    frames = []
    for size in [40, 44, 50, 56, 60, 52, 46, 42]:
        frame = Image.new("RGBA", (96, 96), (255, 0, 255, 255))
        draw = ImageDraw.Draw(frame)
        left = (96 - size) // 2
        draw.rounded_rectangle((left, 18, left + size, 18 + size), radius=12, fill=(20, 120, 220, 255))
        frames.append(frame)

    normalized, meta = meme_pack.normalize_motion_frames(frames)
    boxes = [frame.getbbox() for frame in normalized]
    heights = [box[3] - box[1] for box in boxes]

    assert meta["scale_normalized"] is True
    assert all(frame.size == (240, 240) for frame in normalized)
    assert max(heights) <= 146
    assert min(box[3] for box in boxes) <= 164


def test_normalize_motion_frames_preserves_relative_motion():
    meme_pack = load_module()
    frames = []
    for left in [18, 24, 30, 36]:
        frame = Image.new("RGBA", (96, 96), (255, 0, 255, 255))
        draw = ImageDraw.Draw(frame)
        draw.rounded_rectangle((left, 22, left + 34, 60), radius=10, fill=(20, 120, 220, 255))
        frames.append(frame)

    normalized, _ = meme_pack.normalize_motion_frames(frames, alignment_mode="preserve")
    centers = []
    for frame in normalized:
        box = frame.getbbox()
        assert box is not None
        centers.append((box[0] + box[2]) / 2)

    assert centers == sorted(centers)
    assert centers[-1] - centers[0] > 4


def test_normalize_motion_frames_stable_alignment_removes_source_drift():
    meme_pack = load_module()
    frames = []
    for left in [12, 22, 34, 44]:
        frame = Image.new("RGBA", (96, 96), (255, 0, 255, 255))
        draw = ImageDraw.Draw(frame)
        draw.rounded_rectangle((left, 20, left + 34, 60), radius=10, fill=(20, 120, 220, 255))
        frames.append(frame)

    normalized, meta = meme_pack.normalize_motion_frames(frames, alignment_mode="stable")
    centers = []
    for frame in normalized:
        box = frame.getbbox()
        assert box is not None
        centers.append((box[0] + box[2]) / 2)

    assert meta["alignment_mode"] == "stable"
    assert max(centers) - min(centers) <= 1


def test_qc_sheet_rejects_micro_motion_center_drift(tmp_path: Path):
    meme_pack = load_module()
    rows, cols = meme_pack.parse_sheet_layout("2x4")
    cell = 96
    sheet = Image.new("RGBA", (cols * cell, rows * cell), (255, 0, 255, 255))
    draw = ImageDraw.Draw(sheet)
    offsets = [6, 16, 27, 36, 6, 16, 27, 36]
    for frame, offset in enumerate(offsets):
        row = frame // cols
        col = frame % cols
        x = col * cell
        y = row * cell
        draw.rounded_rectangle((x + offset, y + 20, x + offset + 36, y + 60), radius=10, fill=(20, 120, 220, 255))
    path = tmp_path / "micro-drift.png"
    sheet.save(path)

    report = meme_pack.qc_sheet(path, source_layout="2x4", quality_mode="submission", strict=True, motion_profile="micro")

    assert report["status"] == "fail"
    assert report["motion_profile"] == "micro"
    assert any("frame center drift is too high" in error for error in report["errors"])


def test_qc_sheet_rejects_fake_checkerboard_transparency(tmp_path: Path):
    meme_pack = load_module()
    sheet = make_single_motion_sheet(tmp_path, "2x4", checkerboard=True)

    report = meme_pack.qc_sheet(sheet, source_layout="2x4", quality_mode="submission", strict=True)

    assert report["status"] == "fail"
    assert any("checkerboard" in error for error in report["errors"])


def test_qc_sheet_rejects_edge_touch_in_strict_mode(tmp_path: Path):
    meme_pack = load_module()
    sheet = make_single_motion_sheet(tmp_path, "2x4", edge_touch=True)

    report = meme_pack.qc_sheet(sheet, source_layout="2x4", quality_mode="submission", strict=True)

    assert report["status"] == "fail"
    assert report["edge_touch"] is True


def test_qc_sheet_rejects_excessive_bbox_drift(tmp_path: Path):
    meme_pack = load_module()
    sheet = make_single_motion_sheet(tmp_path, "2x4", scale_jump=True)

    report = meme_pack.qc_sheet(sheet, source_layout="2x4", quality_mode="submission", strict=True)

    assert report["status"] == "fail"
    assert report["bbox_drift"]["size_ratio"] > 0.25


def test_cli_qc_sheet_writes_report_json(tmp_path: Path):
    meme_pack = load_module()
    sheet = make_single_motion_sheet(tmp_path, "2x4")
    output = tmp_path / "qc.json"

    result = meme_pack.main(
        [
            "qc-sheet",
            "--input",
            str(sheet),
            "--source-layout",
            "2x4",
            "--quality-mode",
            "submission",
            "--output",
            str(output),
        ]
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert result == 0
    assert data["status"] == "pass"
    assert data["source_layout"] == "2x4"


def test_submission_mode_rejects_single_bounce_sources(tmp_path: Path):
    meme_pack = load_module()
    source = make_source_frames(tmp_path, 24)

    with pytest.raises(ValueError, match="single_bounce.*preview"):
        meme_pack.build_pack(
            source_dir=source,
            output_dir=tmp_path / "pack",
            entries=meme_pack.default_entries("科研打工人", 24),
            mode="wechat",
            quality_mode="submission",
        )


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


def test_wrap_text_truncates_extreme_copy_to_fit_canvas():
    meme_pack = load_module()

    lines, font = meme_pack.fit_text_lines(
        "老板我真的在写了只是灵魂还没编译通过而且需求又变了所以我现在只能先假装一切都很合理",
        font_path=meme_pack.find_default_font(),
        max_width=214,
        max_height=76,
        max_font_size=34,
        min_font_size=16,
    )
    line_height = max(meme_pack._text_size(line, font)[1] for line in lines) + 6

    assert line_height * len(lines) <= 76
    assert all(meme_pack._text_size(line, font)[0] <= 214 for line in lines)
    assert lines[-1].endswith("…")


def test_build_pack_writes_named_and_wechat_outputs(tmp_path: Path):
    meme_pack = load_module()
    source = make_motion_sheets(tmp_path, 24, "2x4")
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
    assert manifest["items"][0]["qc_status"] == "pass"
    assert manifest["items"][0]["background_mode"] in {"magenta", "transparent", "solid_light", "unknown"}
    assert "bbox_drift" in manifest["items"][0]
    assert manifest["items"][0]["scale_normalized"] is True
    assert manifest["items"][0]["preview_only"] is False

    first_gif = Image.open(output / "wechat-submit" / "main" / "01.gif")
    assert first_gif.size == (240, 240)
    assert (output / "wechat-submit" / "main" / "01.gif").stat().st_size < 500_000

    first_thumb = Image.open(output / "wechat-submit" / "thumbs" / "01.png")
    assert first_thumb.size == (120, 120)
    assert (output / "wechat-submit" / "thumbs" / "01.png").stat().st_size < 50_000


def test_rebuilding_smaller_pack_cleans_stale_wechat_files(tmp_path: Path):
    meme_pack = load_module()
    source = make_motion_sheets(tmp_path, 24, "2x4")
    output = tmp_path / "pack"

    meme_pack.build_pack(
        source_dir=source,
        output_dir=output,
        entries=meme_pack.default_entries("科研打工人", 24),
        mode="wechat",
    )
    meme_pack.build_pack(
        source_dir=source,
        output_dir=output,
        entries=meme_pack.default_entries("码农", 16),
        mode="wechat",
    )

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    main_files = sorted((output / "wechat-submit" / "main").glob("*.gif"))
    thumb_files = sorted((output / "wechat-submit" / "thumbs").glob("*.png"))
    named_files = sorted((output / "named-gifs").glob("*.gif"))

    assert manifest["pack_size"] == 16
    assert len(main_files) == 16
    assert len(thumb_files) == 16
    assert len(named_files) == 16
    assert not (output / "wechat-submit" / "main" / "24.gif").exists()


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
