from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "cubemx-basic"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "hardware_butler.py"), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )


def run_butler_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "butler_cli.py"), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )


def test_guide_json_lists_safe_first_day_commands() -> None:
    result = run_cli("guide", "--root", str(FIXTURE), "--json")

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["schema_version"] == 1
    assert data["status"] == "ok"
    assert data["root"] == str(FIXTURE.resolve())

    command_ids = [item["id"] for item in data["first_day_commands"]]
    assert command_ids == ["doctor", "auto", "next-step", "workbench"]
    assert all(item["safe_by_default"] for item in data["first_day_commands"])
    assert not any(item["touches_hardware"] for item in data["first_day_commands"])
    assert any(item["path"] == "docs/START_HERE.md" for item in data["docs"])


def test_guide_markdown_is_human_readable() -> None:
    result = run_cli("guide", "--root", str(FIXTURE))

    assert result.returncode == 0, result.stderr
    assert "# Hardware Butler Start Guide" in result.stdout
    assert "python tools\\hardware_butler.py doctor" in result.stdout
    assert "python tools\\hardware_butler.py auto" in result.stdout
    assert "Safety Boundary" in result.stdout


def test_butler_alias_supports_guide() -> None:
    result = run_butler_cli("guide", "--root", str(FIXTURE), "--json")

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["status"] == "ok"
    assert [item["id"] for item in data["first_day_commands"]][:3] == ["doctor", "auto", "next-step"]


def test_butler_alias_forwards_guide_help() -> None:
    result = run_butler_cli("guide", "--help")

    assert result.returncode == 0, result.stderr
    assert "--root" in result.stdout
    assert "--json" in result.stdout
