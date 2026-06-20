"""Unit tests for runtime_context module."""

import os
from pathlib import Path

import runtime_context


def test_package_root_is_defined():
    """Package root should be defined and point to repo root."""
    assert runtime_context.PACKAGE_ROOT.exists()
    assert (runtime_context.PACKAGE_ROOT / "tools").exists()
    assert (runtime_context.PACKAGE_ROOT / "embeddedskills").exists()


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
