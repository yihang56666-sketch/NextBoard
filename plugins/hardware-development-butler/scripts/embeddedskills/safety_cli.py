"""CLI helpers for embeddedskills confirmation-token gates."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import safety_gate


def add_safety_args(parser: Any) -> None:
    parser.add_argument("--confirm-token", default="")
    parser.add_argument("--voltage", default="")
    parser.add_argument("--current-limit", default="")
    parser.add_argument("--recovery", default="")
    parser.add_argument("--external-loads", default="")
    parser.add_argument("--erase-scope", default="")
    parser.add_argument("--safety-artifact", default="")
    parser.add_argument("--artifact-hash", default="")


def require_gate(
    *,
    action: str,
    token: str,
    target: str,
    probe: str,
    voltage: str,
    current_limit: str,
    recovery: str,
    backend: str,
    external_loads: str = "",
    erase_scope: str = "",
    artifact: str = "",
    artifact_hash: str = "",
    json_output: bool = False,
    workspace: str | Path | None = None,
) -> None:
    gate = safety_gate.check_token(
        action,
        token,
        target=target,
        probe=probe,
        voltage=voltage,
        current_limit=current_limit,
        recovery=recovery,
        external_loads=external_loads,
        erase_scope=erase_scope,
        artifact=artifact,
        artifact_hash=artifact_hash,
        backend=backend,
        workspace=workspace,
        consume=True,
    )
    if gate["allowed"]:
        return
    result = safety_gate.blocked_result(action, gate)
    if json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[{action}] failed - {result['error']['message']}", file=sys.stderr)
    raise SystemExit(1)


def workspace_root(workspace: str | Path | None = None) -> Path:
    if workspace:
        return Path(workspace).expanduser().resolve()
    return Path.cwd().resolve()
