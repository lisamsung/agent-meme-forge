from pathlib import Path


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
