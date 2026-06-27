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


def make_keypose_sheets(tmp_path: Path, count: int = 24, layout: str = "2x2") -> Path:
    meme_pack = load_module()
    rows, cols = meme_pack.parse_sheet_layout(layout)
    source = tmp_path / f"keyposes-{layout}"
    source.mkdir()
    cell = 112
    for index in range(count):
        sheet = Image.new("RGBA", (cols * cell, rows * cell), (255, 0, 255, 255))
        draw = ImageDraw.Draw(sheet)
        for pose in range(rows * cols):
            row = pose // cols
            col = pose % cols
            x = col * cell
            y = row * cell
            head_shift = [0, 1, -1, 0][pose % 4]
            body_color = ((70 + index * 9) % 180, 112, 220, 255)
            draw.rounded_rectangle((x + 34, y + 28 + head_shift, x + 78, y + 82 + head_shift), radius=16, fill=body_color)
            draw.ellipse((x + 45, y + 46 + head_shift, x + 52, y + 53 + head_shift), fill=(255, 255, 255, 255))
            draw.ellipse((x + 61, y + 46 + head_shift, x + 68, y + 53 + head_shift), fill=(255, 255, 255, 255))
            if pose == 1:
                draw.arc((x + 46, y + 54, x + 66, y + 70), 20, 160, fill=(255, 255, 255, 255), width=3)
            if pose == 2:
                draw.ellipse((x + 74, y + 18, x + 90, y + 34), fill=(170, 150, 235, 255))
            if pose == 3:
                draw.arc((x + 46, y + 58, x + 66, y + 72), 200, 340, fill=(255, 255, 255, 255), width=3)
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


def test_vibe_coding_entries_match_ai_coding_reference_pack():
    meme_pack = load_module()

    entries = meme_pack.default_entries("Vibe Coding", 24)
    names = {entry.name for entry in entries}
    captions = "\n".join(entry.text for entry in entries).replace("\n", "")

    assert len(entries) == 24
    assert [entry.name for entry in entries[:3]] == ["灵感来了", "构思中", "写代码中"]
    assert {
        "灵感来了",
        "构思中",
        "写代码中",
        "专注模式",
        "调试中",
        "发现Bug",
        "测试通过",
        "重构中",
        "部署中",
        "上线啦",
        "今晚又加班",
    }.issubset(names)
    assert "灵感来了" in captions
    assert "上线啦" in captions
    assert all(entry.keyword and entry.scene and entry.motion for entry in entries)


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
    assert plan["animation"]["source_mode"] == "keyposes"
    assert plan["animation"]["source_layout"] == "2x2"
    assert plan["animation"]["keypose_count"] == 4
    assert plan["animation"]["rendered_frame_count"] == 16

    first_prompt = plan["image_prompts"][0]["prompt"]
    first_prompt_plan = plan["image_prompts"][0]
    assert "no text" in first_prompt.lower()
    assert "no speech bubbles" in first_prompt.lower()
    assert "240x240" in first_prompt
    assert "exactly 4 key poses in a 2x2 grid" in first_prompt
    assert "Do not generate the final 16 animation frames" in first_prompt
    assert "same bounding box" in first_prompt.lower()
    assert "local processor will render the final 16-frame GIF" in first_prompt
    assert "medium-readable micro-motion" in first_prompt
    assert "no lateral drift" in first_prompt.lower()
    assert "same silhouette and hand pose" in first_prompt
    assert "transparent png background" in first_prompt.lower()
    assert "For Codex image_gen runs, prefer a pure solid #FF00FF background" in first_prompt
    assert "Key pose 1" in first_prompt and "Key pose 4" in first_prompt
    assert "Claude-inspired warm geometric AI assistant mascot" in first_prompt
    assert first_prompt_plan["meme_name"] == first_prompt_plan["name"]
    assert first_prompt_plan["send_scene"] == first_prompt_plan["scene"]
    assert first_prompt_plan["motion_type"] == first_prompt_plan["motion"]
    assert first_prompt_plan["motion_profile"] == "micro"
    assert first_prompt_plan["source_mode"] == "keyposes"
    assert first_prompt_plan["motion_template"] == "soul_offline"
    assert len(first_prompt_plan["keypose_beats"]) == 4
    assert len(first_prompt_plan["timeline"]) == 16
    assert "continuity_acceptance" in first_prompt_plan
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
    assert plan["image_provider"] == "codex_builtin_image_gen"
    assert plan["requires_agent_tooling"]["provider_mode"] == "terminal_action"
    assert plan["requires_agent_tooling"]["same_turn_postprocess_supported"] is False
    assert plan["image_handoff"]["terminal_action"] is True
    assert "terminal action" in plan["requires_agent_tooling"]["tool_boundary"]
    assert "next turn" in plan["image_handoff"]["tool_output_requirement"]
    joined_instructions = " ".join(plan["agent_instructions"])
    assert "first 3 are a QC checkpoint, not a stopping point" in joined_instructions
    assert "do not end the task after the first-3 preview" in joined_instructions
    assert "do not try to run accept-generated or QC in the same turn" in joined_instructions
    assert "resume in the next turn" in joined_instructions
    assert "same turn" not in plan["workflow_contract"]["continue_after_preview"]
    assert "Replace any weak joke" in " ".join(plan["agent_instructions"])
    assert plan["workflow_contract"]["first_three_policy"] == "The first 3 are a QC checkpoint, not a stopping point."
    assert "Complete only when 24 accepted raw images" in plan["workflow_contract"]["completion_definition"]
    assert "waiting for the next turn with exported Codex image_gen files" in plan["workflow_contract"]["allowed_pause_conditions"]
    assert plan["requires_agent_tooling"]["image_generation_tool"] == "image_gen"
    assert plan["raw_output_dir"] == "output/raw-frames/AgentMemePack"
    assert "accept-generated" in plan["image_handoff"]["accept_generated_command"]
    assert "generated-index.json" in plan["image_handoff"]["index_file"]


