"""Auto-discovered fixtures for the test suite.

pytest only auto-loads files named ``conftest.py``. The hardware-bench
fixtures used to live in ``tests/conftest_hardware.py``, which pytest never
imported, so ``--run-hardware`` runs errored with "fixture 'target' not
found". They now live here so they are registered for every test under
``tests/``. The matching ``--target`` / ``--port`` options are declared in the
rootdir ``conftest.py`` (the only place ``pytest_addoption`` is honoured).
"""

from __future__ import annotations

import time

import pytest


@pytest.fixture
def target(request: pytest.FixtureRequest) -> str:
    """Target MCU for hardware tests."""
    return request.config.getoption("--target")


@pytest.fixture
def serial_port(request: pytest.FixtureRequest) -> str | None:
    """Serial port for hardware communication."""
    return request.config.getoption("--port")


@pytest.fixture
def dut(serial_port: str | None):
    """Device Under Test fixture.

    Yields a real serial-backed DUT when ``--port`` is supplied, otherwise a
    mock DUT so interface-level tests run without hardware. Skips when
    pyserial is not installed.
    """
    try:
        import serial
    except ImportError:
        pytest.skip("pyserial not installed")
        return

    if not serial_port:
        class MockDUT:
            def write(self, data: str) -> None:
                print(f"[MOCK] Write: {data}")

            def expect(self, pattern: str, timeout: float = 5) -> bool:
                print(f"[MOCK] Expect: {pattern}")
                return True

        yield MockDUT()
        return

    ser = serial.Serial(serial_port, 115200, timeout=1)

    class DUT:
        def write(self, data: str) -> None:
            ser.write(data.encode() + b"\n")

        def expect(self, pattern: str, timeout: float = 5) -> bool:
            start = time.time()
            buffer = b""
            while time.time() - start < timeout:
                if ser.in_waiting:
                    buffer += ser.read(ser.in_waiting)
                    if pattern.encode() in buffer:
                        return True
                time.sleep(0.1)
            raise TimeoutError(f"Expected '{pattern}' not found")

        def close(self) -> None:
            ser.close()

    dut_obj = DUT()
    try:
        yield dut_obj
    finally:
        dut_obj.close()
