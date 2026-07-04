"""Tests for the repo-local plugin packaging helper."""

from pathlib import Path

import package_hardware_butler_plugin as packager


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_package_runtime_preserves_packaged_embeddedskills_when_root_checkout_is_absent(
    tmp_path: Path, monkeypatch
) -> None:
    """A clean GitHub checkout should not delete its only embeddedskills runtime."""
    repo = tmp_path / "repo"
    plugin_root = repo / "plugins" / "hardware-development-butler"
    runtime_root = plugin_root / "scripts"

    for dirname in ("tools", "tests", "agents", ".codex", "nextboard", "docs"):
        (repo / dirname).mkdir(parents=True)
    for filename in (
        "README.md",
        "AGENTS.md",
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-all.txt",
        "conftest.py",
    ):
        _write(repo / filename, f"# {filename}\n")
    _write(repo / "docs" / "README.md", "# docs\n")
    _write(repo / "tools" / "hardware_butler.py", "print('tool')\n")

    embedded = runtime_root / "embeddedskills"
    _write(embedded / "safety_gate.py", "SENTINEL = 'keep me'\n")
    _write(embedded / "safety_cli.py", "")
    _write(embedded / "workflow" / "scripts" / "workflow_run.py", "")

    monkeypatch.setattr(packager, "REPO_ROOT", repo)
    monkeypatch.setattr(packager, "PLUGIN_ROOT", plugin_root)
    monkeypatch.setattr(packager, "RUNTIME_ROOT", runtime_root)
    monkeypatch.delenv(packager.ENV_EMBEDDEDSKILLS_ROOT, raising=False)

    copied = packager.package_runtime()

    assert (embedded / "safety_gate.py").read_text(encoding="utf-8") == "SENTINEL = 'keep me'\n"
    assert any(item == "embeddedskills/ (preserved from plugin-runtime)" for item in copied)
    assert (runtime_root / "tools" / "hardware_butler.py").is_file()
