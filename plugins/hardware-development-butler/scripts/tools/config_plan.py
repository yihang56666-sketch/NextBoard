"""Deprecated compatibility wrapper for config_proposal.py.

Use tools/config_proposal.py or `python tools/hardware_butler.py propose-config`.
This wrapper intentionally delegates to the hardened implementation so stale
behavior cannot keep proposing hardware action defaults.
"""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import config_proposal  # noqa: E402


def main() -> None:
    config_proposal.main()


if __name__ == "__main__":
    main()
