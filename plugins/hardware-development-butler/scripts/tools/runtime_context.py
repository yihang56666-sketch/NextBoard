"""Runtime roots for package and workspace execution modes."""

from __future__ import annotations

import os
from pathlib import Path

# Legacy environment variable (kept for compatibility)
ENV_WORKSPACE_ROOT = "HARDWARE_BUTLER_WORKSPACE_ROOT"
# New shorter environment variable
ENV_BUTLER_ROOT = "HW_BUTLER_ROOT"
ENV_EMBEDDEDSKILLS_ROOT = "HW_BUTLER_EMBEDDEDSKILLS_ROOT"

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


def embeddedskills_root(explicit: Path | None = None) -> Path:
    """Return the embeddedskills runtime root.

    A GitHub checkout may provide embeddedskills as a root-level sibling, an
    explicit external checkout, or the packaged plugin runtime mirror. The
    first two are best for development; the plugin mirror keeps packaged and
    clean-clone workflows inspectable when the root checkout is intentionally
    external.
    """
    if explicit:
        return explicit.expanduser().resolve()

    if override := os.getenv(ENV_EMBEDDEDSKILLS_ROOT):
        return Path(override).expanduser().resolve()

    for candidate in embeddedskills_candidates():
        if embeddedskills_available(candidate):
            return candidate.resolve()

    return (PACKAGE_ROOT / "embeddedskills").resolve()


def embeddedskills_candidates() -> list[Path]:
    """Candidate locations for the embeddedskills runtime."""
    return _dedupe_roots(
        [
            PACKAGE_ROOT / "embeddedskills",
            PACKAGE_ROOT / "plugins" / "hardware-development-butler" / "scripts" / "embeddedskills",
        ]
    )


def embeddedskills_available(root: Path) -> bool:
    """Return True when a candidate has the minimum runtime files."""
    return (
        (root / "safety_gate.py").is_file()
        and (root / "safety_cli.py").is_file()
        and (root / "workflow" / "scripts" / "workflow_run.py").is_file()
    )


def embeddedskills_status(explicit: Path | None = None) -> dict[str, str | bool]:
    """Machine-readable status for doctor output and onboarding docs."""
    root = embeddedskills_root(explicit)
    source = "missing"
    if os.getenv(ENV_EMBEDDEDSKILLS_ROOT):
        source = "environment"
    elif root == (PACKAGE_ROOT / "embeddedskills").resolve():
        source = "workspace"
    elif root == (PACKAGE_ROOT / "plugins" / "hardware-development-butler" / "scripts" / "embeddedskills").resolve():
        source = "plugin-runtime"
    return {
        "available": embeddedskills_available(root),
        "path": str(root),
        "source": source,
        "env": ENV_EMBEDDEDSKILLS_ROOT,
    }


def allowed_write_roots(*extra_roots: Path) -> list[Path]:
    """Get list of allowed write roots.

    Args:
        extra_roots: Additional allowed root directories

    Returns:
        Deduplicated list of allowed root paths
    """
    roots = [workspace_root(), *extra_roots]
    return _dedupe_roots(roots)


def _dedupe_roots(roots: list[Path]) -> list[Path]:
    """Deduplicate paths while preserving order."""
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
