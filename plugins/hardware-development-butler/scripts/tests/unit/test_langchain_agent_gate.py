"""Regression tests for natural-language hardware action safety gates."""

from __future__ import annotations

from pathlib import Path

import pytest
from backends import langchain_agent, pyocd_backend


@pytest.fixture(autouse=True)
def _pretend_langchain_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise the tool wrapper without requiring LangChain at test time."""
    monkeypatch.setattr(langchain_agent, "LANGCHAIN_AVAILABLE", True)
    monkeypatch.setattr(langchain_agent, "Tool", _Tool)


class _Tool:
    def __init__(self, *, name: str, func, description: str):
        self.name = name
        self.func = func
        self.description = description


def test_flash_tool_is_planned_gated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Natural-language FlashFirmware must not bypass hardware_action_executor."""
    called = False

    def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("direct PyOCD flash must not be called")

    monkeypatch.setattr(pyocd_backend.PyOCDBackend, "flash", fail_if_called, raising=False)
    tools = langchain_agent.HardwareButlerTools(tmp_path)

    result = tools._flash_firmware("build/app.hex,stm32f407vgtx")

    assert called is False
    assert "planned-gated" in result
    assert "hardware_action_executor" in result


def test_flash_tool_validates_parameter_shape(tmp_path: Path) -> None:
    tools = langchain_agent.HardwareButlerTools(tmp_path)

    result = tools._flash_firmware("only-one-field")

    assert "Error" in result
    assert "firmware_path,target" in result
