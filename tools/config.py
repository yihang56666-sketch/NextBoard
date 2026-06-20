"""Configuration management for hardware butler."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class WorkspaceConfig:
    """Workspace-level configuration."""
    root: Path
    allowed_roots: list[Path] = field(default_factory=list)
    chip_cache_dir: Path | None = None

    def __post_init__(self) -> None:
        self.root = self.root.resolve()
        if not self.allowed_roots:
            self.allowed_roots = [self.root]
        self.allowed_roots = [p.resolve() for p in self.allowed_roots]


@dataclass
class ToolsConfig:
    """External tool paths."""
    jlink: Path | None = None
    openocd: Path | None = None
    probe_rs: Path | None = None
    keil_uvision: Path | None = None


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    file: Path | None = None


@dataclass
class ButlerConfig:
    """Complete hardware butler configuration."""
    workspace: WorkspaceConfig
    tools: ToolsConfig = field(default_factory=ToolsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, workspace_root: Path) -> ButlerConfig:
        """Load config from dictionary."""
        ws_data = data.get("workspace", {})
        workspace = WorkspaceConfig(
            root=Path(ws_data.get("root", workspace_root)),
            allowed_roots=[Path(p) for p in ws_data.get("allowed_roots", [])],
            chip_cache_dir=Path(ws_data["chip_cache_dir"]) if ws_data.get("chip_cache_dir") else None,
        )

        tools_data = data.get("tools", {})
        tools = ToolsConfig(
            jlink=Path(tools_data["jlink"]) if tools_data.get("jlink") else None,
            openocd=Path(tools_data["openocd"]) if tools_data.get("openocd") else None,
            probe_rs=Path(tools_data["probe_rs"]) if tools_data.get("probe_rs") else None,
            keil_uvision=Path(tools_data["keil_uvision"]) if tools_data.get("keil_uvision") else None,
        )

        log_data = data.get("logging", {})
        logging_cfg = LoggingConfig(
            level=log_data.get("level", "INFO"),
            file=Path(log_data["file"]) if log_data.get("file") else None,
        )

        return cls(workspace=workspace, tools=tools, logging=logging_cfg)

    @classmethod
    def load(cls, config_file: Path | None = None, *, workspace_root: Path | None = None) -> ButlerConfig:
        """Load configuration from file or environment.

        Priority:
        1. Explicit config_file parameter
        2. HW_BUTLER_CONFIG environment variable
        3. .hardware-butler.json in current directory
        4. ~/.hardware-butler/config.json
        5. Default configuration
        """
        # Determine workspace root
        if workspace_root is None:
            workspace_root = _detect_workspace_root()

        # Find config file
        if config_file is None:
            config_file = _find_config_file()

        # Load from file if exists
        if config_file and config_file.exists():
            data = json.loads(config_file.read_text(encoding="utf-8"))
            return cls.from_dict(data, workspace_root=workspace_root)

        # Default configuration
        return cls(workspace=WorkspaceConfig(root=workspace_root))


def _detect_workspace_root() -> Path:
    """Detect workspace root from environment or package location."""
    if root := os.getenv("HW_BUTLER_ROOT"):
        return Path(root).expanduser().resolve()

    # Use package root as fallback
    import runtime_context

    return Path(runtime_context.PACKAGE_ROOT)


def _find_config_file() -> Path | None:
    """Find configuration file in standard locations."""
    # Environment variable
    if env_path := os.getenv("HW_BUTLER_CONFIG"):
        path = Path(env_path).expanduser()
        if path.exists():
            return path

    # Current directory
    local_config = Path.cwd() / ".hardware-butler.json"
    if local_config.exists():
        return local_config

    # User home directory
    user_config = Path.home() / ".hardware-butler" / "config.json"
    if user_config.exists():
        return user_config

    return None
