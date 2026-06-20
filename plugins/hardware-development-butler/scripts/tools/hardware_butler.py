"""Unified CLI facade for the hardware development butler.

The facade keeps early project operations discoverable while preserving safety:
it delegates to read-only tooling by default and does not run build, flash,
debug, or bus actions.
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

import bench_runbook  # noqa: E402
import build_log_classifier  # noqa: E402
import build_plan  # noqa: E402
import chip_dossier  # noqa: E402
import command_runner  # noqa: E402
import config_proposal  # noqa: E402
import cube_detect  # noqa: E402
import cubemx_config_advisor  # noqa: E402
import firmware_code_patcher  # noqa: E402
import firmware_intent_planner  # noqa: E402
import hardware_action_audit  # noqa: E402
import hardware_action_executor  # noqa: E402
import hardware_action_plan  # noqa: E402
import hardware_butler_inspect  # noqa: E402
import manual_summarizer  # noqa: E402
import product_doctor  # noqa: E402
import runtime_context  # noqa: E402
import safe_io  # noqa: E402
from logger import get_logger  # noqa: E402

# Setup logging
logger = get_logger(__name__)


REPO_ROOT = runtime_context.PACKAGE_ROOT


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def output(data: dict[str, Any], *, as_json: bool, markdown: str = "", out: str = "") -> None:
    content = json.dumps(data, ensure_ascii=False, indent=2) if as_json or not markdown else markdown
    if out:
        safe_io.safe_write_text(Path(out), content, allowed_roots=runtime_context.allowed_write_roots())
    else:
        print(content)


def write_markdown(path: Path, content: str) -> str:
    return str(safe_io.safe_write_text(path, content, allowed_roots=runtime_context.allowed_write_roots()))


def onboard_project(root: Path, *, out_dir: Path, target: str = "", preset: str = "", config_name: str = "") -> dict[str, Any]:
    root = root.resolve()
    out_dir = out_dir.resolve()

    inspection = hardware_butler_inspect.inspect_project(root, out_dir)
    detection = cube_detect.detect(root)
    plan = build_plan.generate_plan(root)
    discovery = command_runner.run_plan(root, phase="build-discovery")
    config = config_proposal.propose_config(root, target=target, preset=preset, config_name=config_name)
    primary_part = primary_mcu_part(inspection)
    chip = None
    if primary_part:
        chip = chip_dossier.create_dossier(
            primary_part,
            runtime_context.workspace_root() / "docs" / "chip" / chip_dossier.normalize_part(primary_part),
        )
    action_plan = hardware_action_plan.plan_action(
        root,
        action="flash",
        target=primary_part,
    )

    written = {
        "inspection_dir": str(out_dir),
        "build_plan": write_markdown(out_dir / "build-plan.md", build_plan.render_markdown(plan)),
        "discovery_run": write_markdown(out_dir / "discovery-run.md", command_runner.render_markdown(discovery)),
        "config_proposal": write_markdown(out_dir / "config-proposal.md", config_proposal.render_markdown(config)),
        "flash_action_plan": write_markdown(out_dir / "flash-action-plan.md", hardware_action_plan.render_markdown(action_plan)),
    }
    if chip:
        written["chip_dossier"] = chip["written"]["dossier_json"]
    manifest = {
        "schema_version": 1,
        "root": str(root),
        "out_dir": str(out_dir),
        "detection": {
            "selected_backend": detection.get("selected_backend"),
            "backend_candidates": detection.get("backend_candidates", []),
            "cubemx_project_count": len(detection.get("cubemx_projects", [])),
        },
        "build_plan": {
            "status": plan["status"],
            "command_count": len(plan.get("commands", [])),
        },
        "discovery": {
            "summary": discovery["summary"],
            "phase_filter": discovery["phase_filter"],
            "allow_writes": discovery["allow_writes"],
            "allow_confirmation": discovery["allow_confirmation"],
        },
        "config": {
            "status": config["status"],
            "required_inputs": config.get("required_inputs", []),
            "config_path": config.get("config_path", ""),
        },
        "chip": {
            "part": primary_part,
            "dossier": chip["out_dir"] if chip else "",
        },
        "hardware_actions": {
            "flash_plan_status": action_plan["status"],
            "missing_inputs": action_plan["missing_inputs"],
        },
    }
    written["manifest"] = safe_io.safe_write_text(
        out_dir / "onboarding-manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        allowed_roots=runtime_context.allowed_write_roots(),
    )

    return {
        "schema_version": 1,
        "status": onboard_status(detection, discovery, config),
        "root": str(root),
        "out_dir": str(out_dir),
        "inspection": inspection,
        "detection": detection,
        "build_plan": {
            "status": plan["status"],
            "selected_backend": plan.get("selected_backend"),
            "command_count": len(plan.get("commands", [])),
        },
        "discovery": {
            "summary": discovery["summary"],
            "safety_policy": discovery["safety_policy"],
        },
        "config": {
            "status": config["status"],
            "required_inputs": config.get("required_inputs", []),
            "config_path": config.get("config_path", ""),
        },
        "chip": {
            "part": primary_part,
            "dossier": chip["out_dir"] if chip else "",
        },
        "hardware_actions": {
            "flash_plan_status": action_plan["status"],
            "missing_inputs": action_plan["missing_inputs"],
        },
        "written": written,
        "next_actions": onboard_next_actions(config),
    }


def primary_mcu_part(inspection: dict[str, Any]) -> str:
    board_profile = inspection.get("board_profile")
    if not isinstance(board_profile, dict):
        return ""
    mcu = board_profile.get("mcu")
    if not isinstance(mcu, dict):
        return ""
    return str(mcu.get("name") or "")


def onboard_status(detection: dict[str, Any], discovery: dict[str, Any], config: dict[str, Any]) -> str:
    if detection.get("selected_backend") is None:
        return "needs-build-backend"
    if discovery["summary"].get("error", 0) or discovery["summary"].get("timeout", 0):
        return "discovery-has-errors"
    if config.get("required_inputs"):
        return "needs-input"
    return "ready-for-config-review"


def onboard_next_actions(config: dict[str, Any]) -> list[str]:
    if config.get("required_inputs"):
        return [
            f"Provide required inputs: {', '.join(config['required_inputs'])}.",
            "Run propose-config again with the missing target, preset, or config name.",
        ]
    return [
        "Review the generated dossier, build plan, discovery run, and config proposal.",
        "Write .embeddedskills/config.json only with propose-config --write --confirm-write.",
        "Run real build/flash/debug actions only after explicit confirmation.",
    ]


def main() -> None:
    configure_stdio()
    parser = argparse.ArgumentParser(description="Hardware development butler CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_p = sub.add_parser("inspect", help="Generate project dossier, board profile, and firmware profile")
    inspect_p.add_argument("--root", default=".")
    inspect_p.add_argument("--out-dir", default="")
    inspect_p.add_argument("--json", action="store_true", dest="as_json")

    detect_p = sub.add_parser("detect", help="Detect CubeMX metadata and backend candidates")
    detect_p.add_argument("--root", default=".")
    detect_p.add_argument("--json", action="store_true", dest="as_json")
    detect_p.add_argument("--out", default="")

    plan_p = sub.add_parser("plan-build", help="Generate safe build plan without executing it")
    plan_p.add_argument("--root", default=".")
    plan_p.add_argument("--json", action="store_true", dest="as_json")
    plan_p.add_argument("--out", default="")

    config_p = sub.add_parser("propose-config", help="Generate or write .embeddedskills/config.json proposal")
    config_p.add_argument("--root", default=".")
    config_p.add_argument("--target", default="")
    config_p.add_argument("--preset", default="")
    config_p.add_argument("--config-name", default="")
    config_p.add_argument("--write", action="store_true")
    config_p.add_argument("--confirm-write", action="store_true")
    config_p.add_argument("--json", action="store_true", dest="as_json")
    config_p.add_argument("--out", default="")

    run_p = sub.add_parser("run-plan", help="Run safe non-hardware commands from a generated plan")
    run_p.add_argument("--root", default=".")
    run_p.add_argument("--phase", default="")
    run_p.add_argument("--allow-writes", action="store_true")
    run_p.add_argument("--allow-confirmation", action="store_true")
    run_p.add_argument("--timeout", type=int, default=60)
    run_p.add_argument("--json", action="store_true", dest="as_json")
    run_p.add_argument("--out", default="")

    onboard_p = sub.add_parser("onboard", help="Run safe first-pass onboarding and write project reports")
    onboard_p.add_argument("--root", default=".")
    onboard_p.add_argument("--out-dir", default="")
    onboard_p.add_argument("--target", default="")
    onboard_p.add_argument("--preset", default="")
    onboard_p.add_argument("--config-name", default="")
    onboard_p.add_argument("--json", action="store_true", dest="as_json")
    onboard_p.add_argument("--out", default="")

    cap_p = sub.add_parser("capabilities", help="Show product capability matrix")
    cap_p.add_argument("--json", action="store_true", dest="as_json")
    cap_p.add_argument("--out", default="")

    doctor_p = sub.add_parser("doctor", help="Check local environment and product readiness")
    doctor_p.add_argument("--root", default=".")
    doctor_p.add_argument("--json", action="store_true", dest="as_json")
    doctor_p.add_argument("--out", default="")

    status_p = sub.add_parser("status", help="Show project onboarding and readiness status")
    status_p.add_argument("--root", default=".")
    status_p.add_argument("--json", action="store_true", dest="as_json")
    status_p.add_argument("--out", default="")

    log_p = sub.add_parser("classify-log", help="Classify build log")
    log_p.add_argument("log")
    log_p.add_argument("--json", action="store_true", dest="as_json")
    log_p.add_argument("--out", default="")

    chip_p = sub.add_parser("chip-dossier", help="Create chip document dossier and summary skeleton")
    chip_p.add_argument("--part", required=True)
    chip_p.add_argument("--board", default="")
    chip_p.add_argument("--source", action="append", default=[])
    chip_p.add_argument("--search", action="store_true")
    chip_p.add_argument("--search-source", action="append", default=[], help="Omit with --search to use built-in vendor hints")
    chip_p.add_argument("--download", action="store_true")
    chip_p.add_argument("--no-extract", action="store_true")
    chip_p.add_argument("--out-dir", default="")
    chip_p.add_argument("--json", action="store_true", dest="as_json")
    chip_p.add_argument("--out", default="")

    pin_p = sub.add_parser("advise-pin", help="Advise CubeMX pin/peripheral configuration")
    pin_p.add_argument("--root", default=".")
    pin_p.add_argument("--pin", required=True)
    pin_p.add_argument("--function", required=True)
    pin_p.add_argument("--pin-evidence", default="")
    pin_p.add_argument("--json", action="store_true", dest="as_json")
    pin_p.add_argument("--out", default="")

    patch_ioc_p = sub.add_parser("patch-ioc", help="Preview or write safe STM32CubeMX .ioc pin/peripheral changes")
    patch_ioc_p.add_argument("--root", default=".")
    patch_ioc_p.add_argument("--function", required=True)
    patch_ioc_p.add_argument("--pin", default="")
    patch_ioc_p.add_argument("--label", default="")
    patch_ioc_p.add_argument("--instance", default="")
    patch_ioc_p.add_argument("--scl", default="")
    patch_ioc_p.add_argument("--sda", default="")
    patch_ioc_p.add_argument("--timing", default="")
    patch_ioc_p.add_argument("--write", action="store_true")
    patch_ioc_p.add_argument("--confirm-write", action="store_true")
    patch_ioc_p.add_argument("--json", action="store_true", dest="as_json")
    patch_ioc_p.add_argument("--out", default="")

    action_p = sub.add_parser("plan-action", help="Create confirmation-gated hardware action plan")
    action_p.add_argument("--root", default=".")
    action_p.add_argument("--action", required=True)
    action_p.add_argument("--target", default="")
    action_p.add_argument("--probe", default="")
    action_p.add_argument("--voltage", default="")
    action_p.add_argument("--current-limit", default="")
    action_p.add_argument("--erase-scope", default="")
    action_p.add_argument("--recovery", default="")
    action_p.add_argument("--external-loads", default="")
    action_p.add_argument("--artifact", default="")
    action_p.add_argument("--backend", default="")
    action_p.add_argument("--json", action="store_true", dest="as_json")
    action_p.add_argument("--out", default="")

    exec_p = sub.add_parser("execute-action", help="Execute a confirmation-token action plan through safe/fake backends")
    exec_p.add_argument("--plan", required=True)
    exec_p.add_argument("--confirm-token", required=True)
    exec_p.add_argument("--backend", default="")
    exec_p.add_argument("--json", action="store_true", dest="as_json")
    exec_p.add_argument("--out", default="")

    audit_p = sub.add_parser("safety-audit", help="Summarize hardware action safety/audit log without exposing tokens")
    audit_p.add_argument("--root", default=".")
    audit_p.add_argument("--json", action="store_true", dest="as_json")
    audit_p.add_argument("--out", default="")

    runbook_p = sub.add_parser("bench-runbook", help="Generate a no-hardware bench runbook for build/flash/debug/observe")
    runbook_p.add_argument("--root", default=".")
    runbook_p.add_argument("--action", required=True)
    runbook_p.add_argument("--target", default="")
    runbook_p.add_argument("--probe", default="")
    runbook_p.add_argument("--voltage", default="")
    runbook_p.add_argument("--current-limit", default="")
    runbook_p.add_argument("--erase-scope", default="")
    runbook_p.add_argument("--recovery", default="")
    runbook_p.add_argument("--external-loads", default="")
    runbook_p.add_argument("--artifact", default="")
    runbook_p.add_argument("--backend", default="")
    runbook_p.add_argument("--json", action="store_true", dest="as_json")
    runbook_p.add_argument("--out", default="")

    firmware_p = sub.add_parser("firmware-plan", help="Plan CubeMX/HAL/FreeRTOS implementation without editing code")
    firmware_p.add_argument("--root", default=".")
    firmware_p.add_argument("--feature", required=True)
    firmware_p.add_argument("--pin", default="")
    firmware_p.add_argument("--function", default="")
    firmware_p.add_argument("--no-rtos", action="store_true")
    firmware_p.add_argument("--json", action="store_true", dest="as_json")
    firmware_p.add_argument("--out", default="")

    patch_p = sub.add_parser("firmware-patch", help="Generate or write safe app-layer firmware patch files")
    patch_p.add_argument("--root", default=".")
    patch_p.add_argument("--feature", required=True)
    patch_p.add_argument("--pin", default="")
    patch_p.add_argument("--function", default="")
    patch_p.add_argument("--no-rtos", action="store_true")
    patch_p.add_argument("--write", action="store_true")
    patch_p.add_argument("--confirm-write", action="store_true")
    patch_p.add_argument("--json", action="store_true", dest="as_json")
    patch_p.add_argument("--out", default="")

    integrate_p = sub.add_parser("firmware-integrate", help="Preview or write CubeMX USER CODE integration hooks for an app module")
    integrate_p.add_argument("--root", default=".")
    integrate_p.add_argument("--feature", required=True)
    integrate_p.add_argument("--pin", default="")
    integrate_p.add_argument("--function", default="")
    integrate_p.add_argument("--no-rtos", action="store_true")
    integrate_p.add_argument("--write", action="store_true")
    integrate_p.add_argument("--confirm-write", action="store_true")
    integrate_p.add_argument("--json", action="store_true", dest="as_json")
    integrate_p.add_argument("--out", default="")

    summary_p = sub.add_parser("summarize-manual", help="Summarize extracted chip manual text with evidence lines")
    summary_p.add_argument("--part", required=True)
    summary_p.add_argument("--document", action="append", required=True)
    summary_p.add_argument("--json", action="store_true", dest="as_json")
    summary_p.add_argument("--out", default="")

    args = parser.parse_args()

    if args.command == "inspect":
        root = Path(args.root)
        out_dir = Path(args.out_dir) if args.out_dir else root / "docs"
        safe_io.validate_write_path(out_dir, allowed_roots=runtime_context.allowed_write_roots())
        data = hardware_butler_inspect.inspect_project(root, out_dir)
        output(data, as_json=args.as_json)
    elif args.command == "detect":
        data = cube_detect.detect(Path(args.root))
        output(data, as_json=args.as_json, markdown=cube_detect.render_markdown(data), out=args.out)
    elif args.command == "plan-build":
        data = build_plan.generate_plan(Path(args.root))
        output(data, as_json=args.as_json, markdown=build_plan.render_markdown(data), out=args.out)
    elif args.command == "propose-config":
        data = config_proposal.propose_config(
            Path(args.root),
            target=args.target,
            preset=args.preset,
            config_name=args.config_name,
        )
        if args.write:
            try:
                data["write_result"] = config_proposal.write_config(data, confirm_write=args.confirm_write)
            except (ValueError, json.JSONDecodeError) as exc:
                output({"status": "error", "error": str(exc), "proposal": data}, as_json=True)
                sys.exit(2)
        output(data, as_json=args.as_json, markdown=config_proposal.render_markdown(data), out=args.out)
    elif args.command == "run-plan":
        data = command_runner.run_plan(
            Path(args.root),
            phase=args.phase,
            allow_writes=args.allow_writes,
            allow_confirmation=args.allow_confirmation,
            timeout_s=args.timeout,
        )
        output(data, as_json=args.as_json, markdown=command_runner.render_markdown(data), out=args.out)
    elif args.command == "onboard":
        root = Path(args.root)
        out_dir = Path(args.out_dir) if args.out_dir else runtime_context.default_inspection_dir(root)
        safe_io.validate_write_path(out_dir, allowed_roots=runtime_context.allowed_write_roots())
        data = onboard_project(
            root,
            out_dir=out_dir,
            target=args.target,
            preset=args.preset,
            config_name=args.config_name,
        )
        output(data, as_json=args.as_json, out=args.out)
    elif args.command == "capabilities":
        data = product_doctor.capabilities()
        output(data, as_json=args.as_json, markdown=product_doctor.render_capabilities_markdown(data), out=args.out)
    elif args.command == "doctor":
        data = product_doctor.doctor(Path(args.root))
        output(data, as_json=args.as_json, markdown=product_doctor.render_doctor_markdown(data), out=args.out)
    elif args.command == "status":
        data = product_doctor.project_status(Path(args.root))
        output(data, as_json=args.as_json, markdown=product_doctor.render_status_markdown(data), out=args.out)
    elif args.command == "classify-log":
        try:
            text = build_log_classifier.read_log(Path(args.log))
        except (OSError, ValueError) as exc:
            output({"schema_version": 1, "status": "error", "error": str(exc)}, as_json=True)
            sys.exit(2)
        data = build_log_classifier.classify_text(text)
        output(data, as_json=args.as_json, markdown=build_log_classifier.render_markdown(data), out=args.out)
    elif args.command == "chip-dossier":
        part = chip_dossier.normalize_part(args.part)
        out_dir = Path(args.out_dir) if args.out_dir else runtime_context.workspace_root() / "docs" / "chip" / part
        if args.search:
            data = chip_dossier.search_and_download_documents(
                part,
                out_dir,
                board=args.board,
                search_sources=args.search_source or args.source,
            )
        elif args.download:
            data = chip_dossier.download_documents(
                part,
                out_dir,
                board=args.board,
                sources=args.source,
                extract_text=not args.no_extract,
            )
        else:
            data = chip_dossier.create_dossier(part, out_dir, board=args.board, sources=args.source)
        output(data, as_json=args.as_json, markdown=chip_dossier.render_source_map(data), out=args.out)
    elif args.command == "advise-pin":
        data = cubemx_config_advisor.advise(Path(args.root), pin=args.pin, function=args.function, pin_evidence=args.pin_evidence)
        output(data, as_json=args.as_json, markdown=cubemx_config_advisor.render_markdown(data), out=args.out)
    elif args.command == "patch-ioc":
        try:
            patch = cubemx_config_advisor.propose_ioc_patch(
                Path(args.root),
                function=args.function,
                pin=args.pin,
                label=args.label,
                instance=args.instance,
                scl_pin=args.scl,
                sda_pin=args.sda,
                timing=args.timing,
            )
            data = cubemx_config_advisor.write_ioc_patch(patch, confirm_write=args.confirm_write) if args.write else patch
        except (OSError, ValueError) as exc:
            output({"schema_version": 1, "status": "error", "error": str(exc)}, as_json=True)
            sys.exit(2)
        output(data, as_json=args.as_json, markdown=cubemx_config_advisor.render_ioc_patch_markdown(data), out=args.out)
    elif args.command == "plan-action":
        data = hardware_action_plan.plan_action(
            Path(args.root),
            action=args.action,
            target=args.target,
            probe=args.probe,
            voltage=args.voltage,
            current_limit=args.current_limit,
            erase_scope=args.erase_scope,
            recovery=args.recovery,
            external_loads=args.external_loads,
            artifact=args.artifact,
            backend=args.backend,
        )
        output(data, as_json=args.as_json, markdown=hardware_action_plan.render_markdown(data), out=args.out)
    elif args.command == "execute-action":
        try:
            plan = hardware_action_executor.load_plan(Path(args.plan))
            data = hardware_action_executor.execute_plan(plan, token=args.confirm_token, backend=args.backend)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            output({"schema_version": 1, "status": "error", "error": str(exc)}, as_json=True)
            sys.exit(2)
        output(data, as_json=args.as_json, markdown=hardware_action_executor.render_markdown(data), out=args.out)
    elif args.command == "safety-audit":
        data = hardware_action_audit.audit_report(Path(args.root))
        output(data, as_json=args.as_json, markdown=hardware_action_audit.render_markdown(data), out=args.out)
    elif args.command == "bench-runbook":
        data = bench_runbook.generate_runbook(
            Path(args.root),
            action=args.action,
            target=args.target,
            probe=args.probe,
            voltage=args.voltage,
            current_limit=args.current_limit,
            erase_scope=args.erase_scope,
            recovery=args.recovery,
            external_loads=args.external_loads,
            artifact=args.artifact,
            backend=args.backend,
        )
        output(data, as_json=args.as_json, markdown=bench_runbook.render_markdown(data), out=args.out)
    elif args.command == "firmware-plan":
        data = firmware_intent_planner.plan_implementation(
            Path(args.root),
            feature=args.feature,
            pin=args.pin,
            function=args.function,
            rtos=not args.no_rtos,
        )
        output(data, as_json=args.as_json, markdown=firmware_intent_planner.render_markdown(data), out=args.out)
    elif args.command == "firmware-patch":
        try:
            preview = firmware_code_patcher.preview_patch(
                Path(args.root),
                feature=args.feature,
                pin=args.pin,
                function=args.function,
                rtos=not args.no_rtos,
            )
            data = firmware_code_patcher.write_patch(preview, confirm_write=args.confirm_write) if args.write else preview
        except (OSError, ValueError) as exc:
            output({"schema_version": 1, "status": "error", "error": str(exc)}, as_json=True)
            sys.exit(2)
        output(data, as_json=args.as_json, markdown=firmware_code_patcher.render_markdown(data), out=args.out)
    elif args.command == "firmware-integrate":
        try:
            preview = firmware_code_patcher.preview_integration_patch(
                Path(args.root),
                feature=args.feature,
                pin=args.pin,
                function=args.function,
                rtos=not args.no_rtos,
            )
            data = firmware_code_patcher.write_integration_patch(preview, confirm_write=args.confirm_write) if args.write else preview
        except (OSError, ValueError) as exc:
            output({"schema_version": 1, "status": "error", "error": str(exc)}, as_json=True)
            sys.exit(2)
        output(data, as_json=args.as_json, markdown=firmware_code_patcher.render_integration_markdown(data), out=args.out)
    elif args.command == "summarize-manual":
        data = manual_summarizer.summarize_documents(args.part, [Path(item) for item in args.document])
        output(data, as_json=args.as_json, markdown=manual_summarizer.render_markdown(data), out=args.out)


if __name__ == "__main__":
    main()
