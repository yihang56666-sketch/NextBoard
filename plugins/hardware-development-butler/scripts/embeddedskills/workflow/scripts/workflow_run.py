"""workflow 薄编排执行层。"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import safety_gate  # noqa: E402
from workflow_runtime import (  # noqa: E402
    get_state_entry,
    hidden_subprocess_kwargs,
    load_effective_project_config,
    load_workspace_state,
    make_result,
    make_timing,
    now_iso,
    output_json,
    parameter_context,
    save_project_config,
    update_state_entry,
    workspace_root,
)

PYTHON_EXE = sys.executable
SENSITIVE_ARG_FLAGS = {"--confirm-token", "--child-confirm-token"}


def _with_backend(result: dict, backend: str) -> dict:
    details = dict(result.get("details") or {})
    details["backend"] = backend
    result["details"] = details
    return result


def _workflow_state_key(action: str) -> str:
    return f"last_workflow_{action.replace('-', '_')}"


def _workflow_state_details(action: str, result: dict) -> dict:
    details = result.get("details") or {}
    if action in ("build", "observe"):
        return {"backend": details.get("backend"), "summary": result.get("summary", "")}
    if action == "build-flash":
        build = details.get("build") or {}
        flash = details.get("flash") or {}
        return {
            "summary": result.get("summary", ""),
            "build_backend": (build.get("details") or {}).get("backend"),
            "flash_backend": (flash.get("details") or {}).get("backend"),
        }
    if action == "build-debug":
        build = details.get("build") or {}
        debug = details.get("debug") or {}
        return {
            "summary": result.get("summary", ""),
            "build_backend": (build.get("details") or {}).get("backend"),
            "debug_backend": (debug.get("details") or {}).get("backend"),
        }
    return {"summary": result.get("summary", "")}


def artifact_guard(workspace: Path, artifact_file: str, safety: dict | None, source: str) -> dict:
    safety = safety or {}
    expected_artifact = str(safety.get("artifact") or "")
    expected_hash = str(safety.get("artifact_hash") or "")
    if not expected_artifact and not expected_hash:
        return {"status": "ok", "artifact": artifact_file, "artifact_hash": "", "source": source}
    if expected_artifact and normalize_artifact_path(expected_artifact) != normalize_artifact_path(artifact_file):
        return {
            "status": "error",
            "action": "artifact-guard",
            "summary": "confirmed artifact does not match state.last_build artifact",
            "details": {
                "artifact_source": source,
                "state_artifact": artifact_file,
                "confirmed_artifact": expected_artifact,
                "expected_hash": expected_hash,
            },
            "error": {"code": "artifact_mismatch", "message": "confirmed artifact does not match state.last_build artifact"},
        }
    actual_hash = file_sha256(workspace, artifact_file)
    if expected_hash and actual_hash != expected_hash:
        return {
            "status": "error",
            "action": "artifact-guard",
            "summary": "confirmed artifact hash does not match the current file",
            "details": {
                "artifact_source": source,
                "artifact": artifact_file,
                "expected_hash": expected_hash,
                "actual_hash": actual_hash,
            },
            "error": {"code": "artifact_hash_mismatch", "message": "confirmed artifact hash does not match the current file"},
        }
    return {"status": "ok", "artifact": artifact_file, "artifact_hash": actual_hash, "source": source}


def normalize_artifact_path(value: str) -> str:
    return value.replace("\\", "/").strip().lstrip("./")


def file_sha256(workspace: Path, artifact: str) -> str:
    path = Path(artifact)
    if not path.is_absolute():
        path = workspace / path
    resolved = path.resolve()
    if not resolved.is_file():
        return ""
    hasher = hashlib.sha256()
    with resolved.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def discover_projects(root: Path) -> dict:
    return {
        "keil": sorted(str(path.resolve()) for path in root.rglob("*.uvprojx")),
        "gcc": sorted(str(path.parent.resolve()) for path in root.rglob("CMakePresets.json")),
        "eide": sorted(str(path.parents[1].resolve()) for path in root.rglob(".eide/eide.yml")),
    }


def _single_or_error(items: list[str], label: str) -> tuple[str | None, dict | None]:
    if len(items) == 1:
        return items[0], None
    if len(items) > 1:
        return None, {"code": "multiple_candidates", "message": f"发现多个{label}，请在配置或命令中显式指定", "candidates": items}
    return None, {"code": "not_found", "message": f"未发现可用的{label}", "candidates": []}


def _is_openocd_ready(full_config: dict) -> bool:
    openocd_cfg = full_config.get("openocd", {})
    return bool(openocd_cfg.get("board") or (openocd_cfg.get("interface") and openocd_cfg.get("target")))


def _is_jlink_ready(full_config: dict) -> bool:
    return bool((full_config.get("jlink") or {}).get("device"))


def _is_probe_rs_ready(full_config: dict) -> bool:
    return bool((full_config.get("probe-rs") or {}).get("chip"))


def _select_backend(explicit: str | None, preferred: str | None, ready_backends: list[str], action: str) -> tuple[str | None, dict | None]:
    backend = explicit or preferred or "auto"
    if backend != "auto":
        return backend, None
    if len(ready_backends) == 1:
        return ready_backends[0], None
    if len(ready_backends) > 1:
        return None, {
            "code": "multiple_backend_candidates",
            "message": f"{action} 存在多个可用后端，请通过 CLI 或 workflow.preferred_* 显式指定",
            "candidates": ready_backends,
        }
    return None, {
        "code": "no_backend_available",
        "message": f"未找到可用的 {action} 后端，请补充 jlink/openocd/probe-rs 配置",
        "candidates": [],
    }


def run_json(cmd: list[str], workdir: Path) -> dict:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(workdir),
        encoding="utf-8",
        errors="replace",
        **hidden_subprocess_kwargs(),
    )
    payload = (proc.stdout or proc.stderr).strip()
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return {
            "status": "error",
            "action": "subprocess",
            "error": {"code": "invalid_json", "message": payload[-500:] or "子进程未返回 JSON"},
        }


def redacted_argv(argv: list[str]) -> list[str]:
    values = [str(item) for item in argv]
    redacted = []
    hide_next = False
    for item in values:
        if hide_next:
            redacted.append("<redacted>")
            hide_next = False
            continue
        redacted.append(item)
        if item in SENSITIVE_ARG_FLAGS:
            hide_next = True
    return redacted


def command_metadata(cmd: list[str]) -> dict:
    return {
        "argv_redacted": redacted_argv(cmd),
        "safety_args_present": {
            "confirm_token": "--confirm-token" in cmd,
            "voltage": "--voltage" in cmd,
            "current_limit": "--current-limit" in cmd,
            "erase_scope": "--erase-scope" in cmd,
            "recovery": "--recovery" in cmd,
            "external_loads": "--external-loads" in cmd,
            "artifact": "--safety-artifact" in cmd,
            "artifact_hash": "--artifact-hash" in cmd,
        },
        "raw_argv_returned": False,
    }


def generated_command_result(
    cmd: list[str],
    *,
    action: str,
    summary: str,
    backend: str,
    dry_run: bool,
    hardware_side_effect: bool = True,
) -> dict:
    return {
        "status": "ok",
        "action": action,
        "summary": summary,
        "details": {
            "command": command_metadata(cmd),
            "backend": backend,
            "dry_run": dry_run,
            "executed": False,
            "prepared_executable": True,
            "hardware_side_effect_if_executed": hardware_side_effect,
        },
    }


def prepared_command_result(
    cmd: list[str],
    workdir: Path,
    *,
    action: str,
    backend: str,
    hardware_side_effect: bool = False,
    extra_details: dict | None = None,
) -> dict:
    details = {
        "command": command_metadata(cmd),
        "cwd": str(workdir),
        "backend": backend,
        "dry_run": True,
        "executed": False,
        "prepared_executable": True,
        "hardware_side_effect_if_executed": hardware_side_effect,
    }
    if extra_details:
        details.update(extra_details)
    return {
        "status": "ok",
        "action": action,
        "summary": f"dry-run prepared {backend} {action} command without executing it",
        "details": details,
    }


def run_or_prepare(
    cmd: list[str],
    workdir: Path,
    *,
    dry_run: bool,
    action: str,
    backend: str,
    hardware_side_effect: bool = False,
    extra_details: dict | None = None,
) -> dict:
    if dry_run:
        return prepared_command_result(
            cmd,
            workdir,
            action=action,
            backend=backend,
            hardware_side_effect=hardware_side_effect,
            extra_details=extra_details,
        )
    return _with_backend(run_json(cmd, workdir), backend)


def append_safety_args(cmd: list[str], safety: dict | None) -> list[str]:
    if not safety:
        return cmd
    mapping = {
        "confirm_token": "--confirm-token",
        "voltage": "--voltage",
        "current_limit": "--current-limit",
        "erase_scope": "--erase-scope",
        "recovery": "--recovery",
        "external_loads": "--external-loads",
        "artifact": "--safety-artifact",
        "artifact_hash": "--artifact-hash",
    }
    for key, flag in mapping.items():
        value = safety.get(key)
        if value:
            cmd.extend([flag, str(value)])
    return cmd


def select_build_backend(workflow_config: dict, discovery: dict, explicit: str | None) -> tuple[str | None, dict | None]:
    backend = explicit or workflow_config.get("preferred_build") or "auto"
    if backend != "auto":
        return backend, None
    candidates = [name for name in ("keil", "gcc", "eide") if discovery[name]]
    if len(candidates) == 1:
        return candidates[0], None
    if len(candidates) > 1:
        return None, {"code": "multiple_build_backends", "message": "同时发现多个构建后端（Keil/GCC/EIDE），请显式指定 build backend", "candidates": candidates}
    return None, {"code": "no_build_backend", "message": "未发现可构建工程", "candidates": []}


def build_eide_project(workspace: Path, full_config: dict, discovery: dict, *, dry_run: bool = False) -> dict:
    eide_config = full_config.get("eide", {})
    project = eide_config.get("project")
    if not project:
        project, error = _single_or_error(discovery["eide"], "EIDE 工程")
        if error:
            return {"status": "error", "action": "build", "error": error}

    config_name = eide_config.get("config")
    if not config_name:
        return {"status": "error", "action": "build", "error": {"code": "missing_config", "message": "需要在 .embeddedskills/config.json 的 eide 段配置 config（构建配置名称）"}}

    cmd = [
        PYTHON_EXE,
        str(ROOT_DIR / "eide" / "scripts" / "eide_build.py"),
        "build",
        "--workspace",
        str(workspace),
        "--project",
        project,
        "--config",
        config_name,
        "--json",
    ]
    log_dir = eide_config.get("log_dir")
    if log_dir:
        cmd.extend(["--log-dir", log_dir])
    return run_or_prepare(cmd, workspace, dry_run=dry_run, action="build", backend="eide")


def build_project(workspace: Path, full_config: dict, discovery: dict, backend: str | None, *, dry_run: bool = False) -> dict:
    workflow_config = full_config.get("workflow", {})
    selected, error = select_build_backend(workflow_config, discovery, backend)
    if error:
        return {"status": "error", "action": "build", "error": error}

    if selected == "keil":
        keil_config = full_config.get("keil", {})
        project = keil_config.get("project")
        if not project:
            project, error = _single_or_error(discovery["keil"], "Keil 工程")
            if error:
                return {"status": "error", "action": "build", "error": error}
        cmd = [
            PYTHON_EXE,
            str(ROOT_DIR / "keil" / "scripts" / "keil_build.py"),
            "build",
            "--workspace",
            str(workspace),
            "--project",
            project,
            "--json",
        ]
        target = keil_config.get("target")
        uv4_exe = keil_config.get("uv4_exe")
        if target:
            cmd.extend(["--target", target])
        if uv4_exe:
            cmd.extend(["--uv4", uv4_exe])
        return run_or_prepare(cmd, workspace, dry_run=dry_run, action="build", backend=selected)

    if selected == "eide":
        return build_eide_project(workspace, full_config, discovery, dry_run=dry_run)

    gcc_config = full_config.get("gcc", {})
    project = gcc_config.get("project")
    if not project:
        project, error = _single_or_error(discovery["gcc"], "GCC 工程")
        if error:
            return {"status": "error", "action": "build", "error": error}
    preset = gcc_config.get("preset")
    if not preset:
        return {"status": "error", "action": "build", "error": {"code": "missing_preset", "message": "需要在 .embeddedskills/config.json 的 gcc 段配置 preset"}}
    cmd = [
        PYTHON_EXE,
        str(ROOT_DIR / "gcc" / "scripts" / "gcc_build.py"),
        "build",
        "--workspace",
        str(workspace),
        "--project",
        project,
        "--preset",
        preset,
        "--json",
    ]
    cmake_exe = gcc_config.get("cmake_exe")
    if cmake_exe:
        cmd.extend(["--cmake", cmake_exe])
    return run_or_prepare(cmd, workspace, dry_run=dry_run, action="build", backend=selected)


def flash_project(workspace: Path, full_config: dict, state: dict, explicit: str | None, safety: dict | None = None, *, dry_run: bool = False) -> dict:
    workflow_config = full_config.get("workflow", {})
    selected, error = _select_backend(
        explicit,
        workflow_config.get("preferred_flash"),
        [name for name, ready in (("openocd", _is_openocd_ready(full_config)), ("jlink", _is_jlink_ready(full_config)), ("probe-rs", _is_probe_rs_ready(full_config))) if ready],
        "flash",
    )
    if error:
        return {"status": "error", "action": "flash", "error": error}

    last_build = get_state_entry(state, "last_build")
    artifacts = last_build.get("artifacts", {})
    flash_file = last_build.get("flash_file") or artifacts.get("flash_file")
    if not flash_file:
        if dry_run:
            return {
                "status": "warning",
                "action": "flash",
                "summary": "flash dry-run 缺少 state.last_build.flash_file，已跳过 flash 命令生成",
                "details": {
                    "backend": selected,
                    "dry_run": True,
                    "prepared_executable": False,
                    "artifact_source": "missing state.last_build.flash_file",
                    "missing_artifact": "state.last_build.flash_file",
                    "warning_code": "missing_last_build",
                },
            }
        return {
            "status": "error",
            "action": "flash",
            "summary": "未找到 last_build.flash_file，请先执行 workflow build",
            "details": {
                "backend": selected,
                "dry_run": False,
                "prepared_executable": False,
                "artifact_source": "missing state.last_build.flash_file",
                "missing_artifact": "state.last_build.flash_file",
            },
            "error": {"code": "missing_last_build", "message": "未找到 last_build.flash_file，请先执行 workflow build"},
        }

    guard = artifact_guard(workspace, flash_file, safety, "state.last_build.flash_file")
    if guard.get("status") != "ok":
        return guard

    if selected == "openocd":
        openocd_cfg = full_config.get("openocd", {})
        cmd = [
            PYTHON_EXE,
            str(ROOT_DIR / "openocd" / "scripts" / "openocd_run.py"),
            "flash",
            "--workspace",
            str(workspace),
            "--file",
            flash_file,
            "--json",
        ]
        if openocd_cfg.get("board"):
            cmd.extend(["--board", openocd_cfg["board"]])
        if openocd_cfg.get("interface"):
            cmd.extend(["--interface", openocd_cfg["interface"]])
        if openocd_cfg.get("target"):
            cmd.extend(["--target", openocd_cfg["target"]])
        return run_or_prepare(append_safety_args(cmd, safety), workspace, dry_run=dry_run, action="flash", backend="openocd", hardware_side_effect=True, extra_details={"artifact_source": "state.last_build.flash_file", "artifact_hash_verified": guard.get("artifact_hash", "")})

    if selected == "jlink":
        jlink_cfg = full_config.get("jlink", {})
        if not jlink_cfg.get("device"):
            return {"status": "error", "action": "flash", "error": {"code": "missing_device", "message": "使用 jlink flash 时需要在 .embeddedskills/config.json 的 jlink 段提供 device"}}
        cmd = [
            PYTHON_EXE,
            str(ROOT_DIR / "jlink" / "scripts" / "jlink_exec.py"),
            "flash",
            "--file",
            flash_file,
            "--device",
            jlink_cfg["device"],
            "--json",
        ]
        if jlink_cfg.get("interface"):
            cmd.extend(["--interface", jlink_cfg["interface"]])
        if jlink_cfg.get("speed"):
            cmd.extend(["--speed", str(jlink_cfg["speed"])])
        return run_or_prepare(append_safety_args(cmd, safety), workspace, dry_run=dry_run, action="flash", backend="jlink", hardware_side_effect=True, extra_details={"artifact_source": "state.last_build.flash_file", "artifact_hash_verified": guard.get("artifact_hash", "")})

    probe_rs_cfg = full_config.get("probe-rs", {})
    if not probe_rs_cfg.get("chip"):
        return {"status": "error", "action": "flash", "error": {"code": "missing_chip", "message": "使用 probe-rs flash 时需要在 .embeddedskills/config.json 的 probe-rs 段提供 chip"}}
    cmd = [
        PYTHON_EXE,
        str(ROOT_DIR / "probe-rs" / "scripts" / "probe_rs_exec.py"),
        "flash",
        "--workspace",
        str(workspace),
        "--file",
        flash_file,
        "--chip",
        probe_rs_cfg["chip"],
        "--json",
    ]
    if probe_rs_cfg.get("protocol"):
        cmd.extend(["--protocol", probe_rs_cfg["protocol"]])
    if probe_rs_cfg.get("probe"):
        cmd.extend(["--probe", probe_rs_cfg["probe"]])
    if probe_rs_cfg.get("speed"):
        cmd.extend(["--speed", str(probe_rs_cfg["speed"])])
    if probe_rs_cfg.get("connect_under_reset"):
        cmd.append("--connect-under-reset")
    return run_or_prepare(append_safety_args(cmd, safety), workspace, dry_run=dry_run, action="flash", backend="probe-rs", hardware_side_effect=True, extra_details={"artifact_source": "state.last_build.flash_file", "artifact_hash_verified": guard.get("artifact_hash", "")})


def debug_project(workspace: Path, full_config: dict, state: dict, explicit: str | None, safety: dict | None = None, *, dry_run: bool = False) -> dict:
    workflow_config = full_config.get("workflow", {})
    selected, error = _select_backend(
        explicit,
        workflow_config.get("preferred_debug"),
        [name for name, ready in (("openocd", _is_openocd_ready(full_config)), ("jlink", _is_jlink_ready(full_config)), ("probe-rs", _is_probe_rs_ready(full_config))) if ready],
        "debug",
    )
    if error:
        return {"status": "error", "action": "build-debug", "error": error}

    last_build = get_state_entry(state, "last_build")
    artifacts = last_build.get("artifacts", {})
    debug_file = last_build.get("debug_file") or artifacts.get("debug_file")
    if not debug_file:
        if dry_run:
            return {
                "status": "warning",
                "action": "build-debug",
                "summary": "debug dry-run 缺少 state.last_build.debug_file，已跳过 debug 命令生成",
                "details": {
                    "backend": selected,
                    "dry_run": True,
                    "prepared_executable": False,
                    "artifact_source": "missing state.last_build.debug_file",
                    "missing_artifact": "state.last_build.debug_file",
                    "warning_code": "missing_last_build",
                },
            }
        return {
            "status": "error",
            "action": "build-debug",
            "summary": "未找到 last_build.debug_file，请先执行 workflow build",
            "details": {
                "backend": selected,
                "dry_run": False,
                "prepared_executable": False,
                "artifact_source": "missing state.last_build.debug_file",
                "missing_artifact": "state.last_build.debug_file",
            },
            "error": {"code": "missing_last_build", "message": "未找到 last_build.debug_file，请先执行 workflow build"},
        }

    guard = artifact_guard(workspace, debug_file, safety, "state.last_build.debug_file")
    if guard.get("status") != "ok":
        return guard

    if selected == "openocd":
        openocd_cfg = full_config.get("openocd", {})
        cmd = [
            PYTHON_EXE,
            str(ROOT_DIR / "openocd" / "scripts" / "openocd_gdb.py"),
            "crash-report",
            "--workspace",
            str(workspace),
            "--elf",
            debug_file,
            "--json",
        ]
        if openocd_cfg.get("board"):
            cmd.extend(["--board", openocd_cfg["board"]])
        if openocd_cfg.get("interface"):
            cmd.extend(["--interface", openocd_cfg["interface"]])
        if openocd_cfg.get("target"):
            cmd.extend(["--target", openocd_cfg["target"]])
        if openocd_cfg.get("gdb_exe"):
            cmd.extend(["--gdb-exe", openocd_cfg["gdb_exe"]])
        return run_or_prepare(append_safety_args(cmd, safety), workspace, dry_run=dry_run, action="debug", backend="openocd", hardware_side_effect=True, extra_details={"artifact_source": "state.last_build.debug_file", "artifact_hash_verified": guard.get("artifact_hash", "")})

    if selected == "jlink":
        jlink_cfg = full_config.get("jlink", {})
        if not jlink_cfg.get("device"):
            return {"status": "error", "action": "build-debug", "error": {"code": "missing_device", "message": "使用 jlink gdb 时需要在 .embeddedskills/config.json 的 jlink 段提供 device"}}
        cmd = [
            PYTHON_EXE,
            str(ROOT_DIR / "jlink" / "scripts" / "jlink_gdb.py"),
            "crash-report",
            "--workspace",
            str(workspace),
            "--elf",
            debug_file,
            "--device",
            jlink_cfg["device"],
            "--json",
        ]
        if jlink_cfg.get("interface"):
            cmd.extend(["--interface", jlink_cfg["interface"]])
        if jlink_cfg.get("speed"):
            cmd.extend(["--speed", str(jlink_cfg["speed"])])
        return run_or_prepare(append_safety_args(cmd, safety), workspace, dry_run=dry_run, action="debug", backend="jlink", hardware_side_effect=True, extra_details={"artifact_source": "state.last_build.debug_file", "artifact_hash_verified": guard.get("artifact_hash", "")})

    probe_rs_cfg = full_config.get("probe-rs", {})
    if not probe_rs_cfg.get("chip"):
        return {"status": "error", "action": "build-debug", "error": {"code": "missing_chip", "message": "使用 probe-rs gdb 时需要在 .embeddedskills/config.json 的 probe-rs 段提供 chip"}}
    cmd = [
        PYTHON_EXE,
        str(ROOT_DIR / "probe-rs" / "scripts" / "probe_rs_gdb.py"),
        "crash-report",
        "--workspace",
        str(workspace),
        "--elf",
        debug_file,
        "--chip",
        probe_rs_cfg["chip"],
        "--json",
    ]
    if probe_rs_cfg.get("protocol"):
        cmd.extend(["--protocol", probe_rs_cfg["protocol"]])
    if probe_rs_cfg.get("probe"):
        cmd.extend(["--probe", probe_rs_cfg["probe"]])
    if probe_rs_cfg.get("speed"):
        cmd.extend(["--speed", str(probe_rs_cfg["speed"])])
    if probe_rs_cfg.get("connect_under_reset"):
        cmd.append("--connect-under-reset")
    return run_or_prepare(append_safety_args(cmd, safety), workspace, dry_run=dry_run, action="debug", backend="probe-rs", hardware_side_effect=True, extra_details={"artifact_source": "state.last_build.debug_file", "artifact_hash_verified": guard.get("artifact_hash", "")})


def observe_project(workspace: Path, full_config: dict, explicit: str | None, safety: dict | None = None, *, dry_run: bool = False) -> dict:
    workflow_config = full_config.get("workflow", {})
    selected, error = _select_backend(
        explicit,
        workflow_config.get("preferred_observe"),
        [name for name, ready in (("openocd", _is_openocd_ready(full_config)), ("jlink", _is_jlink_ready(full_config)), ("probe-rs", _is_probe_rs_ready(full_config))) if ready],
        "observe",
    )
    if error:
        return {"status": "error", "action": "observe", "error": error}

    if selected == "openocd":
        openocd_cfg = full_config.get("openocd", {})
        cmd = [
            PYTHON_EXE,
            str(ROOT_DIR / "openocd" / "scripts" / "openocd_semihosting.py"),
            "--workspace",
            str(workspace),
            "--json",
        ]
        if openocd_cfg.get("board"):
            cmd.extend(["--board", openocd_cfg["board"]])
        if openocd_cfg.get("interface"):
            cmd.extend(["--interface", openocd_cfg["interface"]])
        if openocd_cfg.get("target"):
            cmd.extend(["--target", openocd_cfg["target"]])
        return generated_command_result(
            append_safety_args(cmd, safety),
            action="observe",
            summary="已生成 openocd semihosting 观察命令",
            backend="openocd",
            dry_run=dry_run,
        )

    if selected == "jlink":
        jlink_cfg = full_config.get("jlink", {})
        if not jlink_cfg.get("device"):
            return {"status": "error", "action": "observe", "error": {"code": "missing_device", "message": "使用 jlink 观测时需要在 .embeddedskills/config.json 的 jlink 段提供 device"}}
        cmd = [
            PYTHON_EXE,
            str(ROOT_DIR / "jlink" / "scripts" / "jlink_rtt.py"),
            "--workspace",
            str(workspace),
            "--device",
            jlink_cfg["device"],
            "--json",
        ]
        return generated_command_result(
            append_safety_args(cmd, safety),
            action="observe",
            summary="已生成 jlink RTT 观察命令",
            backend="jlink",
            dry_run=dry_run,
        )

    probe_rs_cfg = full_config.get("probe-rs", {})
    if not probe_rs_cfg.get("chip"):
        return {"status": "error", "action": "observe", "error": {"code": "missing_chip", "message": "使用 probe-rs 观测时需要在 .embeddedskills/config.json 的 probe-rs 段提供 chip"}}
    cmd = [
        PYTHON_EXE,
        str(ROOT_DIR / "probe-rs" / "scripts" / "probe_rs_rtt.py"),
        "--workspace",
        str(workspace),
        "--chip",
        probe_rs_cfg["chip"],
        "--json",
    ]
    if probe_rs_cfg.get("protocol"):
        cmd.extend(["--protocol", probe_rs_cfg["protocol"]])
    if probe_rs_cfg.get("probe"):
        cmd.extend(["--probe", probe_rs_cfg["probe"]])
    if probe_rs_cfg.get("speed"):
        cmd.extend(["--speed", str(probe_rs_cfg["speed"])])
    if probe_rs_cfg.get("connect_under_reset"):
        cmd.append("--connect-under-reset")
    return generated_command_result(
        append_safety_args(cmd, safety),
        action="observe",
        summary="已生成 probe-rs RTT 观察命令",
        backend="probe-rs",
        dry_run=dry_run,
    )


def diagnose(workspace: Path, full_config: dict, discovery: dict, state: dict) -> dict:
    workflow_config = full_config.get("workflow", {})
    hints = []
    if not discovery["keil"] and not discovery["gcc"] and not discovery["eide"]:
        hints.append("当前 workspace 未发现 Keil/GCC/EIDE 工程")
    if not get_state_entry(state, "last_build"):
        hints.append("尚未生成 last_build，后续 flash/debug 无法自动串联")
    if workflow_config.get("preferred_build") == "auto" and sum(1 for k in ("keil", "gcc", "eide") if discovery[k]) > 1:
        hints.append("同时存在多个构建后端（Keil/GCC/EIDE），建议在 .embeddedskills/config.json 的 workflow 段固定 preferred_build")
    return {
        "status": "ok",
        "action": "diagnose",
        "summary": "workflow 诊断完成",
        "details": {
            "workspace": str(workspace),
            "discovery": discovery,
            "state": {
                "last_build": get_state_entry(state, "last_build"),
                "last_flash": get_state_entry(state, "last_flash"),
                "last_debug": get_state_entry(state, "last_debug"),
                "last_observe": get_state_entry(state, "last_observe"),
            },
            "hints": hints,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="workflow run")
    parser.add_argument("action", choices=["plan", "build", "build-flash", "build-debug", "observe", "diagnose"])
    parser.add_argument("--workspace", default=None, help="workspace 根目录，默认当前目录")
    parser.add_argument("--config", default=None, help="workflow config.json 路径（已废弃，仅保留兼容性）")
    parser.add_argument("--build-backend", choices=["auto", "keil", "gcc", "eide"], default=None)
    parser.add_argument("--flash-backend", choices=["auto", "jlink", "openocd", "probe-rs"], default=None)
    parser.add_argument("--debug-backend", choices=["auto", "jlink", "openocd", "probe-rs"], default=None)
    parser.add_argument("--observe-backend", choices=["auto", "jlink", "openocd", "probe-rs"], default=None)
    parser.add_argument("--confirm-token", default="")
    parser.add_argument("--child-confirm-token", default="")
    parser.add_argument("--target", default="")
    parser.add_argument("--probe", default="")
    parser.add_argument("--voltage", default="")
    parser.add_argument("--current-limit", default="")
    parser.add_argument("--erase-scope", default="")
    parser.add_argument("--recovery", default="")
    parser.add_argument("--external-loads", default="")
    parser.add_argument("--artifact", default="")
    parser.add_argument("--artifact-hash", default="")
    parser.add_argument("--child-artifact-hash", default="")
    parser.add_argument("--dry-run", action="store_true", help="只生成将要执行的命令，不运行子进程、不消费 token、不写 state/config")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    started_at = now_iso()
    started_ts = time.time()
    workspace = workspace_root(args.workspace)
    try:
        full_config, config_path = load_effective_project_config(str(workspace), args.config)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        wrapped = make_result(
            status="error",
            action=args.action,
            summary=str(exc),
            context=parameter_context(provider="workflow", workspace=str(workspace)),
            error={"code": "invalid_config", "message": str(exc)},
            timing=make_timing(started_at, (time.time() - started_ts) * 1000),
        )
        if args.as_json:
            output_json(wrapped)
        else:
            print(f"[workflow {args.action}] {wrapped['summary']}")
        sys.exit(1)

    full_config.get("workflow", {})
    state = load_workspace_state(str(workspace))
    discovery = discover_projects(workspace)

    gate_action = args.action if args.action in {"build-flash", "build-debug"} else ""
    if gate_action and not args.dry_run:
        gate = safety_gate.check_token(
            gate_action,
            args.confirm_token,
            target=args.target,
            probe=args.probe,
            voltage=args.voltage,
            current_limit=args.current_limit,
            erase_scope=args.erase_scope,
            recovery=args.recovery,
            external_loads=args.external_loads,
            artifact=args.artifact,
            artifact_hash=args.artifact_hash,
            backend=args.flash_backend or args.debug_backend or args.observe_backend or "",
            workspace=args.workspace,
            consume=True,
        )
        if not gate["allowed"]:
            blocked = safety_gate.blocked_result(args.action, gate)
            wrapped = make_result(
                status="error",
                action=args.action,
                summary=gate["reason"],
                details=blocked.get("details", {}),
                context=parameter_context(provider="workflow", workspace=str(workspace), config_path=config_path),
                error=blocked["error"],
                timing=make_timing(started_at, (time.time() - started_ts) * 1000),
            )
            if args.as_json:
                output_json(wrapped)
            else:
                print(f"[workflow {args.action}] {wrapped['summary']}", file=sys.stderr)
            sys.exit(1)

    safety_args = {
        "confirm_token": args.child_confirm_token,
        "voltage": args.voltage,
        "current_limit": args.current_limit,
        "erase_scope": args.erase_scope,
        "recovery": args.recovery,
        "external_loads": args.external_loads,
        "artifact": args.artifact,
        "artifact_hash": args.child_artifact_hash or args.artifact_hash,
    }

    # 用于追踪实际使用的后端，成功后将写回配置
    used_backends = {}

    if args.action == "plan":
        cmd = [PYTHON_EXE, str(ROOT_DIR / "workflow" / "scripts" / "workflow_plan.py"), "--workspace", str(workspace), "--json"]
        if config_path:
            cmd.extend(["--config", config_path])
        result = run_or_prepare(cmd, workspace, dry_run=args.dry_run, action="plan", backend="workflow")
    elif args.action == "build":
        result = build_project(workspace, full_config, discovery, args.build_backend, dry_run=args.dry_run)
        if result.get("status") == "ok" and result.get("details", {}).get("backend"):
            used_backends["preferred_build"] = result["details"]["backend"]
    elif args.action == "build-flash":
        build_result = build_project(workspace, full_config, discovery, args.build_backend, dry_run=args.dry_run)
        if build_result.get("status") == "error":
            result = build_result
        else:
            if build_result.get("details", {}).get("backend"):
                used_backends["preferred_build"] = build_result["details"]["backend"]
            if not args.dry_run:
                state = load_workspace_state(str(workspace))
            flash_result = flash_project(workspace, full_config, state, args.flash_backend, safety_args, dry_run=args.dry_run)
            if flash_result.get("status") == "ok" and flash_result.get("details", {}).get("backend"):
                used_backends["preferred_flash"] = flash_result["details"]["backend"]
            result = {
                "status": flash_result.get("status", "error"),
                "action": "build-flash",
                "summary": (
                    "build-flash dry-run 已生成命令"
                    if args.dry_run and flash_result.get("status") == "ok"
                    else (
                        "build-flash dry-run 仅生成 build 命令，flash 需要已有 last_build.flash_file"
                        if args.dry_run and flash_result.get("status") == "warning"
                        else ("build-flash 完成" if flash_result.get("status") == "ok" else flash_result.get("error", {}).get("message", "build-flash 失败"))
                    )
                ),
                "details": {"build": build_result, "flash": flash_result, "dry_run": args.dry_run},
            }
            if flash_result.get("error"):
                result["error"] = flash_result["error"]
    elif args.action == "build-debug":
        build_result = build_project(workspace, full_config, discovery, args.build_backend, dry_run=args.dry_run)
        if build_result.get("status") == "error":
            result = build_result
        else:
            if build_result.get("details", {}).get("backend"):
                used_backends["preferred_build"] = build_result["details"]["backend"]
            if not args.dry_run:
                state = load_workspace_state(str(workspace))
            debug_result = debug_project(workspace, full_config, state, args.debug_backend, safety_args, dry_run=args.dry_run)
            if debug_result.get("status") == "ok" and debug_result.get("details", {}).get("backend"):
                used_backends["preferred_debug"] = debug_result["details"]["backend"]
            result = {
                "status": debug_result.get("status", "error"),
                "action": "build-debug",
                "summary": (
                    "build-debug dry-run 已生成命令"
                    if args.dry_run and debug_result.get("status") == "ok"
                    else (
                        "build-debug dry-run 仅生成 build 命令，debug 需要已有 last_build.debug_file"
                        if args.dry_run and debug_result.get("status") == "warning"
                        else ("build-debug 完成" if debug_result.get("status") == "ok" else debug_result.get("error", {}).get("message", "build-debug 失败"))
                    )
                ),
                "details": {"build": build_result, "debug": debug_result, "dry_run": args.dry_run},
            }
            if debug_result.get("error"):
                result["error"] = debug_result["error"]
    elif args.action == "observe":
        observe_result = observe_project(workspace, full_config, args.observe_backend, safety_args, dry_run=True)
        if args.dry_run:
            result = observe_result
        else:
            details = dict(observe_result.get("details") or {})
            details["observe_execution_gate"] = {
                "status": "planned-gated",
                "executed": False,
                "token_consumed": False,
                "state_written": False,
                "config_written": False,
                "safety_log_written": False,
                "reason": "workflow observe currently prepares a bounded observe command only; real observe execution remains backend-gated.",
            }
            result = {
                "status": "planned-gated",
                "action": "observe",
                "summary": "observe prepared a backend command but did not consume tokens, write state/config, or execute hardware observation.",
                "details": details,
            }
        if args.dry_run and result.get("status") == "ok" and result.get("details", {}).get("backend"):
            used_backends["preferred_observe"] = result["details"]["backend"]
    else:
        result = diagnose(workspace, full_config, discovery, state)

    if args.dry_run:
        details = dict(result.get("details") or {})
        details["dry_run_controls"] = {
            "dry_run": True,
            "executed": False,
            "hardware_side_effect": False,
            "token_consumed": False,
            "state_written": False,
            "config_written": False,
            "safety_log_written": False,
        }
        result["details"] = details

    # 将确认过的 preferred 值写回 .embeddedskills/config.json
    if used_backends and not args.dry_run:
        save_project_config(str(workspace), used_backends)

    # 更新 workflow 自己的运行状态到 state.json，避免覆盖底层 skill 的 last_build/last_flash/last_debug/last_observe
    if result.get("status") == "ok" and args.action in ("build", "build-flash", "build-debug", "observe") and not args.dry_run:
        state_record = {
            "action": args.action,
            "timestamp": now_iso(),
        }
        state_details = _workflow_state_details(args.action, result)
        if state_details:
            state_record["details"] = state_details
        update_state_entry(_workflow_state_key(args.action), state_record, str(workspace))

    wrapped = make_result(
        status=result.get("status", "error"),
        action=args.action,
        summary=result.get("summary") or (result.get("error") or {}).get("message") or "workflow 执行完成",
        details=result.get("details", {}),
        context=parameter_context(provider="workflow", workspace=str(workspace), config_path=config_path),
        error=result.get("error"),
        timing=make_timing(started_at, (time.time() - started_ts) * 1000),
    )

    if args.as_json:
        output_json(wrapped)
    else:
        print(f"[workflow {args.action}] {wrapped['summary']}")
        if wrapped.get("error"):
            sys.exit(1)


if __name__ == "__main__":
    main()
