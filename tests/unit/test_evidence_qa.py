from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import evidence_qa

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "cubemx-basic"
TMP = REPO_ROOT / "tests" / "tmp" / "evidence-qa"


def copy_fixture(name: str) -> Path:
    target = TMP / name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(FIXTURE, target)
    return target


def test_ask_pin_answers_from_cubemx_and_marks_board_connection_unknown() -> None:
    project = copy_fixture("pin")

    result = evidence_qa.answer_question(project, "PD12 接了什么？")

    assert result["status"] == "ok"
    assert result["confidence"] == "medium"
    assert "GPIO_Output" in result["answer"]
    assert "LED_GREEN" in result["answer"]
    assert any(item["path"] == "Blinky.ioc" and item["line"] != "unknown" for item in result["citations"])
    assert any("board-level connection is unknown" in item for item in result["unknowns"])


def test_ask_peripheral_answers_from_cubemx_mode() -> None:
    project = copy_fixture("peripheral")

    result = evidence_qa.answer_question(project, "USART2 是什么模式？")

    assert result["status"] == "ok"
    assert "VM_ASYNC" in result["answer"]
    assert any(item["path"] == "Blinky.ioc" and "USART2.VirtualMode" in item.get("text", "") for item in result["citations"])
    assert any("no indexed pin assignments" in item for item in result["unknowns"])


def test_ask_power_question_keeps_specific_value_unknown_without_board_evidence() -> None:
    project = copy_fixture("power")

    result = evidence_qa.answer_question(project, "CAN 收发器供电是多少？")

    assert result["status"] == "ok"
    assert result["evidence_used"]["mode"] == "project-brain"
    assert "Missing evidence" in result["answer"]
    assert any("power or voltage values are unknown" in item for item in result["unknowns"])
    assert any("schematic" in item.lower() or "bom" in item.lower() for item in result["next_checks"])


def test_ask_cli_emits_local_evidence_answer() -> None:
    project = copy_fixture("cli")

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "hardware_butler.py"),
            "ask",
            "--root",
            str(project),
            "--question",
            "PD12 接了什么？",
            "--json",
            "--no-refresh",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    data = json.loads(result.stdout)

    assert data["status"] == "ok"
    assert "GPIO_Output" in data["answer"]
    assert data["citations"]