def test_plan_pack_can_emit_external_provider_continuous_handoff():
    meme_pack = load_module()

    plan = meme_pack.plan_pack(
        subject="round mascot",
        persona="码农",
        style="clean-sticker",
        pack_size=16,
        mode="wechat",
        pack_name="External Provider Pack",
        image_provider="external_files",
    )

    instructions = " ".join(plan["agent_instructions"])
    assert plan["image_provider"] == "external_files"
    assert plan["requires_agent_tooling"]["provider_mode"] == "external_or_scriptable_files"
    assert plan["requires_agent_tooling"]["same_turn_postprocess_supported"] is True
    assert plan["image_handoff"]["terminal_action"] is False
    assert "all 24" not in instructions
    assert "remaining 21" not in instructions
    assert "all planned image_prompts" in instructions
    assert "continue to the remaining prompts in the same workflow" in instructions
    assert "Complete only when 16 accepted raw images" in plan["workflow_contract"]["completion_definition"]
    assert "strict QC or continuity QC fails and regeneration is needed" not in " ".join(
        plan["workflow_contract"]["allowed_pause_conditions"]
    )
    assert "fails repeatedly after regeneration attempts" in " ".join(
        plan["workflow_contract"]["allowed_pause_conditions"]
    )


def test_plan_pack_can_emit_openai_images_api_batch_handoff():
    meme_pack = load_module()

    plan = meme_pack.plan_pack(
        subject="round mascot",
        persona="码农",
        style="clean-sticker",
        pack_size=16,
        mode="wechat",
        pack_name="API Provider Pack",
        image_provider="openai_images_api",
    )

    instructions = " ".join(plan["agent_instructions"])
    assert plan["image_provider"] == "openai_images_api"
    assert plan["requires_agent_tooling"]["provider_mode"] == "scriptable_api"
    assert plan["requires_agent_tooling"]["same_turn_postprocess_supported"] is True
    assert plan["image_handoff"]["terminal_action"] is False
    assert "generate_raw_batch_command" in plan["image_handoff"]
    assert "generate-raw-batch" in plan["image_handoff"]["generate_raw_batch_command"]
    assert "Do not use Codex built-in image_gen" in instructions
    assert plan["workflow_contract"]["same_turn_continuation"] is True


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


