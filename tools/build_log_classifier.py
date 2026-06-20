"""Classify embedded build logs into actionable issue buckets."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import runtime_context  # noqa: E402
import safe_io  # noqa: E402

MAX_LOG_BYTES = 5 * 1024 * 1024


RULES: list[dict[str, Any]] = [
    {
        "category": "missing_include",
        "severity": "error",
        "patterns": [r"fatal error: .*: No such file", r"cannot open source input file", r"No such file or directory"],
        "next_action": "Check include paths, generated driver folders, and CubeMX middleware selection.",
    },
    {
        "category": "undefined_symbol",
        "severity": "error",
        "patterns": [r"undefined reference to", r"Undefined symbol", r"L6218E: Undefined symbol"],
        "next_action": "Check source file inclusion, weak callbacks, startup file, and library linkage.",
    },
    {
        "category": "multiple_definition",
        "severity": "error",
        "patterns": [r"multiple definition of", r"L6200E: Symbol .* multiply defined"],
        "next_action": "Check duplicated source files, copied CubeMX files, and global variable definitions in headers.",
    },
    {
        "category": "memory_overflow",
        "severity": "error",
        "patterns": [r"region .* overflowed", r"not enough space", r"L6406E: No space in execution regions"],
        "next_action": "Check linker script/scatter file, selected MCU flash/RAM size, and large buffers.",
    },
    {
        "category": "linker_failed",
        "severity": "error",
        "patterns": [r"ld returned \d+ exit status", r"linker command failed", r"L\d+E:"],
        "next_action": "Inspect earlier linker diagnostics first; this line is usually a summary, not the root cause.",
    },
    {
        "category": "syntax_or_type",
        "severity": "error",
        "patterns": [r"\berror:", r"#\d+: error", r"syntax error", r"expected .* before"],
        "next_action": "Inspect the first compiler error before later cascade errors.",
    },
    {
        "category": "warning",
        "severity": "warning",
        "patterns": [r"\bwarning:", r"#\d+: warning", r"Warning:"],
        "next_action": "Review warnings that affect initialization, integer conversion, or unused error returns.",
    },
]


def read_log(path: Path) -> str:
    size = path.stat().st_size
    if size > MAX_LOG_BYTES:
        raise ValueError(f"Log file too large: {size} bytes; limit is {MAX_LOG_BYTES} bytes.")
    return path.read_text(encoding="utf-8", errors="replace")


def classify_text(text: str) -> dict[str, Any]:
    findings = []
    lines = text.splitlines()
    for idx, line in enumerate(lines, 1):
        for rule in RULES:
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in rule["patterns"]):
                findings.append(
                    {
                        "line": idx,
                        "category": rule["category"],
                        "severity": rule["severity"],
                        "message": line.strip(),
                        "next_action": rule["next_action"],
                    }
                )
                break

    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding["category"]] = counts.get(finding["category"], 0) + 1

    return {
        "schema_version": 1,
        "status": "error" if any(f["severity"] == "error" for f in findings) else "ok",
        "finding_count": len(findings),
        "category_counts": dict(sorted(counts.items())),
        "findings": findings[:200],
    }


def render_markdown(data: dict[str, Any]) -> str:
    lines = ["# Build Log Classification", "", f"- Status: `{data['status']}`", f"- Findings: {data['finding_count']}", ""]
    lines.append("## Category Counts")
    lines.append("")
    if data["category_counts"]:
        for category, count in data["category_counts"].items():
            lines.append(f"- {category}: {count}")
    else:
        lines.append("- no issues detected")
    lines.extend(["", "## Findings", ""])
    for finding in data["findings"]:
        lines.append(f"- Line {finding['line']} [{finding['severity']}/{finding['category']}]: `{finding['message']}`")
        lines.append(f"  Next: {finding['next_action']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify embedded build logs")
    parser.add_argument("log", help="Path to build log")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    try:
        text = read_log(Path(args.log))
    except (OSError, ValueError) as exc:
        print(json.dumps({"schema_version": 1, "status": "error", "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(2)
    data = classify_text(text)
    content = json.dumps(data, ensure_ascii=False, indent=2) if args.as_json and not args.markdown else render_markdown(data)
    if args.out:
        safe_io.safe_write_text(Path(args.out), content, allowed_roots=runtime_context.allowed_write_roots())
    else:
        print(content)


if __name__ == "__main__":
    main()
