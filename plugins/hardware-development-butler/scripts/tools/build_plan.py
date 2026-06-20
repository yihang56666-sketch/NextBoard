"""Generate a safe build plan without executing build or hardware actions.

The plan maps CubeMX/backend detection to embeddedskills commands as structured
argv arrays. This avoids quoting bugs on paths with spaces or non-ASCII
characters and keeps the butler in a read-only planning mode.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import cube_detect  # noqa: E402
import runtime_context  # noqa: E402
import safe_io  # noqa: E402

REPO_ROOT = runtime_context.PACKAGE_ROOT
PYTHON = sys.executable


def generate_plan(root: Path) -> dict[str, Any]:
    root = root.resolve()
    detection = cube_detect.detect(root)
    selected = detection.get("selected_backend")
    status = plan_status(selected)
    commands = planned_commands(root, selected, detection)
    backend = legacy_backend_name(selected)

    return {
        "schema_version": 1,
        "root": str(root),
        "status": status,
        "selected_backend": selected,
        "backend": backend,
        "backend_candidates": detection.get("backend_candidates", []),
        "commands": commands,
        "steps": legacy_steps(commands),
        "confirmation_gates": confirmation_gates(),
        "warnings": detection.get("warnings", []),
        "next_actions": next_actions(status, selected),
    }


def legacy_backend_name(selected: dict[str, Any] | None) -> str:
    if not selected:
        return "manual"
    backend = str(selected.get("backend", "manual"))
    if backend == "cmake-gcc":
        return "cmake"
    if backend == "make":
        return "makefile"
    return backend


def legacy_steps(commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "phase": item["phase"],
            "name": item["label"],
            "argv": item["argv"],
            "safe": not item.get("hardware_side_effect", False),
        }
        for item in commands
    ]


def plan_status(selected: dict[str, Any] | None) -> str:
    if selected is None:
        return "blocked-no-supported-backend"
    backend = selected.get("backend")
    if backend == "manual-choice-required":
        return "blocked-manual-backend-choice"
    if selected.get("supported_in_mvp") is False:
        return "blocked-unsupported-backend"
    return "ready"


def planned_commands(root: Path, selected: dict[str, Any] | None, detection: dict[str, Any]) -> list[dict[str, Any]]:
    commands = [
        command(
            label="Create project dossier",
            phase="inspect",
            argv=[
                PYTHON,
                "tools\\hardware_butler_inspect.py",
                "--root",
                path_arg(root),
                "--out-dir",
                path_arg(runtime_context.default_inspection_dir(root)),
                "--json",
            ],
            writes=["docs/inspections/<project>/"],
            reason="Create stable evidence before build attempts.",
        ),
        command(
            label="Detect CubeMX backend candidates",
            phase="inspect",
            argv=[PYTHON, "tools\\cube_detect.py", "--root", path_arg(root), "--json"],
            writes=[],
            reason="Confirm selected backend and avoid guessing when multiple projects exist.",
        ),
    ]

    if not selected or selected.get("backend") == "manual-choice-required":
        return commands

    backend = selected["backend"]
    evidence = selected.get("evidence", [])
    first_evidence = evidence[0]["path"] if evidence else ""

    if backend == "keil":
        commands.extend(keil_commands(root, first_evidence))
    elif backend == "cmake-gcc":
        commands.extend(gcc_commands(root, first_evidence))
    elif backend == "eide":
        commands.extend(eide_commands(root))

    commands.append(
        command(
            label="Classify build log after manual build",
            phase="diagnose",
            argv=[PYTHON, "tools\\build_log_classifier.py", "<build-log-path>", "--json"],
            writes=[],
            reason="Classify compiler/linker output before proposing fixes.",
            placeholders=["<build-log-path>"],
        )
    )
    return commands


def keil_commands(root: Path, project_rel: str) -> list[dict[str, Any]]:
    commands = [
        command(
            label="Scan Keil projects",
            phase="build-discovery",
            argv=[PYTHON, "embeddedskills\\keil\\scripts\\keil_project.py", "scan", "--root", path_arg(root), "--json"],
            writes=[],
            reason="Enumerate Keil projects before selecting a target.",
        )
    ]
    if project_rel:
        commands.append(
            command(
                label="List Keil targets",
                phase="build-discovery",
                argv=[
                    PYTHON,
                    "embeddedskills\\keil\\scripts\\keil_project.py",
                    "targets",
                    "--project",
                    path_arg(root / project_rel),
                    "--json",
                ],
                writes=[],
                reason="Keil builds require an explicit target when multiple targets exist.",
            )
        )
    commands.append(
        command(
            label="Prepare Keil build",
            phase="build-plan",
            argv=[PYTHON, "embeddedskills\\workflow\\scripts\\workflow_run.py", "build", "--json"],
            writes=[".embeddedskills/state.json", ".embeddedskills/build/"],
            reason="Run only after project/target is confirmed in .embeddedskills/config.json.",
            requires_confirmation=True,
        )
    )
    return commands


def gcc_commands(root: Path, project_rel: str) -> list[dict[str, Any]]:
    project_dir = root
    if project_rel:
        candidate = root / project_rel
        project_dir = candidate.parent if candidate.name.lower() in {"cmakelists.txt", "cmakepresets.json"} else candidate
    return [
        command(
            label="Scan CMake/GCC projects",
            phase="build-discovery",
            argv=[PYTHON, "embeddedskills\\gcc\\scripts\\gcc_project.py", "scan", "--root", path_arg(root), "--json"],
            writes=[],
            reason="Enumerate embedded CMake projects before configure/build.",
        ),
        command(
            label="List CMake presets",
            phase="build-discovery",
            argv=[PYTHON, "embeddedskills\\gcc\\scripts\\gcc_project.py", "presets", "--project", path_arg(project_dir), "--json"],
            writes=[],
            reason="Choose configure/build presets explicitly.",
        ),
        command(
            label="Prepare CMake/GCC build",
            phase="build-plan",
            argv=[PYTHON, "embeddedskills\\workflow\\scripts\\workflow_run.py", "build", "--json"],
            writes=[".embeddedskills/state.json", ".embeddedskills/build/"],
            reason="Run only after preset is confirmed in .embeddedskills/config.json.",
            requires_confirmation=True,
        ),
    ]


def eide_commands(root: Path) -> list[dict[str, Any]]:
    return [
        command(
            label="Scan EIDE projects",
            phase="build-discovery",
            argv=[PYTHON, "embeddedskills\\eide\\scripts\\eide_project.py", "scan", "--root", path_arg(root), "--json"],
            writes=[],
            reason="Enumerate EIDE projects before selecting a config.",
        ),
        command(
            label="Prepare EIDE build",
            phase="build-plan",
            argv=[PYTHON, "embeddedskills\\workflow\\scripts\\workflow_run.py", "build", "--json"],
            writes=[".embeddedskills/state.json", ".embeddedskills/build/"],
            reason="Run only after EIDE config is confirmed in .embeddedskills/config.json.",
            requires_confirmation=True,
        ),
    ]


def command(
    *,
    label: str,
    phase: str,
    argv: list[str],
    writes: list[str],
    reason: str,
    requires_confirmation: bool = False,
    placeholders: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "label": label,
        "phase": phase,
        "argv": argv,
        "writes": writes,
        "requires_confirmation": requires_confirmation,
        "hardware_side_effect": False,
        "reason": reason,
        "placeholders": placeholders or [],
    }


def confirmation_gates() -> list[dict[str, Any]]:
    return [
        {
            "action": "flash_or_erase",
            "requires_confirmation": True,
            "reason": "Flash, erase, and write-memory change connected target state.",
        },
        {
            "action": "debug_halt_reset_resume",
            "requires_confirmation": True,
            "reason": "Debug control changes target execution state.",
        },
        {
            "action": "can_send_or_network_scan",
            "requires_confirmation": True,
            "reason": "Bus frames and network scans can affect external systems.",
        },
    ]


def next_actions(status: str, selected: dict[str, Any] | None) -> list[str]:
    if status == "ready":
        return [
            "Review the generated plan with the user.",
            "Run build-discovery commands first.",
            "Write .embeddedskills/config.json only after project/target/preset is confirmed.",
        ]
    if status == "blocked-manual-backend-choice":
        return ["Ask the user to select one supported backend before build planning."]
    if selected is None:
        return ["Add Keil, CMake/GCC, or EIDE build metadata before build planning."]
    return ["Handle unsupported backend manually."]


def path_arg(path: Path) -> str:
    return str(path.resolve())


def render_markdown(plan: dict[str, Any]) -> str:
    selected = plan.get("selected_backend") or {}
    lines = [
        "# Safe Build Plan",
        "",
        f"- Root: `{plan['root']}`",
        f"- Status: `{plan['status']}`",
        f"- Selected backend: `{selected.get('backend', 'none')}`",
        "",
        "## Commands",
        "",
    ]
    for item in plan["commands"]:
        confirm = "yes" if item["requires_confirmation"] else "no"
        writes = ", ".join(item["writes"]) or "none"
        lines.append(f"### {item['label']}")
        lines.append("")
        lines.append(f"- Phase: `{item['phase']}`")
        lines.append(f"- Requires confirmation: {confirm}")
        lines.append(f"- Hardware side effect: {item['hardware_side_effect']}")
        lines.append(f"- Writes: {writes}")
        lines.append(f"- Reason: {item['reason']}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(item["argv"], ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")
    lines.extend(["## Confirmation Gates", ""])
    for gate in plan["confirmation_gates"]:
        lines.append(f"- `{gate['action']}`: {gate['reason']}")
    lines.extend(["", "## Next Actions", ""])
    for action in plan["next_actions"]:
        lines.append(f"- {action}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a safe build plan without executing it")
    parser.add_argument("--root", default=".", help="Project root to inspect")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    plan = generate_plan(Path(args.root))
    content = json.dumps(plan, ensure_ascii=False, indent=2) if args.as_json and not args.markdown else render_markdown(plan)
    if args.out:
        safe_io.safe_write_text(Path(args.out), content, allowed_roots=runtime_context.allowed_write_roots())
    else:
        print(content)


if __name__ == "__main__":
    main()
