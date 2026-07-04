"""Unit tests for runtime_context module."""

import os
from pathlib import Path

import pytest
import runtime_context


def test_package_root_is_defined():
    """Package root should be defined and point to repo root."""
    assert runtime_context.PACKAGE_ROOT.exists()
    assert (runtime_context.PACKAGE_ROOT / "tools").exists()
    assert runtime_context.embeddedskills_available(runtime_context.embeddedskills_root())


def test_embeddedskills_root_respects_env_variable(tmp_path: Path):
    """HW_BUTLER_EMBEDDEDSKILLS_ROOT should override default runtime discovery."""
    embedded = tmp_path / "embeddedskills"
    (embedded / "workflow" / "scripts").mkdir(parents=True)
    (embedded / "safety_gate.py").write_text("", encoding="utf-8")
    (embedded / "safety_cli.py").write_text("", encoding="utf-8")
    (embedded / "workflow" / "scripts" / "workflow_run.py").write_text("", encoding="utf-8")

    old_val = os.environ.get("HW_BUTLER_EMBEDDEDSKILLS_ROOT")
    try:
        os.environ["HW_BUTLER_EMBEDDEDSKILLS_ROOT"] = str(embedded)
        assert runtime_context.embeddedskills_root() == embedded.resolve()
        status = runtime_context.embeddedskills_status()
        assert status["available"] is True
        assert status["source"] == "environment"
    finally:
        if old_val:
            os.environ["HW_BUTLER_EMBEDDEDSKILLS_ROOT"] = old_val
        else:
            os.environ.pop("HW_BUTLER_EMBEDDEDSKILLS_ROOT", None)


def test_embeddedskills_root_falls_back_to_plugin_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A clean root clone can use the packaged plugin runtime mirror."""
    package_root = tmp_path / "package"
    mirror = package_root / "plugins" / "hardware-development-butler" / "scripts" / "embeddedskills"
    (mirror / "workflow" / "scripts").mkdir(parents=True)
    (mirror / "safety_gate.py").write_text("", encoding="utf-8")
    (mirror / "safety_cli.py").write_text("", encoding="utf-8")
    (mirror / "workflow" / "scripts" / "workflow_run.py").write_text("", encoding="utf-8")

    monkeypatch.setattr(runtime_context, "PACKAGE_ROOT", package_root)
    monkeypatch.delenv("HW_BUTLER_EMBEDDEDSKILLS_ROOT", raising=False)

    assert runtime_context.embeddedskills_root() == mirror.resolve()
    status = runtime_context.embeddedskills_status()
    assert status["available"] is True
    assert status["source"] == "plugin-runtime"


def test_workspace_root_defaults_to_package_root():
    """Without env override, workspace_root should return package root."""
    # Clear environment variables
    old_val = os.environ.pop("HW_BUTLER_ROOT", None)
    old_legacy = os.environ.pop("HARDWARE_BUTLER_WORKSPACE_ROOT", None)

    try:
        root = runtime_context.workspace_root()
        assert root == runtime_context.PACKAGE_ROOT
    finally:
        if old_val:
            os.environ["HW_BUTLER_ROOT"] = old_val
        if old_legacy:
            os.environ["HARDWARE_BUTLER_WORKSPACE_ROOT"] = old_legacy


def test_workspace_root_respects_env_variable(tmp_path: Path):
    """HW_BUTLER_ROOT env variable should override default."""
    test_root = tmp_path / "test-workspace"
    test_root.mkdir()

    old_val = os.environ.get("HW_BUTLER_ROOT")
    try:
        os.environ["HW_BUTLER_ROOT"] = str(test_root)
        root = runtime_context.workspace_root()
        assert root == test_root.resolve()
    finally:
        if old_val:
            os.environ["HW_BUTLER_ROOT"] = old_val
        else:
            os.environ.pop("HW_BUTLER_ROOT", None)


def test_workspace_root_accepts_explicit_path(tmp_path: Path):
    """Explicit path parameter should take precedence."""
    explicit = tmp_path / "explicit"
    explicit.mkdir()

    root = runtime_context.workspace_root(explicit=explicit)
    assert root == explicit.resolve()


def test_allowed_write_roots_includes_workspace():
    """allowed_write_roots should include workspace root."""
    roots = runtime_context.allowed_write_roots()
    assert runtime_context.workspace_root() in roots


def test_allowed_write_roots_deduplicates(tmp_path: Path):
    """allowed_write_roots should deduplicate identical paths."""
    test_root = tmp_path / "test"
    test_root.mkdir()

    roots = runtime_context.allowed_write_roots(test_root, test_root)
    # Should not have duplicates
    assert len(roots) == len(set(str(r) for r in roots))


def test_default_inspection_dir_uses_project_name(tmp_path: Path):
    """default_inspection_dir should use project name."""
    project = tmp_path / "my-project"
    project.mkdir()

    inspection = runtime_context.default_inspection_dir(project)
    assert inspection.name == "my-project"
    assert "inspections" in inspection.parts
