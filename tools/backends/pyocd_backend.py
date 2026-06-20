"""PyOCD hardware backend for real hardware operations.

Provides unified interface for:
- Flash programming
- Debug operations
- Memory read/write
- Target control

Supports multiple probe types: J-Link, ST-Link, CMSIS-DAP, DAPLink
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from pyocd.core.helpers import ConnectHelper
    from pyocd.flash.file_programmer import FileProgrammer
    PYOCD_AVAILABLE = True
except ImportError:
    PYOCD_AVAILABLE = False

from logger import get_logger

logger = get_logger(__name__)


@dataclass
class FlashResult:
    """Result of flash operation."""
    success: bool
    target: str
    firmware_path: str
    duration_ms: int
    error: str | None = None
    bytes_written: int = 0


@dataclass
class ProbeInfo:
    """Probe information."""
    unique_id: str
    vendor_name: str
    product_name: str
    supported_targets: list[str]


class PyOCDBackend:
    """PyOCD-based hardware backend."""

    def __init__(self, target_override: str | None = None):
        """Initialize PyOCD backend.

        Args:
            target_override: Optional target override (e.g., 'stm32f407vgtx')
        """
        if not PYOCD_AVAILABLE:
            raise RuntimeError("PyOCD not installed. Run: pip install pyocd")

        self.target_override = target_override
        logger.info("PyOCD backend initialized")

    def list_probes(self) -> list[ProbeInfo]:
        """List available debug probes.

        Returns:
            List of connected probes
        """
        probes = ConnectHelper.get_all_connected_probes()
        result = []

        for probe in probes:
            result.append(ProbeInfo(
                unique_id=probe.unique_id,
                vendor_name=probe.vendor_name,
                product_name=probe.product_name,
                supported_targets=probe.supported_target_names if hasattr(probe, 'supported_target_names') else [],
            ))

        logger.info(f"Found {len(result)} probe(s)")
        return result

    def flash(
        self,
        firmware_path: str | Path,
        target: str | None = None,
        erase: bool = True,
        verify: bool = True,
    ) -> FlashResult:
        """Flash firmware to target.

        Args:
            firmware_path: Path to firmware file (hex, bin, elf)
            target: Target MCU (e.g., 'stm32f407vgtx')
            erase: Erase before programming
            verify: Verify after programming

        Returns:
            Flash operation result
        """
        firmware_path = Path(firmware_path)
        if not firmware_path.exists():
            return FlashResult(
                success=False,
                target=target or "unknown",
                firmware_path=str(firmware_path),
                duration_ms=0,
                error=f"Firmware file not found: {firmware_path}",
            )

        target = target or self.target_override
        start_time = time.time()

        try:
            logger.info(f"Flashing {firmware_path} to {target}")

            with ConnectHelper.session_with_chosen_probe(
                target_override=target,
                auto_open=True,
            ) as session:
                # Get target info
                target_name = session.target.part_number
                logger.info(f"Connected to: {target_name}")

                # Program firmware
                programmer = FileProgrammer(
                    session,
                    chip_erase=erase,
                    trust_crc=not verify,
                )
                programmer.program(str(firmware_path))

                # Get flash size
                flash_region = session.target.memory_map.get_region_for_address(0x08000000)
                bytes_written = flash_region.length if flash_region else 0

            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(f"Flash complete in {duration_ms}ms")
            return FlashResult(
                success=True,
                target=target or target_name,
                firmware_path=str(firmware_path),
                duration_ms=duration_ms,
                bytes_written=bytes_written,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Flash failed: {e}")
            return FlashResult(
                success=False,
                target=target or "unknown",
                firmware_path=str(firmware_path),
                duration_ms=duration_ms,
                error=str(e),
            )

    def read_memory(
        self,
        address: int,
        count: int,
        target: str | None = None,
    ) -> bytes | None:
        """Read memory from target.

        Args:
            address: Memory address
            count: Number of bytes to read
            target: Target MCU

        Returns:
            Memory contents or None on error
        """
        target = target or self.target_override

        try:
            with ConnectHelper.session_with_chosen_probe(
                target_override=target
            ) as session:
                data = session.target.read_memory_block8(address, count)
                return bytes(data)

        except Exception as e:
            logger.error(f"Memory read failed: {e}")
            return None

    def reset(self, target: str | None = None) -> bool:
        """Reset target.

        Args:
            target: Target MCU

        Returns:
            True if successful
        """
        target = target or self.target_override

        try:
            with ConnectHelper.session_with_chosen_probe(
                target_override=target
            ) as session:
                session.target.reset()
                logger.info("Target reset successful")
                return True

        except Exception as e:
            logger.error(f"Reset failed: {e}")
            return False


# Convenience function for hardware_action_executor integration
def execute_flash_action(
    firmware_path: str,
    target: str,
    confirmation_token: str,
) -> dict[str, Any]:
    """Execute a real flash action — DISABLED by default (fails closed).

    Real flashing is planned-gated. This helper previously called
    ``backend.flash()`` directly with a comment claiming the caller validated
    the token, but it validated nothing and ran a real flash unconditionally.

    Real hardware flash must go through ``tools.hardware_action_executor``,
    which keeps real backends blocked until backend-specific bench validation.
    To opt in to a direct real flash (bench-validated environments only), set
    the environment variable ``HARDWARE_BUTLER_ENABLE_REAL_FLASH=1`` and pass a
    non-empty ``confirmation_token``.

    Args:
        firmware_path: Path to firmware
        target: Target MCU
        confirmation_token: Safety confirmation token (must be non-empty)

    Returns:
        Action result dict
    """
    if os.environ.get("HARDWARE_BUTLER_ENABLE_REAL_FLASH") != "1":
        return {
            "action": "flash",
            "success": False,
            "target": target,
            "firmware": firmware_path,
            "duration_ms": 0,
            "bytes_written": 0,
            "error": (
                "real flash is disabled: route through "
                "tools.hardware_action_executor, or set "
                "HARDWARE_BUTLER_ENABLE_REAL_FLASH=1 in a bench-validated "
                "environment"
            ),
        }
    if not confirmation_token:
        return {
            "action": "flash",
            "success": False,
            "target": target,
            "firmware": firmware_path,
            "duration_ms": 0,
            "bytes_written": 0,
            "error": "confirmation token required for real flash",
        }

    backend = PyOCDBackend(target_override=target)
    result = backend.flash(firmware_path, target)

    return {
        "action": "flash",
        "success": result.success,
        "target": result.target,
        "firmware": result.firmware_path,
        "duration_ms": result.duration_ms,
        "bytes_written": result.bytes_written,
        "error": result.error,
    }
