"""Launch Hardware Agent GUI - Windows executable wrapper."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

# Launch GUI
if __name__ == "__main__":
    gui_script = REPO_ROOT / "gui" / "hardware_agent_ui.py"
    result = subprocess.run([sys.executable, str(gui_script)])
    if result.returncode != 0:
        print(f"GUI exited with code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)
