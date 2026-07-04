#!/usr/bin/env python3
import argparse
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
    parser = argparse.ArgumentParser(description="Start foreground OpenSSH local port forwarding")
    parser.add_argument("alias")
    parser.add_argument("--local-port", required=True)
    parser.add_argument("--remote-host", default="127.0.0.1")
    parser.add_argument("--remote-port", required=True)
    parser.add_argument("--accept-new-host-key", action="store_true")
    parser.add_argument("--known-hosts-file")
    parser.add_argument("--workspace", default=None)
    safety_cli.add_safety_args(parser)
    args = parser.parse_args()

    target = f"127.0.0.1:{args.local_port}:{args.remote_host}:{args.remote_port}"
    safety_cli.require_gate(
        action="ssh-tunnel",
        token=args.confirm_token,
        target=args.alias,
        probe=args.alias,
        voltage=args.voltage,
        current_limit=args.current_limit,
        recovery=args.recovery,
        external_loads=args.external_loads,
        artifact=target,
        backend="ssh",
        json_output=True,
        workspace=args.workspace,
    )
    cmd = ["ssh"]
    add_host_key_options(cmd, args)
    cmd.extend(["-N", "-L", target, args.alias])
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
