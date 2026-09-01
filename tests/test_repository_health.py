import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_open_source_maintenance_files_are_present():
    required = [
        "CHANGELOG.md",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "SECURITY.md",
        "SUPPORT.md",
        "THIRD_PARTY_NOTICES.md",
        ".github/CODEOWNERS",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/workflows/ci.yml",
        "skills/generate-meme-gif-pack/assets/fonts/OFL.txt",
        "skills/generate-meme-gif-pack/assets/fonts/ZCOOLKuaiLe-Regular.ttf",
    ]

    missing = [path for path in required if not (ROOT / path).is_file()]
    assert not missing, missing


def test_release_version_is_documented():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
    assert match, "pyproject.toml must declare a project version"

    version = match.group(1)
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{version}] -" in changelog
    assert f"releases/tag/v{version}" in changelog


def test_ci_actions_are_pinned_to_commit_shas():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    action_refs = re.findall(r"^\s*uses:\s*[^@\s]+@([^\s]+)", workflow, re.MULTILINE)

    assert action_refs
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in action_refs), action_refs
