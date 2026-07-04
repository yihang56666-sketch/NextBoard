"""Unified CLI with grouped commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

from hardware_butler import (  # noqa: E402
    configure_stdio,
)
from hardware_butler import (
    main as original_main,
)
from logger import get_logger  # noqa: E402

logger = get_logger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create grouped command parser."""
    parser = argparse.ArgumentParser(
        prog="hardware-butler",
        description="Hardware Development Butler - Unified CLI",
    )
    parser.add_argument("--version", action="version", version="0.1.0")

    subparsers = parser.add_subparsers(dest="group", help="Command groups")

    # Project commands
    project = subparsers.add_parser("project", help="Project operations")
    project_sub = project.add_subparsers(dest="command")
    project_sub.add_parser("inspect", help="Inspect project structure")
    project_sub.add_parser("onboard", help="Onboard new project")
    project_sub.add_parser("status", help="Show project status")
    project_sub.add_parser("doctor", help="Check environment health")

    # Chip commands
    chip = subparsers.add_parser("chip", help="Chip operations")
    chip_sub = chip.add_subparsers(dest="command")
    chip_sub.add_parser("dossier", help="Create chip dossier")
    chip_sub.add_parser("summarize", help="Summarize chip manual")

    # Firmware commands
    firmware = subparsers.add_parser("firmware", help="Firmware operations")
    firmware_sub = firmware.add_subparsers(dest="command")
    firmware_sub.add_parser("plan", help="Plan firmware implementation")
    firmware_sub.add_parser("patch", help="Generate firmware patches")
    firmware_sub.add_parser("integrate", help="Integrate with CubeMX")

    # Action commands
    action = subparsers.add_parser("action", help="Hardware actions")
    action_sub = action.add_subparsers(dest="command")
    action_sub.add_parser("plan", help="Plan hardware action")
    action_sub.add_parser("execute", help="Execute action")
    action_sub.add_parser("audit", help="Audit action log")

    # Build commands
    build = subparsers.add_parser("build", help="Build operations")
    build_sub = build.add_subparsers(dest="command")
    build_sub.add_parser("detect", help="Detect build backend")
    build_sub.add_parser("plan", help="Generate build plan")
    build_sub.add_parser("run", help="Run build commands")

    # Fallback to original CLI
    subparsers.add_parser("legacy", help="Use original flat CLI")
    subparsers.add_parser("guide", help="Show first-day guide", add_help=False)

    return parser


def main() -> None:
    """Unified CLI entry point."""
    configure_stdio()

    parser = create_parser()
    args, remaining = parser.parse_known_args()

    # If no group specified or legacy, use original CLI
    if args.group == "guide":
        sys.argv = [sys.argv[0], "guide"] + remaining
        original_main()
        return

    if not args.group or args.group == "legacy":
        logger.info("Using legacy CLI")
        original_main()
        return

    # Map grouped commands to original commands
    command_map = {
        ("project", "inspect"): "inspect",
        ("project", "onboard"): "onboard",
        ("project", "status"): "status",
        ("project", "doctor"): "doctor",
        ("chip", "dossier"): "chip-dossier",
        ("chip", "summarize"): "summarize-manual",
        ("firmware", "plan"): "firmware-plan",
        ("firmware", "patch"): "firmware-patch",
        ("firmware", "integrate"): "firmware-integrate",
        ("action", "plan"): "plan-action",
        ("action", "execute"): "execute-action",
        ("action", "audit"): "safety-audit",
        ("build", "detect"): "detect",
        ("build", "plan"): "plan-build",
        ("build", "run"): "run-plan",
    }

    key = (args.group, args.command)
    if key in command_map:
        # Rewrite sys.argv to call original command
        original_command = command_map[key]
        sys.argv = [sys.argv[0], original_command] + remaining
        logger.debug(f"Mapped {key} -> {original_command}")
        original_main()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
