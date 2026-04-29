from pathlib import Path
from urllib.parse import urljoin


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "generate-meme-gif-pack" / "SKILL.md"
REFERENCES = ROOT / "skills" / "generate-meme-gif-pack" / "references"


def test_skill_frontmatter_and_hard_rules_are_present():
    text = SKILL.read_text(encoding="utf-8")

    assert "name: generate-meme-gif-pack" in text
    assert "Use when" in text
    assert "TRIGGER" in text and "SKIP" in text
    assert "generate-meme-gif-pack-ai-studio" in text
    assert "16 or 24" in text
    assert "18" in text and "self_use" in text
    assert "no text" in text.lower()
    assert "meme_pack.py" in text
    assert "text_concept" in text
    assert "image_gen" in text
    assert "keyposes" in text
    assert "plan-wizard" in text
    assert "choose" in text.lower() or "ask" in text.lower()
    assert "terminal action" in text
    assert "openai_images_api" in text
    assert "next turn" in text
    assert "没人用的表情包就是垃圾表情包" in text
    assert "sendability gate" in text.lower()
    assert "Required Intake" in text
    assert "Tool Boundary" in text
    assert "Required References" in text
    assert "preview.html" in text
    assert "named-gifs" in text
    assert "external_files" in text
    assert len(text.split()) < 650


def test_references_cover_wechat_prompt_persona_and_humor():
    expected = [
        "agent-rules.md",
        "commands.md",
        "pressure-scenarios.md",
        "qc-checklist.md",
        "tool-boundary.md",
        "workflow.md",
        "wechat-spec.md",
        "wechat-platform-upload.md",
        "prompt-rules.md",
        "styles.md",
        "personas.md",
        "meme-library.md",
    ]

    for filename in expected:
        path = REFERENCES / filename
        assert path.exists(), filename
        text = path.read_text(encoding="utf-8")
        assert len(text) > 300


def test_wechat_platform_upload_runbook_is_documented():
    skill_text = SKILL.read_text(encoding="utf-8")
    upload_text = (REFERENCES / "wechat-platform-upload.md").read_text(encoding="utf-8")
    combined = skill_text + "\n" + upload_text

    assert "Playwright" in combined
    assert "Microsoft Edge" in combined
    assert "sticker.weixin.qq.com" in combined
    assert "--browser msedge" in combined
    assert "--persistent" in combined
    assert "扫码" in combined
    assert "setInputFiles" in combined
    assert "wechat-submit/main" in combined
    assert "banner.png" in combined
    assert "cover.png" in combined
    assert "icon.png" in combined
    assert "版权归属" in combined
    assert "人物角色 - 女人" in combined
    assert "接受赞赏" in combined
    assert "赞赏引导图" in combined
    assert "赞赏致谢图" in combined
    assert "750x560" in combined
    assert "750x750" in combined
    assert "pack builder does not create reward images automatically" in combined
    assert "保存" in combined
    assert "提交" in combined
    assert "审核驳回" in combined


def test_prompt_rules_support_direct_text_generation():
    text = (REFERENCES / "prompt-rules.md").read_text(encoding="utf-8")

    assert "text_concept" in text
    assert "image_gen" in text
    assert "no official logo" in text
    assert "240x240" in text
    assert "same bounding box" in text
    assert "micro-motion" in text
    assert "in-between animation" in text
    assert "motion_profile=micro" in text
    assert "lateral drift" in text
    assert "2x4" in text
    assert "2x2" in text
    assert "keypose" in text.lower()
    assert "continuity" in text.lower()
    assert "4x4" in text
    assert "16-frame" in text
    assert "1x4" in text
    assert "transparent PNG background" in text
    assert "ChatGPT Images" in text
    assert "gpt-image-2" in text
    assert "output_format" in text
    assert "checkerboard" in text
    assert "QC" in text or "qc" in text
    assert "edge" in text
    assert "accept-generated" in text
    assert "only cute" in text
    assert "local_effects" in text
    assert "face/head shape drift" in text
    assert "prop position jump" in text
    assert "intermediate raw keypose sheet" in text
    assert "not the final deliverable" in text
    assert "final handoff" in text
    assert "not a stopping point" in text
    assert "full pack" in text
    assert "terminal action" in text
    assert "same-turn" in text


def test_skill_references_hold_detailed_workflow_rules():
    combined = "\n".join(
        (REFERENCES / filename).read_text(encoding="utf-8")
        for filename in [
            "agent-rules.md",
            "workflow.md",
            "commands.md",
            "qc-checklist.md",
            "tool-boundary.md",
            "pressure-scenarios.md",
        ]
    )

    assert "generate-raw-batch" in combined
    assert "openai_images_api" in combined
    assert "--strict-continuity-qc" in combined
    assert "first 3" in combined
    assert "QC checkpoint" in combined
    assert "2x2" in combined
    assert "16-frame" in combined
    assert "face/head" in combined
    assert "prop position" in combined
    assert "Google AI Studio" in combined


def test_pages_readme_link_stays_inside_project_or_github():
    text = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    marker = 'href="'
    links = [part.split('"', 1)[0] for part in text.split(marker)[1:]]
    readme_links = [link for link in links if "README.zh-CN.md" in link]

    assert readme_links
    for link in readme_links:
        resolved = urljoin("https://lisamsung.github.io/agent-meme-forge/", link)
        assert resolved.startswith("https://lisamsung.github.io/agent-meme-forge/") or resolved.startswith(
            "https://github.com/lisamsung/agent-meme-forge/"
        )
