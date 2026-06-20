"""Tests for the value-sanity (防呆) layer in safety_gate.

The confirmation gate historically only checked that safety fields were
*present* (non-empty). It never checked the *values* were physically sane, so
``voltage="999"``, ``current_limit="abc"``, or an accidental full-chip erase
all passed silently. ``evaluate_value_safety`` adds an automated mistake-
prevention layer: it blocks physically-impossible values and warns loudly on
valid-but-risky ones, without rejecting any legitimate flow.
"""

from __future__ import annotations

import pytest
import safety_gate

# --- low-level parsers -----------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("3.3V", 3.3),
        ("3.3 V", 3.3),
        ("1.8v", 1.8),
        ("5", 5.0),
        ("3V3", 3.3),  # EE engineering notation
        ("1V8", 1.8),
        ("3.3 volts", 3.3),
        ("", None),
        ("abc", None),
        ("NaN", None),
    ],
)
def test_parse_voltage(text: str, expected: float | None) -> None:
    assert safety_gate.parse_voltage(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("100mA", 100.0),
        ("100 mA", 100.0),
        ("0.1A", 100.0),
        ("1A", 1000.0),
        ("500", 500.0),  # bare number assumed mA
        ("", None),
        ("abc", None),
    ],
)
def test_parse_current_ma(text: str, expected: float | None) -> None:
    assert safety_gate.parse_current_ma(text) == expected


# --- whole-record evaluation ----------------------------------------------


def _record(**overrides: str) -> dict[str, str]:
    base = {
        "target": "stm32f407vgtx",
        "probe": "stlink",
        "voltage": "3.3V",
        "current_limit": "100mA",
        "erase_scope": "firmware image only",
        "recovery": "boot0 reset",
    }
    base.update(overrides)
    return base


def test_known_good_values_are_safe() -> None:
    result = safety_gate.evaluate_value_safety("flash", _record())
    assert result["safe"] is True
    assert result["blocks"] == []
    assert result["warnings"] == []


@pytest.mark.parametrize("bad", ["999", "12V", "0V", "-1V", "abc"])
def test_impossible_voltage_blocks(bad: str) -> None:
    result = safety_gate.evaluate_value_safety("flash", _record(voltage=bad))
    assert result["safe"] is False
    assert any("voltage" in b.lower() for b in result["blocks"])


@pytest.mark.parametrize("warn_v", ["5V", "4.5V"])
def test_elevated_voltage_warns_but_allows(warn_v: str) -> None:
    result = safety_gate.evaluate_value_safety("flash", _record(voltage=warn_v))
    assert result["safe"] is True
    assert any("voltage" in w.lower() for w in result["warnings"])


@pytest.mark.parametrize("bad", ["abc", "0mA", "-5mA"])
def test_impossible_current_blocks(bad: str) -> None:
    result = safety_gate.evaluate_value_safety("flash", _record(current_limit=bad))
    assert result["safe"] is False
    assert any("current" in b.lower() for b in result["blocks"])


def test_high_current_warns_but_allows() -> None:
    result = safety_gate.evaluate_value_safety("flash", _record(current_limit="2A"))
    assert result["safe"] is True
    assert any("current" in w.lower() for w in result["warnings"])


@pytest.mark.parametrize(
    "scope",
    ["mass erase", "full chip erase", "whole chip", "erase all sectors", "option byte", "整片擦除", "全片擦除"],
)
def test_destructive_erase_scope_warns(scope: str) -> None:
    result = safety_gate.evaluate_value_safety("erase", _record(erase_scope=scope))
    # Destructive but sometimes legitimate (recovery/unlock): warn, never block.
    assert result["safe"] is True
    assert any("erase" in w.lower() for w in result["warnings"])


def test_value_safety_ignores_non_hardware_action() -> None:
    result = safety_gate.evaluate_value_safety("info", _record(voltage="999"))
    assert result["safe"] is True
    assert result["blocks"] == []


def test_check_token_blocks_unsafe_voltage() -> None:
    """An impossible voltage must be refused by the gate even with a valid token."""
    record = _record(voltage="999")
    token = safety_gate.confirmation_token("flash", record)
    gate = safety_gate.check_token("flash", token, **record)
    assert gate["allowed"] is False
    assert gate.get("error_code") == "unsafe_value"


def test_check_token_surfaces_warnings_without_blocking() -> None:
    record = _record(current_limit="2A")
    token = safety_gate.confirmation_token("flash", record)
    gate = safety_gate.check_token("flash", token, **record)
    assert gate["allowed"] is True
    assert gate.get("warnings")
