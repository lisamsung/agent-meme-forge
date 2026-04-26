from pathlib import Path
from urllib.parse import urljoin


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "generate-meme-gif-pack" / "SKILL.md"
REFERENCES = ROOT / "skills" / "generate-meme-gif-pack" / "references"


def test_skill_frontmatter_and_hard_rules_are_present():
    text = SKILL.read_text(encoding="utf-8")

    assert "name: generate-meme-gif-pack" in text
    assert "Use when" in text
    assert "16 or 24" in text
    assert "18" in text and "self_use" in text
    assert "no text" in text.lower()
    assert "meme_pack.py" in text
    assert "text_concept" in text
    assert "image_gen" in text
    assert "motion sheet" in text
    assert "keyposes" in text
    assert "--strict-continuity-qc" in text
    assert "4x4" in text
    assert "16-frame" in text
    assert "--source-layout" in text
    assert "qc-sheet" in text
    assert "accept-generated" in text
    assert "generated-index.json" in text
    assert "plan-wizard" in text
    assert "choose" in text.lower() or "ask" in text.lower()
    assert "--quality-mode submission" in text
    assert "--strict-qc" in text
    assert "MUST call" in text
    assert "do not stop after" in text
    assert "没人用的表情包就是垃圾表情包" in text
    assert "sendability gate" in text.lower()
    assert "local_effects" in text
    assert "face_shape_drift_score" in text
    assert "prop_position_jump" in text
    assert "Intake-first rule" in text
    assert "explicitly said to use defaults" in text


def test_references_cover_wechat_prompt_persona_and_humor():
    expected = [
        "wechat-spec.md",
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