def test_plan_pack_can_request_legacy_16_frame_4x4_motion_sheet():
    meme_pack = load_module()

    plan = meme_pack.plan_pack(
        subject="stylized office avatar with glasses",
        persona="都市丽人",
        style="clean-sticker",
        pack_size=16,
        mode="wechat",
        source_mode="motion_sheet",
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


def test_render_keypose_motion_uses_template_to_create_16_frames(tmp_path: Path):
    meme_pack = load_module()
    source = make_keypose_sheets(tmp_path, 1, "2x2")
    keyposes, kind, layout = meme_pack.load_source_frames(source / "01-2x2.png", source_layout="2x2")

    frames, meta = meme_pack.render_keypose_motion(
        keyposes,
        motion_template="soul_offline",
        frame_count=16,
        motion_profile="micro",
    )

    assert kind == "sheet"
    assert layout == "2x2"
    assert len(frames) == 16
    assert all(frame.size == (240, 240) for frame in frames)
    assert meta["source_mode"] == "keyposes"
    assert meta["motion_template"] == "soul_offline"
    assert meta["rendered_frame_count"] == 16
    assert meta["keypose_count"] == 4
    assert meta["scale_normalized"] is True


def test_eased_frame_durations_holds_longer_than_transitions():
    meme_pack = load_module()
    poses = [1, 1, 2, 2, 2, 3, 3, 3, 3, 2, 2, 4, 4, 1, 1, 1]  # soul_offline pose sequence
    total = meme_pack.gif_duration_for_frame_count(16) * 16

    durations = meme_pack.eased_frame_durations(poses, total)

    assert len(durations) == 16
    assert all(value >= 60 and value % 10 == 0 for value in durations)
    assert sum(durations) == total  # pace preserved exactly
    assert meme_pack.eased_frame_durations(poses, total) == durations  # deterministic
    prev_poses = [poses[-1], *poses[:-1]]
    arrivals = [d for d, pose, prev in zip(durations, poses, prev_poses) if pose != prev]
    holds = [d for d, pose, prev in zip(durations, poses, prev_poses) if pose == prev]
    assert max(arrivals) < min(holds)  # transitions snap, holds linger

    # Non-default frame counts: total_ms may not be a multiple of the 10ms grid; the sum must
    # still come out exact (regression for odd render_frame_count like 13/15).
    poses13 = [1, 1, 2, 2, 3, 3, 3, 4, 4, 2, 1, 1, 1]
    total13 = meme_pack.gif_duration_for_frame_count(13) * 13  # 125 * 13 = 1625, not a multiple of 10
    durations13 = meme_pack.eased_frame_durations(poses13, total13)
    assert len(durations13) == 13
    assert sum(durations13) == total13
    assert all(value >= 60 for value in durations13)


def test_save_gif_under_limit_honors_per_frame_durations(tmp_path: Path):
    meme_pack = load_module()
    frames = []
    for index in range(6):
        frame = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
        ImageDraw.Draw(frame).ellipse((40 + index * 4, 40, 200, 200), fill=(60, 120, 220, 255))
        frames.append(frame)

    timed_path = tmp_path / "timed.gif"
    meme_pack.save_gif_under_limit(frames, timed_path, durations=[80, 200, 80, 200, 80, 200])
    timed = [frame.info.get("duration", 0) for frame in ImageSequence.Iterator(Image.open(timed_path))]
    assert len(set(timed)) > 1  # per-frame timing landed

    scalar_path = tmp_path / "scalar.gif"
    meme_pack.save_gif_under_limit(frames, scalar_path)  # durations=None -> scalar fallback
    scalar = [frame.info.get("duration", 0) for frame in ImageSequence.Iterator(Image.open(scalar_path))]
    assert len(set(scalar)) == 1


def test_motion_template_plan_exposes_effects_and_qc_policy():
    meme_pack = load_module()

    entries = [
        meme_pack.MemeEntry("收到离线", "收到\n但灵魂已离线", "收到", "缓冲回复", "eyes blink and tiny nod"),
        meme_pack.MemeEntry("加载中", "别催\n我在加载", "稍等", "被催进度", "loading wobble"),
        meme_pack.MemeEntry("先装懂", "我先\n装懂一下", "懂了", "没听懂先稳住", "confused nod"),
    ]

    plans = [meme_pack.motion_template_plan_for_entry(entry, 16) for entry in entries]

    assert [plan["motion_template"] for plan in plans] == ["soul_offline", "loading_loop", "pretend_understand"]
    assert plans[0]["local_effects"] == ["soul_puff"]
    assert plans[1]["local_effects"] == ["loading_dots"]
    assert plans[2]["local_effects"] == ["sweat_drop", "awkward_lines"]
    assert all("min_prop_lifetime" in plan["qc_policy"] for plan in plans)


def test_continuity_qc_rejects_area_and_loop_jumps():
    meme_pack = load_module()
    frames = []
    for index in range(16):
        frame = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)
        if index == 8:
            draw.rounded_rectangle((30, 10, 210, 176), radius=32, fill=(30, 120, 220, 255))
        elif index == 15:
            draw.rounded_rectangle((126, 58, 172, 118), radius=12, fill=(220, 80, 80, 255))
        else:
            draw.rounded_rectangle((88, 48, 152, 128), radius=18, fill=(30, 120, 220, 255))
        frames.append(frame)

    report = meme_pack.continuity_qc(frames, quality_mode="submission", motion_profile="micro")

    assert report["status"] == "fail"
    assert any("area jump" in error for error in report["errors"])
    assert any("loop closure" in error for error in report["errors"])


