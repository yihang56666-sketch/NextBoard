"""Run the packaged hardware butler CLI from a skill invocation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    skill_dir = Path(__file__).resolve().parents[1]
    plugin_root = skill_dir.parents[1]
    runtime_root = plugin_root / "scripts"
    cli = runtime_root / "tools" / "hardware_butler.py"
    if not cli.exists():
        print(f"hardware_butler.py not found: {cli}", file=sys.stderr)
        return 2

    env = os.environ.copy()
    env.setdefault("HARDWARE_BUTLER_WORKSPACE_ROOT", str(Path.cwd().resolve()))
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return subprocess.call([sys.executable, str(cli), *sys.argv[1:]], cwd=runtime_root, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
