from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_cli_safe_write_error_is_json_without_traceback() -> None:
    out = REPO_ROOT.parent / "hardware-butler-outside.json"

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "hardware_butler.py"),
            "capabilities",
            "--json",
            "--out",
            str(out),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    data = json.loads(result.stderr)
    assert data["schema_version"] == 1
    assert data["status"] == "error"
    assert data["error"]["code"] == "safe-write-denied"
    assert "Refusing to write outside allowed roots" in data["error"]["message"]
