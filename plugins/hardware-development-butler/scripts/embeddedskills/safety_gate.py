"""Shared confirmation gate for embeddedskills hardware actions.

This module is intentionally small and dependency-free so low-level scripts can
import it before opening probes, serial ports, CAN adapters, or sockets.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_log_locks: dict[str, threading.Lock] = {}
_log_locks_lock = threading.Lock()

# Value-sanity (防呆) thresholds. These guard against typos and accidental
# inputs touching real hardware; they are deliberately wide so any legitimate
# embedded target passes untouched.
VOLTAGE_MIN_V = 0.0          # anything <= 0 is physically meaningless here
VOLTAGE_WARN_V = 3.6         # above typical 1.8/3.3 logic rails -> warn
VOLTAGE_MAX_V = 6.0          # above this for an MCU target is almost certainly a typo
CURRENT_WARN_MA = 1000.0     # > 1A for a dev-board target -> warn

# Erase-scope phrases that are destructive but sometimes legitimate (recovery,
# read-protection removal). Never blocked, always warned so a human notices.
_DESTRUCTIVE_ERASE_KEYWORDS = (
    "mass erase",
    "full chip",
    "whole chip",
    "chip erase",
    "erase all",
    "option byte",
    "整片擦除",
    "全片擦除",
    "全片",
    "整片",
)

_NUMBER_RE = re.compile(r"[-+]?\d*\.?\d+")
_EE_VOLTAGE_RE = re.compile(r"^(\d+)v(\d+)$")


def _extract_float(text: str) -> float | None:
    match = _NUMBER_RE.search(text)
    if not match:
        return None
    try:
        value = float(match.group())
    except ValueError:
        return None
    # Reject nan/inf which float() accepts but make no physical sense.
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return value


def parse_voltage(text: str) -> float | None:
    """Parse a voltage string to volts, or None when it is not understood.

    Accepts ``3.3V``, ``3.3 V``, ``1.8v``, bare ``5``, and EE notation ``3V3``.
    """
    t = str(text or "").strip().lower()
    if not t:
        return None
    ee = _EE_VOLTAGE_RE.match(t.replace(" ", ""))
    if ee:
        return float(f"{ee.group(1)}.{ee.group(2)}")
    return _extract_float(t)


def parse_current_ma(text: str) -> float | None:
    """Parse a current-limit string to milliamps, or None when not understood.

    Accepts ``100mA``, ``0.1A``, ``1A``, and bare numbers (assumed mA).
    """
    t = str(text or "").strip().lower()
    if not t:
        return None
    is_amp = "ma" not in t and "a" in t
    value = _extract_float(t)
    if value is None:
        return None
    return value * 1000.0 if is_amp else value


def evaluate_value_safety(action: str, record: dict[str, Any]) -> dict[str, Any]:
    """Automated mistake-prevention checks on safety-field *values*.

    Field presence is enforced by :func:`missing_required_fields`; this layer
    looks at the values themselves. It blocks physically-impossible inputs
    (unparseable / non-positive / absurd voltage or current) and warns on
    valid-but-risky ones (elevated voltage, high current, destructive erase
    scope). Non-hardware actions and empty fields are left alone.
    """
    action = normalize_action(action)
    blocks: list[str] = []
    warnings: list[str] = []
    if not is_hardware_action(action):
        return {"safe": True, "blocks": blocks, "warnings": warnings}

    voltage_raw = str(record.get("voltage") or "").strip()
    if voltage_raw:
        volts = parse_voltage(voltage_raw)
        if volts is None:
            blocks.append(f"voltage value not understood: {voltage_raw!r}")
        elif volts <= VOLTAGE_MIN_V:
            blocks.append(f"voltage must be positive, got {voltage_raw!r}")
        elif volts > VOLTAGE_MAX_V:
            blocks.append(f"implausible voltage for an MCU target: {voltage_raw!r} (> {VOLTAGE_MAX_V}V)")
        elif volts > VOLTAGE_WARN_V:
            warnings.append(f"elevated voltage {voltage_raw!r} (> {VOLTAGE_WARN_V}V) — confirm the target rail")

    current_raw = str(record.get("current_limit") or "").strip()
    if current_raw:
        milliamps = parse_current_ma(current_raw)
        if milliamps is None:
            blocks.append(f"current limit value not understood: {current_raw!r}")
        elif milliamps <= 0:
            blocks.append(f"current limit must be positive, got {current_raw!r}")
        elif milliamps > CURRENT_WARN_MA:
            warnings.append(f"high current limit {current_raw!r} (> {CURRENT_WARN_MA:.0f}mA) — confirm it is intentional")

    if action in {"erase", "flash", "build-flash"}:
        scope = str(record.get("erase_scope") or "").strip().lower()
        if scope and any(keyword in scope for keyword in _DESTRUCTIVE_ERASE_KEYWORDS):
            warnings.append(
                f"destructive erase scope {record.get('erase_scope')!r} — confirm a full/mass/option-byte erase is intended"
            )

    return {"safe": not blocks, "blocks": blocks, "warnings": warnings}

TOKEN_FIELDS = [
    "action",
    "target",
    "probe",
    "voltage",
    "current_limit",
    "erase_scope",
    "recovery",
    "external_loads",
    "artifact",
    "artifact_hash",
    "backend",
]

READ_ONLY_ACTIONS = {
    "adapter-info",
    "detect",
    "flash-banks",
    "info",
    "list",
    "probe",
    "targets",
}

HARDWARE_ACTIONS = {
    "attach",
    "build-debug",
    "build-flash",
    "capture-network",
    "can-observe",
    "debug",
    "erase",
    "flash",
    "go",
    "halt",
    "network-ping",
    "network-scan",
    "observe",
    "raw",
    "read-mem",
    "regs",
    "reset",
    "reset-init",
    "run",
    "run-to",
    "send-can",
    "send-uart",
    "serial-mux",
    "ssh-exec",
    "ssh-transfer",
    "ssh-tunnel",
    "step",
    "swo",
    "write-mem",
    "write-memory",
}

COMMON_REQUIRED_FIELDS = ("target", "probe", "voltage", "current_limit", "recovery")
BUS_REQUIRED_FIELDS = (*COMMON_REQUIRED_FIELDS, "external_loads")
ERASE_REQUIRED_FIELDS = (*COMMON_REQUIRED_FIELDS, "erase_scope")


def normalize_action(action: str) -> str:
    return action.strip().lower().replace("_", "-")


def token_payload(action: str, record: dict[str, Any]) -> dict[str, str]:
    payload = {"action": normalize_action(action)}
    for key in TOKEN_FIELDS:
        if key == "action":
            continue
        payload[key] = str(record.get(key) or "")
    return payload


def confirmation_token(action: str, record: dict[str, Any]) -> str:
    payload = json.dumps(token_payload(action, record), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return "hwc1-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def token_from_env_or_arg(token: str = "") -> str:
    return token or os.environ.get("HARDWARE_BUTLER_CONFIRM_TOKEN", "")


def is_hardware_action(action: str) -> bool:
    action = normalize_action(action)
    return action in HARDWARE_ACTIONS and action not in READ_ONLY_ACTIONS


def check_token(
    action: str,
    token: str = "",
    *,
    target: str = "",
    probe: str = "",
    voltage: str = "",
    current_limit: str = "",
    erase_scope: str = "",
    recovery: str = "",
    external_loads: str = "",
    artifact: str = "",
    artifact_hash: str = "",
    backend: str = "",
    workspace: str | Path | None = None,
    consume: bool = False,
) -> dict[str, Any]:
    action = normalize_action(action)
    if not is_hardware_action(action):
        return {"allowed": True, "required": False, "action": action, "reason": ""}

    record = {
        "target": target,
        "probe": probe,
        "voltage": voltage,
        "current_limit": current_limit,
        "erase_scope": erase_scope,
        "recovery": recovery,
        "external_loads": external_loads,
        "artifact": artifact,
        "artifact_hash": artifact_hash,
        "backend": backend,
    }
    missing = missing_required_fields(action, record)
    if missing:
        return {
            "allowed": False,
            "required": True,
            "action": action,
            "reason": f"missing safety fields: {', '.join(missing)}",
            "expected_scope": token_payload(action, record),
            "missing_fields": missing,
        }
    value_safety = evaluate_value_safety(action, record)
    if value_safety["blocks"]:
        return {
            "allowed": False,
            "required": True,
            "action": action,
            "reason": "unsafe safety-field value(s): " + "; ".join(value_safety["blocks"]),
            "error_code": "unsafe_value",
            "value_safety": value_safety,
            "expected_scope": token_payload(action, record),
        }
    expected = confirmation_token(action, record)
    supplied = token_from_env_or_arg(token)
    if supplied == expected:
        if consume:
            replay = consume_token(workspace_root(workspace), supplied, action=action, backend=backend)
            if replay:
                return {
                    "allowed": False,
                    "required": True,
                    "action": action,
                    "reason": "confirmation token has already been consumed",
                    "error_code": "token_replay",
                    "details": replay,
                }
        return {
            "allowed": True,
            "required": True,
            "action": action,
            "reason": "",
            "token": supplied,
            "warnings": value_safety["warnings"],
        }
    return {
        "allowed": False,
        "required": True,
        "action": action,
        "reason": "confirmation token missing or not bound to this hardware action",
        "expected_scope": token_payload(action, record),
    }


def missing_required_fields(action: str, record: dict[str, Any]) -> list[str]:
    required: tuple[str, ...]
    if action in {
        "can-observe",
        "capture-network",
        "network-ping",
        "network-scan",
        "send-can",
        "send-uart",
        "serial-mux",
        "ssh-exec",
        "ssh-transfer",
        "ssh-tunnel",
    }:
        required = BUS_REQUIRED_FIELDS
    elif action in {"erase", "flash", "build-flash"}:
        required = ERASE_REQUIRED_FIELDS
    else:
        required = COMMON_REQUIRED_FIELDS
    return [field for field in required if not str(record.get(field) or "").strip()]


def blocked_result(action: str, gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "error",
        "action": normalize_action(action),
        "error": {
            "code": gate.get("error_code") or "confirmation_required",
            "message": gate.get("reason") or "confirmation token required for hardware action",
        },
        "details": {
            "confirmation_required": True,
            "expected_scope": gate.get("expected_scope", {}),
            **(gate.get("details") or {}),
        },
    }


def workspace_root(workspace: str | Path | None = None) -> Path:
    if workspace:
        return Path(workspace).expanduser().resolve()
    return Path.cwd().resolve()


def safety_log_path(workspace: Path) -> Path:
    return workspace / ".embeddedskills" / "safety-log.jsonl"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def read_events(workspace: Path) -> list[dict[str, Any]]:
    path = safety_log_path(workspace)
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def _get_log_lock(log_path: str) -> threading.Lock:
    with _log_locks_lock:
        if log_path not in _log_locks:
            _log_locks[log_path] = threading.Lock()
        return _log_locks[log_path]


def consume_token(workspace: Path, token: str, *, action: str, backend: str) -> dict[str, Any]:
    hashed = token_hash(token)
    log_path = safety_log_path(workspace)
    lock = _get_log_lock(str(log_path))
    with lock:
        if any(item.get("event") == "token-consumed" and item.get("token_hash") == hashed for item in read_events(workspace)):
            return {"token_hash": hashed, "log_path": str(log_path)}
        log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "event": "token-consumed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "backend": backend,
            "token_hash": hashed,
        }
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return {}