def test_continuity_qc_rejects_fake_animation_with_low_motion_energy():
    meme_pack = load_module()
    frame = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    draw.rounded_rectangle((88, 48, 152, 128), radius=18, fill=(30, 120, 220, 255))

    report = meme_pack.continuity_qc([frame.copy() for _ in range(16)], quality_mode="submission", motion_profile="micro")

    assert report["status"] == "fail"
    assert any("motion energy" in error for error in report["errors"])


def test_continuity_qc_rejects_one_frame_prop_flash():
    meme_pack = load_module()
    frames = []
    for index in range(16):
        frame = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)
        x_shift = [0, 1, 0, -1][index % 4]
        draw.rounded_rectangle((82 + x_shift, 42, 158 + x_shift, 138), radius=18, fill=(30, 120, 220, 255))
        if index == 8:
            draw.ellipse((170, 50, 205, 85), fill=(255, 200, 0, 255))
        frames.append(frame)

    report = meme_pack.continuity_qc(frames, quality_mode="submission", motion_profile="standard")

    assert report["status"] == "fail"
    assert any("one frame" in error for error in report["errors"])
    assert report["metrics"]["transient_component_frames"] == [9]


def test_continuity_qc_rejects_prop_position_jump():
    meme_pack = load_module()
    frames = []
    for index in range(16):
        frame = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)
        draw.rounded_rectangle((82, 42, 158, 138), radius=18, fill=(30, 120, 220, 255))
        x0 = 28 if index < 8 else 182
        draw.ellipse((x0, 54, x0 + 34, 88), fill=(255, 200, 0, 255))
        frames.append(frame)

    report = meme_pack.continuity_qc(frames, quality_mode="submission", motion_profile="standard")

    assert report["status"] == "fail"
    assert any("prop position jump" in error for error in report["errors"])
    assert report["metrics"]["prop_position_jump"] > 80


def test_continuity_qc_rejects_head_shape_drift():
    meme_pack = load_module()
    frames = []
    for index in range(16):
        frame = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)
        draw.rounded_rectangle((86, 92, 154, 158), radius=18, fill=(30, 120, 220, 255))
        if index == 8:
            draw.ellipse((58, 28, 182, 86), fill=(30, 120, 220, 255))
        else:
            draw.ellipse((82, 26, 158, 96), fill=(30, 120, 220, 255))
        frames.append(frame)

    report = meme_pack.continuity_qc(frames, quality_mode="submission", motion_profile="standard")

    assert report["status"] == "fail"
    assert any("face/head shape drift" in error for error in report["errors"])
    assert report["metrics"]["face_shape_drift_score"] > 0.25


def test_continuity_qc_allows_stable_head_with_continuous_loading_effect():
    meme_pack = load_module()
    frames = []
    for index in range(16):
        frame = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)
        draw.rounded_rectangle((88, 86, 152, 150), radius=18, fill=(30, 120, 220, 255))
        draw.ellipse((88, 32, 152, 96), fill=(30, 120, 220, 255))
        dot_x = 165 + (index % 3) * 9
        draw.ellipse((dot_x, 48, dot_x + 7, 55), fill=(80, 130, 255, 255))
        frames.append(frame)

    report = meme_pack.continuity_qc(
        frames,
        quality_mode="submission",
        motion_profile="micro",
        motion_template="loading_loop",
    )

    assert report["status"] == "pass"
    assert report["metrics"]["prop_lifecycle_errors"] == []
    assert report["metrics"]["face_shape_drift_score"] < 0.12


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
    assert data["animation"]["source_mode"] == "keyposes"
    assert data["animation"]["source_layout"] == "2x2"
    assert data["animation"]["rendered_frame_count"] == 16
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
            "",  # default Codex built-in image_gen terminal provider
            "",  # forced/default 2x2 keyposes
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
    assert plan["image_provider"] == "codex_builtin_image_gen"
    assert plan["requires_agent_tooling"]["provider_mode"] == "terminal_action"
    assert plan["animation"]["source_mode"] == "keyposes"
    assert plan["animation"]["source_layout"] == "2x2"
    assert any("先生成前 3 张" in message for message in messages)
    assert any("前三张只是质量闸门，不是交付终点" in message for message in messages)


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
            "3",  # external_files provider can continue after local files exist
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
    assert plan["image_provider"] == "external_files"
    assert plan["requires_agent_tooling"]["same_turn_postprocess_supported"] is True
    assert plan["animation"]["source_layout"] == "1x4"


