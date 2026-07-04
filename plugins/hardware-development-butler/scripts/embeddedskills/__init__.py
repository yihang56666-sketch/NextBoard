"""EmbeddedSkills Lab Operator Tools.

This package provides embedded development toolchain integration including:
- Build systems: Keil, GCC/CMake, EIDE
- Debug probes: J-Link, OpenOCD, probe-rs
- Observation: Serial, CAN, Network, RTT, SWO
"""

__version__ = "0.1.0"

from . import safety_gate

__all__ = ["safety_gate"]
