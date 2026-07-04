from __future__ import annotations

from tools import release_verify


def test_quick_profile_covers_no_hardware_demo_and_plugin_sync() -> None:
    names = {step.name for step in release_verify.build_steps("quick")}

    assert "package-plugin-runtime" in names
    assert "demo-guide" in names
    assert "demo-doctor" in names
    assert "demo-evidence-ask" in names
    assert "plugin-validation" in names
    assert "quick-tests" in names


def test_full_profile_covers_launch_verification_matrix() -> None:
    names = {step.name for step in release_verify.build_steps("full")}

    assert "lint" in names
    assert "typecheck" in names
    assert "tests" in names
    assert "butler-validation" in names
    assert "editable-install-dry-run" in names
    assert "dev-requirements-dry-run" in names
    assert "all-requirements-dry-run" in names
    assert "diff-check" in names


def test_format_command_keeps_command_readable() -> None:
    step = next(step for step in release_verify.STEPS if step.name == "demo-evidence-ask")

    command = release_verify.format_command(step.command)

    assert "hardware_butler.py" in command
    assert "Mcu.Package" in command


def test_build_env_defaults_python_children_to_utf8(monkeypatch) -> None:
    monkeypatch.delenv("PYTHONUTF8", raising=False)
    monkeypatch.delenv("PYTHONIOENCODING", raising=False)

    env = release_verify.build_env()

    assert env["PYTHONUTF8"] == "1"
    assert env["PYTHONIOENCODING"] == "utf-8"
