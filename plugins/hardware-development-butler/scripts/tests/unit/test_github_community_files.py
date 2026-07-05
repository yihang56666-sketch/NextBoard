from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_note_config_covers_launch_labels() -> None:
    config_path = REPO_ROOT / ".github" / "release.yml"
    if not config_path.exists():
        pytest.skip("release note config is only required in the root GitHub repository")

    text = config_path.read_text(encoding="utf-8")

    assert "changelog:" in text
    assert "Safety And Hardware Gates" in text
    assert "User Workflows" in text
    assert "Documentation" in text
    assert "Other Changes" in text
    for label in ("safety", "hardware", "enhancement", "documentation", "bug", "dependencies", "chore"):
        assert f"- {label}" in text
    assert '- "*"' in text