def test_generate_raw_batch_writes_jsonl_and_calls_provider_cli(tmp_path: Path):
    meme_pack = load_module()
    plan_path = tmp_path / "plan.json"
    raw_dir = tmp_path / "raw"
    fake_cli = tmp_path / "fake_image_gen.py"
    fake_cli.write_text(
        """
import json
import sys
from pathlib import Path

args = sys.argv[1:]
out_dir = Path(args[args.index('--out-dir') + 1])
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / 'called.txt').write_text('ok', encoding='utf-8')
print(json.dumps({'args': args}))
""".strip(),
        encoding="utf-8",
    )

    plan = meme_pack.plan_pack(
        subject="round mascot",
        persona="科研打工人",
        style="clean-sticker",
        pack_size=16,
        mode="wechat",
        pack_name="Batch Test",
        image_provider="openai_images_api",
    )
    meme_pack.write_plan(plan_path, plan)

    record = meme_pack.generate_raw_batch(
        plan_path=plan_path,
        imagegen_cli=fake_cli,
        source_dir=raw_dir,
        limit=2,
        dry_run=True,
    )

    jobs = (raw_dir / "_imagegen-batch.jsonl").read_text(encoding="utf-8").splitlines()
    first_job = json.loads(jobs[0])
    assert record["dry_run"] is True
    assert record["jobs"] == 2
    assert len(jobs) == 2
    assert first_job["out"] == plan["image_prompts"][0]["raw_image_filename"]
    assert first_job["prompt"] == plan["image_prompts"][0]["prompt"]
    assert (raw_dir / "called.txt").exists()


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
        source_mode="motion_sheet",
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
        source_mode="motion_sheet",
        source_layout="auto",
        quality_mode="preview",
        strict_continuity_qc=False,
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
        source_mode="motion_sheet",
        source_layout="2x4",
        strict_continuity_qc=False,
    )

    first_item = result["items"][0]
    gif = Image.open(output / "wechat-submit" / "main" / "01.gif")

    assert first_item["animation_source"] == "sheet"
    assert first_item["source_layout"] == "2x4"
    assert first_item["source_frame_count"] == 8
    assert first_item["motion_profile"] == "micro"
    assert first_item["alignment_mode"] == "stable"
    assert first_item["rendered_frame_count"] == 8
    assert 6 <= gif.n_frames <= 8
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
        source_mode="motion_sheet",
        source_layout="4x4",
        strict_continuity_qc=False,
    )

    first_item = result["items"][0]
    gif = Image.open(output / "wechat-submit" / "main" / "01.gif")

    assert first_item["animation_source"] == "sheet"
    assert first_item["source_layout"] == "4x4"
    assert first_item["source_frame_count"] == 16
    assert first_item["rendered_frame_count"] == 16
    assert first_item["gif_frame_count"] >= 15
    assert 140 <= first_item["gif_duration_ms"] <= 160
    assert gif.n_frames >= 15


