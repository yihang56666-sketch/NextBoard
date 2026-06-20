"""Unit tests for runtime_context module."""

import os
import sys

sys.path.insert(0, 'tools')

import runtime_context


def test_package_root_is_defined():
    """Package root should be defined and point to repo root."""
    assert runtime_context.PACKAGE_ROOT.exists()
    assert (runtime_context.PACKAGE_ROOT / "tools").exists()


def test_workspace_root_defaults_to_package_root():
    """Without env override, workspace_root should return package root."""
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


def test_allowed_write_roots_includes_workspace():
    """allowed_write_roots should include workspace root."""
    roots = runtime_context.allowed_write_roots()
    assert runtime_context.workspace_root() in roots
