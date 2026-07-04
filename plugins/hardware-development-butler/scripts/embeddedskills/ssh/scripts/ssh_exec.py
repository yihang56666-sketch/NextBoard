#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import safety_cli


def add_host_key_options(cmd: list[str], args: argparse.Namespace) -> None:
    if args.accept_new_host_key:
        cmd.extend(["-o", "StrictHostKeyChecking=accept-new"])
    if args.known_hosts_file:
        cmd.extend(["-o", f"UserKnownHostsFile={args.known_hosts_file}"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute command through OpenSSH host alias")
    parser.add_argument("alias")
    parser.add_argument("command")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--accept-new-host-key", action="store_true")
    parser.add_argument("--known-hosts-file")
    parser.add_argument("--workspace", default=None)
    safety_cli.add_safety_args(parser)
    args = parser.parse_args()

    safety_cli.require_gate(
        action="ssh-exec",
        token=args.confirm_token,
        target=args.alias,
        probe=args.alias,
        voltage=args.voltage,
        current_limit=args.current_limit,
        recovery=args.recovery,
        external_loads=args.external_loads,
        artifact=args.command,
        backend="ssh",
        json_output=True,
        workspace=args.workspace,
    )

    cmd = ["ssh"]
    add_host_key_options(cmd, args)
    cmd.extend([args.alias, args.command])

    proc = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=args.timeout,
    )
    result = {
        "success": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["success"] else proc.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.TimeoutExpired as exc:
        print(json.dumps({
            "success": False,
            "exit_code": -1,
            "stdout": exc.stdout or "",
            "stderr": f"timeout after {exc.timeout}s",
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(124)
