"""Evidence-backed chip manual summarizer.

The summarizer is conservative: it extracts source lines from text or PDF
manuals, groups them under bring-up categories, and marks absent categories as
unknown instead of inventing electrical values.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import runtime_context  # noqa: E402
import safe_io  # noqa: E402

CATEGORIES = {
    "power": ["vdd", "vdda", "voltage", "supply", "power", "regulator"],
    "clock": ["hse", "lse", "pll", "oscillator", "clock", "crystal"],
    "reset_boot": ["reset", "boot", "boot0", "nreset", "nrst"],
    "debug": ["swd", "jtag", "debug", "trace", "programming"],
    "memory": ["flash", "sram", "memory", "eeprom"],
    "peripherals": ["i2c", "spi", "usart", "uart", "can", "adc", "timer", "pwm", "usb"],
    "electrical_limits": [
        "absolute maximum",
        "maximum rating",
        "gpio",
        "current",
        "injection",
        "source current",
        "sink current",
    ],
    "errata": ["errata", "limitation", "workaround", "silicon"],
}


def summarize_documents(part: str, paths: list[Path]) -> dict[str, Any]:
    docs = [read_text_document(path, index=index) for index, path in enumerate(paths, start=1)]
    combined_lines = []
    for doc in docs:
        combined_lines.extend(doc["lines"])
    sections = {name: collect_evidence(combined_lines, keywords) for name, keywords in CATEGORIES.items()}
    return {
        "schema_version": 1,
        "status": "ok",
        "part": part,
        "documents": [
            {
                "document_id": item["document_id"],
                "document_type": item["document_type"],
                "path": item["path"],
                "line_count": len(item["lines"]),
            }
            for item in docs
        ],
        "sections": sections,
        "unknown": [name for name, evidence in sections.items() if not evidence],
        "rules": [
            "Only source text snippets are summarized.",
            "Missing categories remain unknown.",
            "Verify electrical limits against the official datasheet before hardware action.",
        ],
    }


def read_text_document(path: Path, *, index: int = 1) -> dict[str, Any]:
    path = path.resolve()
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = extract_pdf_text(path)
    elif suffix in {".txt", ".md", ".log"}:
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        raise ValueError(f"Manual summary accepts .pdf or extracted text files only: {path}")
    document_id = f"doc-{index:02d}-{re.sub(r'[^A-Za-z0-9_.-]+', '-', path.stem)[:48]}"
    raw_pages = text.split("\f")
    line_records: list[dict[str, Any]] = []
    global_line = 0
    for page_index, page_text in enumerate(raw_pages, start=1):
        for raw_line in page_text.splitlines():
            line = normalize_line(raw_line)
            if not line:
                continue
            global_line += 1
            line_records.append(
                {
                    "document_id": document_id,
                    "document_type": "pdf" if suffix == ".pdf" else "text",
                    "path": str(path),
                    "page": page_index,
                    "line": global_line,
                    "text": line,
                }
            )
    return {
        "document_id": document_id,
        "document_type": "pdf" if suffix == ".pdf" else "text",
        "path": str(path),
        "lines": line_records,
    }


def extract_pdf_text(path: Path) -> str:
    exe = shutil.which("pdftotext")
    if exe:
        proc = subprocess.run(
            [exe, "-layout", str(path), "-"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout
    return fallback_pdf_text(path.read_bytes())


def fallback_pdf_text(data: bytes) -> str:
    text = data.decode("latin-1", errors="ignore")
    chunks = re.findall(r"[\x20-\x7E]{4,}", text)
    return "\n".join(chunks)


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def collect_evidence(lines: list[dict[str, Any]], keywords: list[str], *, limit: int = 5) -> list[dict[str, Any]]:
    evidence = []
    seen = set()
    for item in lines:
        line = item["text"]
        lower = line.lower()
        if not any(keyword.lower() in lower for keyword in keywords):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        evidence.append(
            {
                "document_id": item["document_id"],
                "document_type": item["document_type"],
                "page": item["page"],
                "line": item["line"],
                "text": line,
            }
        )
        if len(evidence) >= limit:
            break
    return evidence


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Manual Summary",
        "",
        f"- Part: `{summary['part']}`",
        f"- Status: `{summary['status']}`",
        "",
        "## Documents",
        "",
    ]
    for item in summary["documents"]:
        lines.append(f"- `{item['document_id']}` `{item['path']}` ({item['line_count']} lines)")
    lines.extend(["", "## Quick Bring-Up Evidence", ""])
    for section, evidence in summary["sections"].items():
        lines.append(f"### {section}")
        lines.append("")
        if evidence:
            for item in evidence:
                lines.append(f"- {item['document_id']} page {item['page']} line {item['line']}: {item['text']}")
        else:
            lines.append("- unknown")
        lines.append("")
    lines.extend(["## Rules", ""])
    for item in summary["rules"]:
        lines.append(f"- {item}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize extracted chip manual text or PDF")
    parser.add_argument("--part", required=True)
    parser.add_argument("--document", action="append", required=True)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    summary = summarize_documents(args.part, [Path(item) for item in args.document])
    content = json.dumps(summary, ensure_ascii=False, indent=2) if args.as_json else render_markdown(summary)
    if args.out:
        safe_io.safe_write_text(Path(args.out), content, allowed_roots=runtime_context.allowed_write_roots())
    else:
        print(content)


if __name__ == "__main__":
    main()
