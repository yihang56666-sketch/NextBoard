"""Project workflow state and next-step recommendations.

This module ties the existing safe project checks into a small state machine.
It deliberately recommends hardware-facing actions only as plans or dry runs;
real flash/debug/observe stays behind the existing confirmation gates.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import product_doctor
import project_brain
import project_scanner
import runtime_context
import safe_io

STATE_DIR = ".hardware-butler"
STATE_FILE = "project-state.json"
REPORT_DEFINITIONS = [
    ("manifest", "Onboarding manifest", "Machine-readable run summary", "onboarding-manifest.json"),
    ("project_dossier", "Project dossier", "Project overview", "project-dossier.md"),
    ("board_profile", "Board profile", "Board evidence", "board-profile.md"),
    ("firmware_profile", "Firmware profile", "Firmware structure", "firmware-profile.md"),
    ("build_plan", "Build plan", "Build steps", "build-plan.md"),
    ("discovery_run", "Discovery run", "Safe command evidence", "discovery-run.md"),
    ("config_proposal", "Config proposal", "Embeddedskills config", "config-proposal.md"),
    ("flash_action_plan", "Flash action plan", "Planned-gated hardware action", "flash-action-plan.md"),
]
ARTIFACT_LABELS = {
    "schematic": ("原理图", "板级连接、电源、接口和调试链路证据"),
    "pcb": ("PCB", "板级布局和布线证据"),
    "bom": ("BOM", "器件选型、替代料和采购风险证据"),
    "datasheet": ("数据手册", "芯片和器件电气参数证据"),
    "manual": ("手册", "开发板、芯片参考或用户操作资料"),
    "cubemx_ioc": ("CubeMX", "MCU、时钟、引脚和外设配置入口"),
    "keil_project": ("Keil 工程", "MDK 构建入口"),
    "cmake_project": ("CMake 工程", "GCC/CMake 构建入口"),
    "eide_project": ("EIDE 工程", "EIDE 构建入口"),
    "makefile": ("Makefile", "Make 构建入口"),
    "linker_script": ("链接脚本", "内存布局和链接配置"),
    "startup_file": ("启动文件", "中断向量和启动流程"),
    "build_log": ("构建日志", "编译问题和工具链证据"),
    "debug_log": ("调试日志", "串口、RTT、SWO 或调试输出证据"),
}

OnboardRunner = Callable[[Path, Path], dict[str, Any]]


def collect_project_state(root: Path, *, reports_dir: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    status = product_doctor.project_status(root)
    if reports_dir is not None:
        status = apply_reports_dir(status, root, reports_dir.resolve())
    doctor = product_doctor.doctor(root)
    next_step = recommend_next_step(status, doctor)
    phases = workflow_phases(status)
    return {
        "schema_version": 1,
        "product": "hardware-development-butler",
        "root": str(root),
        "status": workflow_status(status, doctor),
        "backend": status.get("backend") or {},
        "cubemx_project_count": status.get("cubemx_project_count", 0),
        "config": status.get("config", {}),
        "reports_dir": status.get("reports_dir", ""),
        "discovery": status.get("discovery", {}),
        "bench_readiness": status.get("bench_readiness", {}),
        "doctor_summary": doctor.get("summary", {}),
        "phases": phases,
        "next_step": next_step,
        "next_actions": status.get("next_actions", []),
        "safety": {
            "safe_by_default": True,
            "real_hardware_actions": "planned-gated",
            "touches_hardware": False,
        },
    }


def apply_reports_dir(status: dict[str, Any], root: Path, reports_dir: Path) -> dict[str, Any]:
    reports = {
        "manifest": product_doctor.file_state(reports_dir / "onboarding-manifest.json"),
        "project_dossier": product_doctor.file_state(reports_dir / "project-dossier.md"),
        "board_profile": product_doctor.file_state(reports_dir / "board-profile.md"),
        "firmware_profile": product_doctor.file_state(reports_dir / "firmware-profile.md"),
        "build_plan": product_doctor.file_state(reports_dir / "build-plan.md"),
        "discovery_run": product_doctor.file_state(reports_dir / "discovery-run.md"),
        "config_proposal": product_doctor.file_state(reports_dir / "config-proposal.md"),
    }
    manifest = product_doctor.read_manifest(reports_dir / "onboarding-manifest.json")
    discovery = product_doctor.discovery_status(root, manifest)
    backend = status.get("backend") or {}
    config = status.get("config") or {}
    discovery_ready = bool(backend.get("backend") in {"keil", "cmake-gcc", "eide"})
    updated = dict(status)
    updated["reports_dir"] = str(reports_dir)
    updated["reports"] = reports
    updated["manifest"] = manifest
    updated["discovery"] = discovery
    updated["status"] = product_doctor.project_state(backend, config, reports, discovery)
    updated["next_actions"] = product_doctor.status_next_actions(backend, config, reports, discovery_ready, discovery)
    return updated


def recommend_next_step(status: dict[str, Any], doctor: dict[str, Any]) -> dict[str, Any]:
    root = status.get("root", ".")
    backend = status.get("backend") or {}
    config = status.get("config") or {}
    reports = status.get("reports") or {}
    discovery = status.get("discovery") or {}
    bench = status.get("bench_readiness") or {}
    doctor_summary = doctor.get("summary") or {}

    if doctor_summary.get("error", 0):
        return step(
            "fix-environment",
            "Fix environment checks",
            "Run doctor and resolve required environment checks before project automation.",
            ["python", "tools/hardware_butler.py", "doctor", "--root", root, "--json"],
        )
    if not backend.get("backend"):
        return step(
            "run-onboard",
            "Analyze project",
            "No supported build backend has been selected yet.",
            ["python", "tools/hardware_butler.py", "onboard", "--root", root, "--json"],
            writes_reports=True,
        )
    if not reports.get("manifest", {}).get("exists") or discovery.get("status") != "ok":
        return step(
            "run-onboard",
            "Run safe onboarding",
            discovery.get("message", "Project reports or safe discovery evidence are missing."),
            ["python", "tools/hardware_butler.py", "onboard", "--root", root, "--json"],
            writes_reports=True,
        )
    if not config.get("exists"):
        return step(
            "review-config",
            "Generate config proposal",
            "The project has no .embeddedskills/config.json yet.",
            ["python", "tools/hardware_butler.py", "propose-config", "--root", root, "--json"],
            writes_reports=False,
        )
    if not config.get("valid_json"):
        return step(
            "fix-config",
            "Fix config JSON",
            "The existing .embeddedskills/config.json cannot be parsed.",
            ["python", "tools/hardware_butler.py", "status", "--root", root, "--json"],
        )
    if config.get("auto_hardware_preferences"):
        return step(
            "review-hardware-preferences",
            "Review hardware backend preferences",
            "Hardware action preferences should be explicit before bench work.",
            ["python", "tools/hardware_butler.py", "doctor", "--root", root, "--json"],
        )
    if bench.get("status") in {"needs-bench-input", "ready-with-bench-warnings"}:
        return step(
            "prepare-bench-runbook",
            "Prepare bench runbook",
            "Bench readiness still needs inputs or review; generate a no-hardware runbook.",
            ["python", "tools/hardware_butler.py", "bench-runbook", "--root", root, "--action", "build-flash", "--json"],
        )
    return step(
        "plan-confirmed-action",
        "Plan confirmed build path",
        "The project is ready for a confirmation-gated build or simulated hardware path.",
        ["python", "tools/hardware_butler.py", "plan-action", "--root", root, "--action", "build", "--json"],
    )


def step(
    step_id: str,
    title: str,
    reason: str,
    argv: list[str],
    *,
    writes_reports: bool = False,
) -> dict[str, Any]:
    return {
        "id": step_id,
        "title": title,
        "reason": reason,
        "argv": argv,
        "command": " ".join(argv),
        "safe_by_default": True,
        "touches_hardware": False,
        "writes_reports": writes_reports,
    }


def workflow_status(status: dict[str, Any], doctor: dict[str, Any]) -> str:
    if (doctor.get("summary") or {}).get("error", 0):
        return "needs-environment-fix"
    project = str(status.get("status", "unknown"))
    if project in {"needs-backend", "needs-config", "config-invalid", "needs-safe-discovery"}:
        return project.replace("needs-safe-discovery", "needs-onboarding")
    return project


def workflow_phases(status: dict[str, Any]) -> list[dict[str, Any]]:
    backend = status.get("backend") or {}
    config = status.get("config") or {}
    reports = status.get("reports") or {}
    discovery = status.get("discovery") or {}
    bench = status.get("bench_readiness") or {}
    return [
        phase("project-detection", "Project detection", bool(backend.get("backend")), backend.get("backend", "No backend detected")),
        phase("safe-onboarding", "Safe onboarding", bool(reports.get("manifest", {}).get("exists")), discovery.get("message", "No manifest found")),
        phase("configuration", "Configuration", bool(config.get("exists") and config.get("valid_json")), config.get("path", "No config file")),
        phase("safe-discovery", "Safe discovery", discovery.get("status") == "ok", discovery.get("message", "Not run")),
        phase("bench-readiness", "Bench readiness", bench.get("status") == "ready-for-bench-preflight", bench.get("status", "unknown")),
    ]


def workflow_reports(root: Path, reports_dir: Path) -> list[dict[str, Any]]:
    del root
    reports = []
    for report_id, title, role, filename in REPORT_DEFINITIONS:
        state = product_doctor.file_state(reports_dir / filename)
        reports.append(
            {
                "id": report_id,
                "title": title,
                "role": role,
                "path": state["path"],
                "exists": state["exists"],
                "size_bytes": state["size_bytes"],
            }
        )
    return reports


def workbench_artifacts(root: Path) -> dict[str, Any]:
    scan = project_scanner.scan(root)
    rows = []
    for label, items in scan.get("artifacts", {}).items():
        display, role = ARTIFACT_LABELS.get(label, (label, "项目资料"))
        for item in items:
            path = str(item.get("path", ""))
            rows.append(
                {
                    "id": label,
                    "type": display,
                    "role": role,
                    "path": path,
                    "size_bytes": int(item.get("size_bytes", 0) or 0),
                }
            )
    order = {key: index for index, key in enumerate(ARTIFACT_LABELS)}
    rows.sort(key=lambda row: (order.get(str(row["id"]), 999), str(row["path"]).lower()))
    return {
        "summary": scan.get("summary", {}),
        "recommended_next_steps": scan.get("recommended_next_steps", []),
        "rows": rows,
    }


def workbench_actions(state: dict[str, Any]) -> list[dict[str, Any]]:
    root = str(state.get("root", "."))
    primary = state.get("next_step") if isinstance(state.get("next_step"), dict) else {}
    actions = [
        action(
            "refresh",
            "Refresh project",
            "Reload project evidence and update the workbench.",
            ["python", "tools/hardware_butler.py", "workbench", "--root", root, "--json"],
        ),
        action(
            "auto",
            "Auto analyze",
            "Run safe onboarding when needed and update project state.",
            ["python", "tools/hardware_butler.py", "auto", "--root", root, "--json"],
            writes_reports=True,
        ),
        action(
            "brain",
            "Project brain",
            "Build evidence health, missing evidence, and deterministic hardware risks.",
            ["python", "tools/hardware_butler.py", "brain", "--root", root, "--json"],
            writes_reports=True,
        ),
        action(
            "doctor",
            "Check environment",
            "Check local tools and product readiness.",
            ["python", "tools/hardware_butler.py", "doctor", "--root", root, "--json"],
        ),
        action(
            "detect",
            "Detect project",
            "Detect CubeMX metadata and build backend candidates.",
            ["python", "tools/hardware_butler.py", "detect", "--root", root, "--json"],
        ),
        action(
            "bench-runbook",
            "Prepare bench runbook",
            "Create a no-hardware runbook for the bench path.",
            ["python", "tools/hardware_butler.py", "bench-runbook", "--root", root, "--action", "build-flash", "--json"],
        ),
        action(
            "safety-audit",
            "Review safety audit",
            "Summarize hardware action safety history without exposing tokens.",
            ["python", "tools/hardware_butler.py", "safety-audit", "--root", root, "--json"],
        ),
    ]
    if primary:
        actions.append(
            action(
                "recommended",
                str(primary.get("title", "Recommended action")),
                str(primary.get("reason", "")),
                [str(item) for item in primary.get("argv", [])],
                writes_reports=bool(primary.get("writes_reports")),
            )
        )
    return actions


def action(
    action_id: str,
    title: str,
    reason: str,
    argv: list[str],
    *,
    writes_reports: bool = False,
) -> dict[str, Any]:
    return {
        "id": action_id,
        "title": title,
        "reason": reason,
        "argv": argv,
        "command": " ".join(argv),
        "safe_by_default": True,
        "touches_hardware": False,
        "writes_reports": writes_reports,
    }


def build_workbench(root: Path, *, reports_dir: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    target_reports = reports_dir.resolve() if reports_dir else runtime_context.default_inspection_dir(root)
    state = collect_project_state(root, reports_dir=target_reports)
    artifacts = workbench_artifacts(root)
    brain = project_brain.build_project_brain(root)
    return {
        "schema_version": 1,
        "app": "hardware-butler-workbench",
        "project": {
            "root": str(root),
            "name": root.name,
            "reports_dir": str(target_reports),
        },
        "state": state,
        "primary_action": state["next_step"],
        "actions": workbench_actions(state),
        "artifact_summary": artifacts["summary"],
        "artifacts": artifacts["rows"],
        "artifact_next_steps": artifacts["recommended_next_steps"],
        "brain": brain,
        "reports": workflow_reports(root, target_reports),
        "safety": state["safety"],
    }


def phase(phase_id: str, title: str, complete: bool, detail: str) -> dict[str, Any]:
    return {
        "id": phase_id,
        "title": title,
        "status": "complete" if complete else "needs-action",
        "detail": str(detail),
    }


def project_state_path(root: Path) -> Path:
    return root.resolve() / STATE_DIR / STATE_FILE


def write_project_state(root: Path, state: dict[str, Any]) -> Path:
    path = project_state_path(root)
    safe_io.safe_write_text(
        path,
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        allowed_roots=runtime_context.allowed_write_roots(),
    )
    return path


def run_auto(root: Path, *, out_dir: Path | None = None, onboard_runner: OnboardRunner | None = None) -> dict[str, Any]:
    root = root.resolve()
    target_out = out_dir.resolve() if out_dir else runtime_context.default_inspection_dir(root)
    before = collect_project_state(root, reports_dir=target_out if out_dir is not None else None)
    ran: list[str] = []
    onboarding: dict[str, Any] | None = None
    requested_out_dir_missing = out_dir is not None and not (target_out / "onboarding-manifest.json").exists()
    if (before["next_step"]["id"] == "run-onboard" or requested_out_dir_missing) and onboard_runner is not None:
        onboarding = onboard_runner(root, target_out)
        ran.append("onboard")
    after = collect_project_state(root, reports_dir=target_out)
    state_path = write_project_state(root, after)
    return {
        "schema_version": 1,
        "status": after["status"],
        "root": str(root),
        "state_path": str(state_path),
        "automation": {
            "ran": ran,
            "onboarding": onboarding,
        },
        "state": after,
        "next_step": after["next_step"],
    }
