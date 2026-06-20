"""Append structured build/flash/debug attempts to a Markdown logbook."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import runtime_context  # noqa: E402
import safe_io  # noqa: E402


def append_entry(
    logbook: Path,
    stage: str,
    status: str,
    summary: str,
    evidence: str = "",
    next_action: str = "",
) -> None:
    safe_io.validate_write_path(logbook, allowed_roots=runtime_context.allowed_write_roots())
    timestamp = datetime.now(timezone.utc).isoformat()
    content = logbook.read_text(encoding="utf-8") if logbook.exists() else "# Debug Logbook\n\n"
    content += f"## {timestamp} - {stage} - {status}\n\n"
    content += f"**Summary:** {summary}\n\n"
    if evidence:
        content += "**Evidence:**\n\n"
        content += f"```text\n{evidence.strip()}\n```\n\n"
    if next_action:
        content += f"**Next action:** {next_action}\n\n"
    safe_io.safe_write_text(logbook, content, allowed_roots=runtime_context.allowed_write_roots())


def main() -> None:
    parser = argparse.ArgumentParser(description="Append a debug logbook entry")
    parser.add_argument("--logbook", default="docs/debug-logbook.md")
    parser.add_argument("--stage", required=True, help="build, flash, debug, observe, diagnose, fix, verify")
    parser.add_argument("--status", required=True, help="pass, fail, concern, info")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--evidence", default="")
    parser.add_argument("--next-action", default="")
    args = parser.parse_args()

    append_entry(
        Path(args.logbook),
        stage=args.stage,
        status=args.status,
        summary=args.summary,
        evidence=args.evidence,
        next_action=args.next_action,
    )


if __name__ == "__main__":
    main()
