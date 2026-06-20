"""Hardware Butler Core Tools.

This package provides the core functionality for hardware development management,
including project inspection, chip documentation, CubeMX configuration, and
firmware integration.
"""

__version__ = "0.1.0"
__author__ = "Hardware Butler Team"

# Core modules
from . import runtime_context, safe_io

__all__ = [
    "runtime_context",
    "safe_io",
]
