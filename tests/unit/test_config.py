"""Unit tests for config module."""

import json
import os
from pathlib import Path

import config


def test_workspace_config_initialization():
    """WorkspaceConfig should initialize with proper defaults."""
    cfg = config.WorkspaceConfig(root=Path("/test"))

    assert cfg.root == Path("/test").resolve()
    assert cfg.root in cfg.allowed_roots


def test_workspace_config_resolves_paths(tmp_path: Path):
    """WorkspaceConfig should resolve all paths."""
    cfg = config.WorkspaceConfig(
        root=tmp_path,
        allowed_roots=[tmp_path / "subdir"],
    )

    assert cfg.root.is_absolute()
    assert all(p.is_absolute() for p in cfg.allowed_roots)


def test_butler_config_default_load(tmp_path: Path):
    """ButlerConfig.load should work with no config file."""
    # Clear environment
    old_env = os.environ.pop("HW_BUTLER_CONFIG", None)
    old_root = os.environ.pop("HW_BUTLER_ROOT", None)

    try:
        cfg = config.ButlerConfig.load(workspace_root=tmp_path)

        assert cfg.workspace.root == tmp_path
        assert cfg.logging.level == "INFO"
        assert cfg.tools.jlink is None
    finally:
        if old_env:
            os.environ["HW_BUTLER_CONFIG"] = old_env
        if old_root:
            os.environ["HW_BUTLER_ROOT"] = old_root


def test_butler_config_loads_from_file(tmp_path: Path):
    """ButlerConfig.load should read config from file."""
    config_file = tmp_path / "config.json"
    config_data = {
        "workspace": {
            "root": str(tmp_path),
            "allowed_roots": [str(tmp_path)],
        },
        "logging": {
            "level": "DEBUG",
        },
    }
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    cfg = config.ButlerConfig.load(config_file=config_file)

    assert cfg.workspace.root == tmp_path
    assert cfg.logging.level == "DEBUG"


def test_butler_config_respects_env_variable(tmp_path: Path, monkeypatch):
    """ButlerConfig should respect HW_BUTLER_ROOT environment variable."""
    test_root = tmp_path / "workspace"
    test_root.mkdir()

    monkeypatch.setenv("HW_BUTLER_ROOT", str(test_root))

    cfg = config.ButlerConfig.load()

    assert cfg.workspace.root == test_root.resolve()


def test_tools_config_paths(tmp_path: Path):
    """ToolsConfig should handle optional tool paths."""
    tools = config.ToolsConfig(
        jlink=tmp_path / "jlink.exe",
        openocd=None,
    )

    assert tools.jlink == tmp_path / "jlink.exe"
    assert tools.openocd is None
