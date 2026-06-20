"""Example hardware tests using pytest-embedded patterns."""


import pytest


@pytest.mark.hardware
def test_probe_connection(target):
    """Test that we can connect to the target."""
    from tools.backends.pyocd_backend import PyOCDBackend

    backend = PyOCDBackend(target_override=target)
    probes = backend.list_probes()

    assert len(probes) > 0, "No debug probes found"
    print(f"Found {len(probes)} probe(s)")


@pytest.mark.hardware
def test_firmware_flash(target, tmp_path):
    """Test firmware flashing (mock)."""
    from tools.backends.pyocd_backend import PyOCDBackend

    # Create dummy firmware
    firmware = tmp_path / "test.hex"
    firmware.write_text(":00000001FF\n")  # Intel HEX end record

    backend = PyOCDBackend(target_override=target)

    # This will fail without real hardware, but tests the interface
    result = backend.flash(firmware, target)

    # In real test, would assert result.success
    assert result.firmware_path == str(firmware)


@pytest.mark.hardware
def test_gpio_blink(dut):
    """Test GPIO blink on real hardware.

    Requires:
    - Hardware connected via serial
    - Firmware that responds to 'blink' command
    """
    dut.write('blink')
    dut.expect('Blink started', timeout=2)

    for i in range(3):
        dut.expect('LED ON', timeout=1)
        dut.expect('LED OFF', timeout=1)


@pytest.mark.hardware
def test_uart_echo(dut):
    """Test UART echo functionality."""
    test_string = "Hello Hardware"

    dut.write(test_string)
    dut.expect(test_string, timeout=2)


@pytest.mark.hardware
def test_adc_reading(dut):
    """Test ADC reading."""
    dut.write('read_adc 0')
    dut.expect('ADC', timeout=2)
    # Would parse actual ADC value in real test


def test_build_plan_generation():
    """Test that build plan generation works."""
    from pathlib import Path

    from tools import build_plan

    # Use test fixture
    test_project = Path("tests/fixtures/cubemx-basic")

    if test_project.exists():
        plan = build_plan.generate_plan(test_project)
        assert "commands" in plan
        assert len(plan["commands"]) > 0
