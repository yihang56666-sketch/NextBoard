"""Regression tests for the pyocd backend real-flash gate.

``execute_flash_action`` previously accepted a ``confirmation_token`` argument
but ignored it and ran a real flash unconditionally (fail-open). It must now
fail closed unless explicitly enabled in a bench-validated environment.
"""

from __future__ import annotations

import pytest
from backends.pyocd_backend import execute_flash_action


@pytest.fixture(autouse=True)
def _real_flash_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the real-flash enable flag is unset for every test."""
    monkeypatch.delenv("HARDWARE_BUTLER_ENABLE_REAL_FLASH", raising=False)


def test_execute_flash_action_disabled_by_default() -> None:
    """Without the enable flag, real flash must be refused."""
    result = execute_flash_action("fw.hex", "stm32f407vgtx", "hwc1-faketoken")

    assert result["success"] is False
    assert "disabled" in result["error"]
    assert "hardware_action_executor" in result["error"]


def test_execute_flash_action_requires_token_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even with the enable flag, an empty token must be refused."""
    monkeypatch.setenv("HARDWARE_BUTLER_ENABLE_REAL_FLASH", "1")

    result = execute_flash_action("fw.hex", "stm32f407vgtx", "")

    assert result["success"] is False
    assert "token required" in result["error"]