def test_build_pack_keyposes_renders_16_frame_gif_and_manifest_fields(tmp_path: Path):
    meme_pack = load_module()
    source = make_keypose_sheets(tmp_path, 24, "2x2")
    output = tmp_path / "pack"

    result = meme_pack.build_pack(
        source_dir=source,
        output_dir=output,
        entries=meme_pack.default_entries("科研打工人", 24),
        mode="wechat",
        source_mode="keyposes",
        keypose_layout="2x2",
        render_frame_count=16,
        strict_continuity_qc=True,
    )

    first_item = result["items"][0]
    gif = Image.open(output / "wechat-submit" / "main" / "01.gif")

    assert first_item["source_mode"] == "keyposes"
    assert first_item["animation_source"] == "keyposes"
    assert first_item["source_layout"] == "2x2"
    assert first_item["source_frame_count"] == 4
    assert first_item["motion_template"] == "soul_offline"
    assert first_item["rendered_frame_count"] == 16
    assert first_item["continuity_qc_status"] == "pass"
    assert first_item["continuity_errors"] == []
    assert "loop_closure_score" in first_item
    assert "motion_energy_score" in first_item
    assert "prop_lifecycle_errors" in first_item
    assert "prop_position_jump" in first_item
    assert "prop_area_jump" in first_item
    assert "face_shape_drift_score" in first_item
    assert "max_head_center_step_px" in first_item
    # De-jitter lets PIL merge byte-identical hold frames (summing their durations), so the
    # saved GIF may carry fewer than the 16 logical frames; the logical count stays 16.
    assert first_item["rendered_frame_count"] == 16
    assert 8 <= gif.n_frames <= 16
    # Chunk 1 timing: held poses play longer than transitions, so the saved GIF no longer
    # uses a single scalar duration, and the total still preserves the loop pace.
    frame_durations = [frame.info.get("duration", 0) for frame in ImageSequence.Iterator(gif)]
    assert len(set(frame_durations)) > 1
    assert 2200 <= sum(frame_durations) <= 2600


def test_build_pack_submission_requires_one_source_per_entry(tmp_path: Path):
    meme_pack = load_module()
    source = make_keypose_sheets(tmp_path, 3, "2x2")
    output = tmp_path / "pack"

    with pytest.raises(ValueError, match="build-preview"):
        meme_pack.build_pack(
            source_dir=source,
            output_dir=output,
            entries=meme_pack.default_entries("科研打工人", 24),
            mode="wechat",
            source_mode="keyposes",
            keypose_layout="2x2",
            quality_mode="submission",
            strict_continuity_qc=True,
        )


def test_build_preview_uses_first_sources_without_reuse_and_writes_html(tmp_path: Path):
    meme_pack = load_module()
    source = make_keypose_sheets(tmp_path, 3, "2x2")
    output = tmp_path / "preview"

    result = meme_pack.build_preview(
        source_dir=source,
        output_dir=output,
        entries=meme_pack.default_entries("科研打工人", 24),
        pack_name="前三张预览",
        persona="科研打工人",
        style="clean-sticker",
        source_mode="keyposes",
        keypose_layout="2x2",
        render_frame_count=16,
        quality_mode="submission",
        strict_qc=True,
        strict_continuity_qc=True,
        preview_count=3,
    )

    assert result["mode"] == "preview"
    assert result["pack_size"] == 3
    assert [Path(item["source"]).name for item in result["items"]] == ["01-2x2.png", "02-2x2.png", "03-2x2.png"]
    assert {path.name for path in (output / "named-gifs").glob("*.gif")} == {
        f"{item['name']}.gif" for item in result["items"]
    }
    assert result["items"][2]["caption_reserved_height"] < meme_pack.CAPTION_RESERVED_HEIGHT
    assert (
        result["items"][2]["continuity_metrics"]["caption_reserved_height"]
        == result["items"][2]["caption_reserved_height"]
    )
    preview_html = output / "preview.html"
    assert preview_html.exists()
    html = preview_html.read_text(encoding="utf-8")
    assert "前三张预览" in html
    assert html.count("<figure") == 3
    assert "named-gifs/" in html


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


