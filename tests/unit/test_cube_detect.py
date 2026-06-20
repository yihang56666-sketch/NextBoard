"""Unit tests for cube_detect module."""

import sys

sys.path.insert(0, 'tools')
from pathlib import Path

import cube_detect


def test_detect_keil_backend(cubemx_basic_fixture: Path):
    """Should detect Keil backend."""
    result = cube_detect.detect(cubemx_basic_fixture)

    assert result["selected_backend"]["backend"] == "keil"
    assert result["has_cubemx"] is True


def test_detect_returns_mcu_from_ioc(cubemx_basic_fixture: Path):
    """Should extract MCU from .ioc file."""
    result = cube_detect.detect(cubemx_basic_fixture)

    assert result["mcu"] is not None
    assert result["ioc_path"] is not None
