"""Regression tests for value-safety enforcement across the butler paths.

The planner refuses to mint a token for physically-impossible safety values,
and the executor re-checks at execution time (defense in depth) so a
hand-crafted plan carrying a self-computed token is still refused.
"""

from __future__ import annotations

from pathlib import Path

import hardware_action_executor
import hardware_action_plan


def test_plan_blocks_unsafe_voltage_and_mints_no_token(tmp_path: Path) -> None:
    plan = hardware_action_plan.plan_action(
        tmp_path,
        action="flash",
        target="stm32f407vgtx",
        probe="stlink",
        voltage="999",
        current_limit="100mA",
        erase_scope="firmware image only",
        recovery="boot0 reset",
    )
    assert plan["status"] == "blocked-unsafe-safety-value"
    assert plan["confirmation_token"] == ""
    assert plan["value_safety"]["blocks"]


def test_plan_warns_on_high_current_but_issues_token(tmp_path: Path) -> None:
    plan = hardware_action_plan.plan_action(
        tmp_path,
        action="flash",
        target="stm32f407vgtx",
        probe="stlink",
        voltage="3.3V",
        current_limit="2A",
        erase_scope="firmware image only",
        recovery="boot0 reset",
    )
    assert plan["status"] == "ready-for-user-confirmation"
    assert plan["confirmation_token"]
    assert plan["value_safety"]["warnings"]


def test_executor_blocks_handcrafted_plan_with_unsafe_value(tmp_path: Path) -> None:
    """A plan with an impossible value plus a matching token is still refused."""
    record = {
        "root": str(tmp_path),
        "target": "stm32f407vgtx",
        "probe": "stlink",
        "voltage": "999",
        "current_limit": "100mA",
        "erase_scope": "firmware image only",
        "recovery": "boot0 reset",
        "external_loads": "unknown",
        "artifact": "",
        "artifact_hash": "",
        "backend": "fake",
    }
    token = hardware_action_plan.confirmation_token("flash", record)
    plan = {
        "schema_version": 1,
        "action": "flash",
        "root": str(tmp_path),
        "hardware_side_effect": True,
        "confirmation_record": record,
        "confirmation_token": token,
    }
    result = hardware_action_executor.execute_plan(plan, token=token, backend="fake")
    assert result["status"] == "blocked-unsafe-safety-value"
    assert result["executed"] is False