def test_component_filter_removes_near_subject_fake_checkerboard_tiles():
    meme_pack = load_module()
    image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((44, 36, 86, 94), radius=12, fill=(70, 132, 216, 255))
    for y in range(30, 100, 14):
        for x in range(18, 112, 14):
            if 42 <= x <= 88 and 34 <= y <= 96:
                continue
            color = (238, 238, 238, 255) if ((x + y) // 14) % 2 else (204, 204, 204, 255)
            draw.rectangle((x, y, x + 5, y + 5), fill=color)

    cleaned, info = meme_pack.filter_subject_components(image, min_component_area=4, keep_distance=18)

    assert cleaned.getpixel((18, 30))[3] == 0
    assert cleaned.getpixel((110, 86))[3] == 0
    assert cleaned.getpixel((64, 60))[3] == 255
    assert info["removed_artifact_component_count"] > 0
    assert info["removed_checkerboard_component_count"] > 0


def test_component_filter_removes_thin_sheet_separator_lines():
    meme_pack = load_module()
    image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((44, 42, 86, 98), radius=12, fill=(70, 132, 216, 255))
    draw.rectangle((20, 28, 110, 30), fill=(126, 80, 34, 255))

    cleaned, info = meme_pack.filter_subject_components(image, min_component_area=4, keep_distance=18)

    assert cleaned.getpixel((60, 29))[3] == 0
    assert cleaned.getpixel((64, 60))[3] == 255
    assert info["removed_separator_line_count"] == 1


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


def test_qc_sheet_rejects_near_subject_checkerboard_residue(tmp_path: Path):
    meme_pack = load_module()
    rows, cols = meme_pack.parse_sheet_layout("2x4")
    cell = 96
    sheet = Image.new("RGBA", (cols * cell, rows * cell), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    for frame in range(rows * cols):
        row = frame // cols
        col = frame % cols
        x = col * cell
        y = row * cell
        draw.rounded_rectangle((x + 32, y + 24, x + 64, y + 76), radius=10, fill=(54, 116, 220, 255))
        for tile_y in range(y + 16, y + 82, 12):
            for tile_x in range(x + 10, x + 86, 12):
                if x + 28 <= tile_x <= x + 68 and y + 20 <= tile_y <= y + 80:
                    continue
                color = (238, 238, 238, 255) if ((tile_x + tile_y) // 12) % 2 else (204, 204, 204, 255)
                draw.rectangle((tile_x, tile_y, tile_x + 4, tile_y + 4), fill=color)
    path = tmp_path / "checker-residue.png"
    sheet.save(path)

    report = meme_pack.qc_sheet(path, source_layout="2x4", quality_mode="submission", strict=True)

    assert report["status"] == "fail"
    assert any("checkerboard residue" in error for error in report["errors"])


def test_qc_sheet_rejects_sheet_separator_line_residue(tmp_path: Path):
    meme_pack = load_module()
    rows, cols = meme_pack.parse_sheet_layout("2x4")
    cell = 96
    sheet = Image.new("RGBA", (cols * cell, rows * cell), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    for frame in range(rows * cols):
        row = frame // cols
        col = frame % cols
        x = col * cell
        y = row * cell
        draw.rounded_rectangle((x + 32, y + 30, x + 64, y + 78), radius=10, fill=(54, 116, 220, 255))
        draw.rectangle((x + 8, y + 18, x + 88, y + 20), fill=(126, 80, 34, 255))
    path = tmp_path / "separator-residue.png"
    sheet.save(path)

    report = meme_pack.qc_sheet(path, source_layout="2x4", quality_mode="submission", strict=True)

    assert report["status"] == "fail"
    assert any("separator line" in error for error in report["errors"])


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
            source_mode="single_bounce",
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


def test_caption_layout_treats_manual_breaks_as_soft_for_short_copy():
    meme_pack = load_module()

    lines, font = meme_pack.fit_text_lines(
        "收到\n但灵魂已离线",
        font_path=meme_pack.find_default_font(),
        max_width=214,
        max_height=76,
        max_font_size=34,
        min_font_size=16,
    )
    reserved = meme_pack.caption_reserved_height_for_text("收到\n但灵魂已离线", meme_pack.find_default_font())

    assert lines == ["收到但灵魂已离线"]
    assert font.size >= 26
    assert reserved < meme_pack.CAPTION_RESERVED_HEIGHT


def test_caption_layout_moves_short_copy_closer_to_subject():
    meme_pack = load_module()
    font_path = meme_pack.find_default_font()
    text = "收到\n但灵魂已离线"

    lines, font = meme_pack.fit_text_lines(text, font_path, max_width=214, max_height=76)
    reserved = meme_pack.caption_reserved_height_for_text(text, font_path)
    captioned = meme_pack.draw_caption(Image.new("RGBA", (240, 240), (0, 0, 0, 0)), text, font_path)

    assert reserved <= meme_pack.caption_text_height(lines, font) + 8
    assert captioned.getbbox()[1] <= 189


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
        source_mode="motion_sheet",
        strict_continuity_qc=False,
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
    assert "continuity_qc_status" in manifest["items"][0]

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
        source_mode="motion_sheet",
        strict_continuity_qc=False,
    )
    meme_pack.build_pack(
        source_dir=source,
        output_dir=output,
        entries=meme_pack.default_entries("码农", 16),
        mode="wechat",
        source_mode="motion_sheet",
        strict_continuity_qc=False,
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
