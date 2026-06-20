"""Runtime roots for package and workspace execution modes."""

from __future__ import annotations

import os
from pathlib import Path

# Legacy environment variable (kept for compatibility)
ENV_WORKSPACE_ROOT = "HARDWARE_BUTLER_WORKSPACE_ROOT"
# New shorter environment variable
ENV_BUTLER_ROOT = "HW_BUTLER_ROOT"

TOOLS_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = TOOLS_DIR.parent


def workspace_root(explicit: Path | None = None) -> Path:
    """Get workspace root directory.

    Priority:
    1. Explicit parameter
    2. HW_BUTLER_ROOT environment variable
    3. HARDWARE_BUTLER_WORKSPACE_ROOT (legacy, for compatibility)
    4. Package root (where tools/ is located)

    Args:
        explicit: Explicitly provided workspace root

    Returns:
        Resolved workspace root path
    """
    if explicit:
        return explicit.resolve()

    # Check new environment variable first
    if override := os.getenv(ENV_BUTLER_ROOT):
        return Path(override).expanduser().resolve()

    # Check legacy environment variable
    if override := os.getenv(ENV_WORKSPACE_ROOT):
        return Path(override).expanduser().resolve()

    # Use package root as safe default instead of cwd()
    return PACKAGE_ROOT


def allowed_write_roots(*extra_roots: Path) -> list[Path]:
    """Get list of allowed write roots.

    Args:
        extra_roots: Additional allowed root directories

    Returns:
        Deduplicated list of allowed root paths
    """
    roots = [workspace_root(), *extra_roots]
    result: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        resolved = root.resolve()
        key = str(resolved).lower()
        if key not in seen:
            seen.add(key)
            result.append(resolved)
    return result


def default_inspection_dir(project_root: Path) -> Path:
    """Get default inspection output directory for a project.

    Args:
        project_root: Project root directory

    Returns:
        Path to docs/inspections/<project_name>
    """
    return workspace_root() / "docs" / "inspections" / project_root.resolve().name
