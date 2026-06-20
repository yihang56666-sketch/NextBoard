"""Propose .embeddedskills/config.json without writing by default.

This bridges the butler's project detection with embeddedskills runtime config.
It is intentionally conservative: missing Keil targets, GCC presets, or EIDE
configs block writes until the user supplies explicit values.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import build_plan  # noqa: E402
import runtime_context  # noqa: E402
import safe_io  # noqa: E402

BACKEND_TO_WORKFLOW = {
    "keil": "keil",
    "cmake-gcc": "gcc",
    "eide": "eide",
}


def propose_config(
    root: Path,
    *,
    target: str = "",
    preset: str = "",
    config_name: str = "",
) -> dict[str, Any]:
    root = root.resolve()
    plan = build_plan.generate_plan(root)
    selected = plan.get("selected_backend") or {}
    backend = selected.get("backend", "")
    config_path = root / ".embeddedskills" / "config.json"
    required_inputs: list[str] = []
    warnings: list[str] = []
    config: dict[str, Any] = {
        "workflow": {
            "preferred_build": BACKEND_TO_WORKFLOW.get(backend, "auto"),
        }
    }

    evidence = selected.get("evidence", [])
    first_path = evidence[0]["path"] if evidence else ""

    if backend == "keil":
        if not target:
            required_inputs.append("keil.target")
        config["keil"] = {
            "project": first_path,
            "target": target,
            "log_dir": ".embeddedskills/build",
        }
    elif backend == "cmake-gcc":
        if not preset:
            required_inputs.append("gcc.preset")
        config["gcc"] = {
            "project": project_dir_from_cmake_evidence(first_path),
            "preset": preset,
            "log_dir": ".embeddedskills/build",
        }
    elif backend == "eide":
        if not config_name:
            required_inputs.append("eide.config")
        config["eide"] = {
            "project": ".",
            "config": config_name,
            "log_dir": ".embeddedskills/build",
        }
    else:
        warnings.append(f"No supported backend selected: {backend or 'none'}")

    status = "ready-to-write" if not required_inputs and backend in BACKEND_TO_WORKFLOW else "needs-input"
    return {
        "schema_version": 1,
        "root": str(root),
        "status": status,
        "config_path": str(config_path),
        "selected_backend": selected,
        "required_inputs": required_inputs,
        "warnings": warnings + [item["message"] for item in plan.get("warnings", [])],
        "proposed_config": config,
        "write_policy": {
            "default": "dry-run",
            "write_requires": ["--write", "--confirm-write", "no required_inputs"],
            "preserve_existing": True,
            "hardware_actions": "not proposed by default",
            "backup_existing": True,
        },
        "next_actions": next_actions(status, required_inputs, backend),
    }


def project_dir_from_cmake_evidence(path: str) -> str:
    if not path:
        return "."
    p = Path(path)
    if p.name in {"CMakeLists.txt", "CMakePresets.json"}:
        parent = p.parent
        return "." if str(parent) == "." else parent.as_posix()
    return p.as_posix()


def next_actions(status: str, required_inputs: list[str], backend: str) -> list[str]:
    if status == "ready-to-write":
        return [
            "Review proposed_config.",
            "Run this script with --write --confirm-write to create or merge .embeddedskills/config.json.",
            "Run tools/build_plan.py again after config is written.",
        ]
    if required_inputs:
        return [f"Provide explicit value for {item} before writing config." for item in required_inputs]
    return [f"Resolve backend selection before config generation: {backend or 'none'}"]


def merge_config(existing: dict[str, Any], proposed: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in proposed.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = dict(merged[key])
            nested.update(value)
            merged[key] = nested
        else:
            merged[key] = value
    return merged


def write_config(proposal: dict[str, Any], *, confirm_write: bool) -> dict[str, Any]:
    if proposal.get("status") != "ready-to-write":
        raise ValueError(f"Cannot write config while proposal status is {proposal.get('status', 'unknown')}.")
    if proposal["required_inputs"]:
        raise ValueError("Cannot write config while required_inputs is non-empty.")
    if not confirm_write:
        raise ValueError("Writing requires --confirm-write.")
    path = Path(proposal["config_path"])
    root = Path(proposal["root"]).resolve()
    existing: dict[str, Any] = {}
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
    merged = merge_config(existing, proposal["proposed_config"])
    safe_io.safe_write_text(
        path,
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
        allowed_roots=[root],
        backup_existing=True,
    )
    backup = path.with_suffix(path.suffix + ".bak")
    return {
        "status": "written",
        "path": str(path),
        "backup_path": str(backup) if backup.exists() else "",
        "config": merged,
    }


def render_markdown(proposal: dict[str, Any]) -> str:
    selected = proposal.get("selected_backend") or {}
    lines = [
        "# EmbeddedSkills Config Proposal",
        "",
        f"- Root: `{proposal['root']}`",
        f"- Status: `{proposal['status']}`",
        f"- Config path: `{proposal['config_path']}`",
        f"- Selected backend: `{selected.get('backend', 'none')}`",
        "",
        "## Required Inputs",
        "",
    ]
    if proposal["required_inputs"]:
        for item in proposal["required_inputs"]:
            lines.append(f"- `{item}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Proposed Config", "", "```json"])
    lines.append(json.dumps(proposal["proposed_config"], ensure_ascii=False, indent=2))
    lines.extend(["```", "", "## Next Actions", ""])
    for item in proposal["next_actions"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Propose .embeddedskills/config.json")
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--target", default="", help="Keil target name")
    parser.add_argument("--preset", default="", help="CMake/GCC preset name")
    parser.add_argument("--config-name", default="", help="EIDE config name")
    parser.add_argument("--write", action="store_true", help="Write merged config")
    parser.add_argument("--confirm-write", action="store_true", help="Required with --write")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    proposal = propose_config(Path(args.root), target=args.target, preset=args.preset, config_name=args.config_name)
    if args.write:
        try:
            proposal["write_result"] = write_config(proposal, confirm_write=args.confirm_write)
        except (ValueError, json.JSONDecodeError) as exc:
            print(json.dumps({"status": "error", "error": str(exc), "proposal": proposal}, ensure_ascii=False, indent=2))
            sys.exit(2)

    content = json.dumps(proposal, ensure_ascii=False, indent=2) if args.as_json and not args.markdown else render_markdown(proposal)
    if args.out:
        safe_io.safe_write_text(Path(args.out), content, allowed_roots=runtime_context.allowed_write_roots())
    else:
        print(content)


if __name__ == "__main__":
    main()
