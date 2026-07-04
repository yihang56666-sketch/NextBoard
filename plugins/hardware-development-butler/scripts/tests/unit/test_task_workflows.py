from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import task_workflows

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "cubemx-basic"


def test_collect_evidence_plan_includes_chip_dossier_preset() -> None:
    plan = task_workflows.build_task_plan(FIXTURE, "collect-evidence", part="STM32F407VGTx")

    assert plan["status"] == "ready"
    assert plan["intent"]["id"] == "collect-evidence"
    chip_step = next(item for item in plan["steps"] if item["id"] == "chip-dossier")
    assert "--api-preset" in chip_step["argv"]
    assert "chip-docs" in chip_step["argv"]
    assert all(item["safe_by_default"] for item in plan["steps"])
    assert all(item["touches_hardware"] is False for item in plan["steps"])


def test_configure_peripheral_reports_missing_pin_for_gpio() -> None:
    plan = task_workflows.build_task_plan(FIXTURE, "configure-peripheral", function="gpio-output")

    assert plan["status"] == "needs-input"
    assert "pin" in plan["missing_inputs"]
    assert any(item["id"] == "firmware-plan" for item in plan["steps"])


def test_configure_peripheral_accepts_instance_for_bus_peripheral() -> None:
    plan = task_workflows.build_task_plan(FIXTURE, "configure-peripheral", function="i2c", instance="I2C1")

    assert plan["status"] == "ready"
    assert plan["missing_inputs"] == []
    assert [item["id"] for item in plan["steps"]] == ["brain", "firmware-plan"]


def test_task_cli_emits_safe_prepare_bringup_plan() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "hardware_butler.py"),
            "task",
            "--root",
            str(FIXTURE),
            "--intent",
            "prepare-bringup",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    data = json.loads(result.stdout)

    assert data["status"] == "ready"
    assert data["safety"]["real_hardware_actions"] == "planned-gated"
    assert {item["id"] for item in data["steps"]} >= {"brain", "bench-runbook", "plan-action"}
    assert all(item["touches_hardware"] is False for item in data["steps"])
