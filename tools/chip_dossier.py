"""Create chip document dossiers and manual-summary skeletons.

This module is intentionally conservative: it records source URLs and creates a
stable dossier layout. It does not pretend that URLs were downloaded unless a
caller explicitly downloads and validates a PDF later.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict, cast


class SourceResponse(TypedDict):
    data: bytes
    final_url: str
    http_status: str
    content_type: str
    etag: str
    last_modified: str

try:
    from butler_types import ChipDossier, DocumentRecord
except ImportError:
    ChipDossier = dict  # type: ignore
    DocumentRecord = dict  # type: ignore
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, url2pathname, urlopen

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import document_providers  # noqa: E402
import manual_summarizer  # noqa: E402
import runtime_context  # noqa: E402
import safe_io  # noqa: E402
from cache import get_default_cache  # noqa: E402

# Initialize cache
_cache = get_default_cache("chip-dossier")


DOCUMENT_PATTERNS = [
    ("reference_manual", ("reference_manual", "reference-manual", "rm", "manual")),
    ("programming_manual", ("programming_manual", "programming-manual", "pm")),
    ("datasheet", ("datasheet", "data-sheet", "ds")),
    ("errata", ("errata", "es")),
    ("application_note", ("application_note", "application-note", "an")),
    ("schematic", ("schematic", "sch")),
    ("board_manual", ("user_manual", "user-manual", "board-manual", "board_manual")),
]
MAX_PDF_BYTES = 50 * 1024 * 1024


def normalize_part(part: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", part.strip())
    return cleaned.strip("-") or "unknown-part"


def classify_source(url: str) -> str:
    text = url.lower()
    for kind, markers in DOCUMENT_PATTERNS:
        if any(marker in text for marker in markers):
            return kind
    if text.endswith(".pdf"):
        return "pdf"
    return "source"


def create_dossier(part: str, out_dir: Path, *, board: str = "", sources: list[str] | None = None) -> ChipDossier:
    part = normalize_part(part)
    out_dir = out_dir.resolve()
    documents_dir = out_dir / "documents"
    safe_io.validate_write_path(out_dir, allowed_roots=runtime_context.allowed_write_roots())
    documents_dir.mkdir(parents=True, exist_ok=True)

    source_records = [source_record(item) for item in (sources or [])]
    data = {
        "schema_version": 1,
        "status": "ok",
        "part": part,
        "board": board,
        "out_dir": str(out_dir),
        "documents_dir": str(documents_dir),
        "documents": source_records,
        "required_documents": required_documents(),
        "document_coverage": document_coverage(source_records),
        "provider_search_hints": document_providers.search_hints(part),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    written = {
        "source_map": safe_io.safe_write_text(
            out_dir / "source-map.md",
            render_source_map(data),
            allowed_roots=runtime_context.allowed_write_roots(),
        ),
        "manual_summary": safe_io.safe_write_text(
            out_dir / "manual-summary.md",
            render_manual_summary_skeleton(data),
            allowed_roots=runtime_context.allowed_write_roots(),
        ),
        "cubemx_config": safe_io.safe_write_text(
            out_dir / "cubemx-config.md",
            render_cubemx_config_skeleton(data),
            allowed_roots=runtime_context.allowed_write_roots(),
        ),
        "safety_checklist": safe_io.safe_write_text(
            out_dir / "safety-checklist.md",
            render_safety_checklist(data),
            allowed_roots=runtime_context.allowed_write_roots(),
        ),
        "document_coverage_json": safe_io.safe_write_text(
            out_dir / "document-coverage.json",
            json.dumps(data["document_coverage"], ensure_ascii=False, indent=2),
            allowed_roots=runtime_context.allowed_write_roots(),
        ),
        "document_coverage_md": safe_io.safe_write_text(
            out_dir / "document-coverage.md",
            render_document_coverage(data["document_coverage"]),
            allowed_roots=runtime_context.allowed_write_roots(),
        ),
        "dossier_json": safe_io.safe_write_text(
            out_dir / "chip-dossier.json",
            json.dumps(data, ensure_ascii=False, indent=2),
            allowed_roots=runtime_context.allowed_write_roots(),
        ),
    }
    data["written"] = written
    return data


def discover_sources(part: str, search_sources: list[str], *, timeout_s: int = 20) -> dict[str, Any]:
    records = []
    seen = set()
    for source in search_sources:
        for url in extract_pdf_links(source, timeout_s=timeout_s):
            key = url.lower()
            if key in seen:
                continue
            seen.add(key)
            if source_matches_part(part, url):
                records.append(source_record(url))
    result: dict[str, Any] = {
        "schema_version": 1,
        "part": normalize_part(part),
        "status": "ok",
        "search_sources": search_sources,
        "documents": records,
    }
    return result


def extract_pdf_links(source: str, *, timeout_s: int) -> list[str]:
    urlparse(source)
    if source.lower().endswith(".pdf"):
        return [source]
    try:
        data = read_source_bytes(source, timeout_s=timeout_s)
    except OSError:
        return []
    text = data.decode("utf-8", errors="replace")
    links = re.findall(r"""href=["']([^"']+\.pdf(?:\?[^"']*)?)["']""", text, flags=re.IGNORECASE)
    bare_links = re.findall(r"""https?://[^\s"'<>]+\.pdf(?:\?[^\s"'<>]*)?""", text, flags=re.IGNORECASE)
    return [urljoin(source, item) for item in [*links, *bare_links]]


def source_matches_part(part: str, url: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "", part.lower())
    haystack = re.sub(r"[^a-z0-9]+", "", unquote(url).lower())
    if normalized and normalized in haystack:
        return True
    family = re.match(r"([a-z]+\d+[a-z]?\d*)", normalized)
    return bool(family and family.group(1) in haystack)


def vendor_search_hints(part: str) -> list[str]:
    return [item["url"] for item in document_providers.search_hints(part)]


def download_documents(
    part: str,
    out_dir: Path,
    *,
    sources: list[str],
    board: str = "",
    timeout_s: int = 20,
    extract_text: bool = True,
) -> dict[str, Any]:
    dossier = create_dossier(part, out_dir, board=board, sources=sources)
    documents_dir = Path(dossier["documents_dir"])
    results = []
    for source in sources:
        results.append(download_one(source, documents_dir, timeout_s=timeout_s))
    dossier["download_results"] = results
    dossier["documents"] = merge_download_results(dossier["documents"], results)
    dossier["document_coverage"] = document_coverage(dossier["documents"])
    safe_io.safe_write_text(
        out_dir / "source-map.md",
        render_source_map(dossier),
        allowed_roots=runtime_context.allowed_write_roots(),
    )
    safe_io.safe_write_text(
        out_dir / "document-coverage.json",
        json.dumps(dossier["document_coverage"], ensure_ascii=False, indent=2),
        allowed_roots=runtime_context.allowed_write_roots(),
    )
    safe_io.safe_write_text(
        out_dir / "document-coverage.md",
        render_document_coverage(dossier["document_coverage"]),
        allowed_roots=runtime_context.allowed_write_roots(),
    )
    safe_io.safe_write_text(
        out_dir / "chip-dossier.json",
        json.dumps(dossier, ensure_ascii=False, indent=2),
        allowed_roots=runtime_context.allowed_write_roots(),
    )
    if extract_text:
        write_downloaded_manual_summary(dossier, out_dir)
    return cast(dict[str, Any], dossier)


def search_and_download_documents(
    part: str,
    out_dir: Path,
    *,
    search_sources: list[str],
    board: str = "",
    timeout_s: int = 20,
) -> dict[str, Any]:
    effective_search_sources = search_sources or vendor_search_hints(part)
    discovered = discover_sources(part, effective_search_sources, timeout_s=timeout_s)
    discovered["auto_search"] = not bool(search_sources)
    sources = [item["url"] for item in discovered["documents"]]
    if not sources:
        dossier = create_dossier(part, out_dir, board=board, sources=[])
        dossier["status"] = "no-documents-discovered"
        dossier["search"] = discovered
        dossier["vendor_search_hints"] = vendor_search_hints(part)
        dossier["provider_search_hints"] = document_providers.search_hints(part)
        dossier["document_coverage"] = document_coverage(dossier["documents"])
        safe_io.safe_write_text(
            out_dir / "source-map.md",
            render_source_map(dossier),
            allowed_roots=runtime_context.allowed_write_roots(),
        )
        safe_io.safe_write_text(
            out_dir / "document-coverage.json",
            json.dumps(dossier["document_coverage"], ensure_ascii=False, indent=2),
            allowed_roots=runtime_context.allowed_write_roots(),
        )
        safe_io.safe_write_text(
            out_dir / "document-coverage.md",
            render_document_coverage(dossier["document_coverage"]),
            allowed_roots=runtime_context.allowed_write_roots(),
        )
        return cast(dict[str, Any], dossier)
    dossier = download_documents(part, out_dir, board=board, sources=sources, timeout_s=timeout_s, extract_text=True)
    dossier["search"] = discovered
    return dossier


def write_downloaded_manual_summary(dossier: dict[str, Any], out_dir: Path) -> None:
    paths = [
        Path(item["saved_path"])
        for item in dossier.get("download_results", [])
        if item.get("status") == "downloaded" and item.get("saved_path")
    ]
    if not paths:
        return
    summary = manual_summarizer.summarize_documents(dossier["part"], paths)
    dossier["manual_summary"] = summary
    extracted_dir = out_dir / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        text = manual_summarizer.extract_pdf_text(path)
        safe_io.safe_write_text(
            extracted_dir / f"{path.stem}.txt",
            text,
            allowed_roots=runtime_context.allowed_write_roots(),
        )
    safe_io.safe_write_text(
        out_dir / "manual-summary.md",
        manual_summarizer.render_markdown(summary),
        allowed_roots=runtime_context.allowed_write_roots(),
    )
    safe_io.safe_write_text(
        out_dir / "manual-summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2),
        allowed_roots=runtime_context.allowed_write_roots(),
    )
    safe_io.safe_write_text(
        out_dir / "chip-dossier.json",
        json.dumps(dossier, ensure_ascii=False, indent=2),
        allowed_roots=runtime_context.allowed_write_roots(),
    )


def download_one(source: str, documents_dir: Path, *, timeout_s: int) -> dict[str, Any]:
    try:
        response = read_source_response(source, timeout_s=timeout_s)
        data = response["data"]
    except OSError as exc:
        return {**source_record(source), "status": "error", "error": str(exc), "saved_path": ""}
    metadata = {key: value for key, value in response.items() if key != "data"}
    provider = document_providers.infer_provider(str(metadata.get("final_url") or source))
    digest = hashlib.sha256(data).hexdigest()
    if len(data) > MAX_PDF_BYTES:
        return {
            **source_record(source),
            **metadata,
            **provider,
            "url": source,
            "status": "rejected-too-large",
            "error": f"document exceeds maximum allowed size: {MAX_PDF_BYTES} bytes",
            "saved_path": "",
            "size_bytes": len(data),
            "sha256": digest,
        }
    if not looks_like_pdf(data):
        return {
            **source_record(source),
            **metadata,
            **provider,
            "url": source,
            "status": "rejected-non-pdf",
            "error": "response does not start with a PDF header",
            "saved_path": "",
            "size_bytes": len(data),
            "sha256": digest,
        }
    filename = safe_pdf_filename(source)
    saved = safe_io.safe_write_bytes(
        documents_dir / filename,
        data,
        allowed_roots=runtime_context.allowed_write_roots(),
    )
    record = source_record(source)
    return {
        **record,
        **metadata,
        **provider,
        "status": "downloaded",
        "download_status": "downloaded",
        "error": "",
        "saved_path": saved,
        "size_bytes": len(data),
        "sha256": digest,
    }


def read_source_response(source: str, *, timeout_s: int) -> SourceResponse:
    parsed = urlparse(source)
    if parsed.scheme == "file":
        path = Path(url2pathname(unquote(parsed.path))).resolve()
        data = path.read_bytes()
        return {
            "data": data,
            "final_url": path.as_uri(),
            "http_status": "",
            "content_type": "application/pdf" if path.suffix.lower() == ".pdf" else "application/octet-stream",
            "etag": "",
            "last_modified": "",
        }
    if parsed.scheme in {"http", "https"}:
        request = Request(source, headers={"User-Agent": "hardware-butler/0.1"})
        with urlopen(request, timeout=timeout_s) as response:  # noqa: S310 - user-provided docs download
            data = response.read(MAX_PDF_BYTES + 1)
            if len(data) > MAX_PDF_BYTES:
                raise OSError(f"Document exceeds maximum allowed size: {MAX_PDF_BYTES} bytes")
            headers = response.headers
            return {
                "data": data,
                "final_url": response.geturl(),
                "http_status": str(getattr(response, "status", response.getcode())),
                "content_type": headers.get("Content-Type", ""),
                "etag": headers.get("ETag", ""),
                "last_modified": headers.get("Last-Modified", ""),
            }
    path = Path(source)
    if path.exists():
        resolved = path.resolve()
        data = resolved.read_bytes()
        return {
            "data": data,
            "final_url": str(resolved),
            "http_status": "",
            "content_type": "application/pdf" if resolved.suffix.lower() == ".pdf" else "application/octet-stream",
            "etag": "",
            "last_modified": "",
        }
    raise OSError(f"Unsupported or missing source: {source}")


def read_source_bytes(source: str, *, timeout_s: int) -> bytes:
    response = read_source_response(source, timeout_s=timeout_s)
    return response["data"]


def looks_like_pdf(data: bytes) -> bool:
    if not data.startswith(b"%PDF"):
        return False
    tail = data[-2048:] if len(data) > 2048 else data
    return b"%%EOF" in tail


def safe_pdf_filename(source: str) -> str:
    parsed = urlparse(source)
    name = Path(unquote(parsed.path)).name if parsed.path else ""
    if not name.lower().endswith(".pdf"):
        name = f"{classify_source(source)}.pdf"
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", name) or "document.pdf"


def merge_download_results(records: list[dict[str, str]], results: list[dict[str, Any]]) -> list[dict[str, str]]:
    by_url = {item["url"]: item for item in results}
    merged = []
    for record in records:
        result = by_url.get(record["url"])
        if result:
            updated = dict(record)
            for key, value in result.items():
                if key != "data":
                    updated[key] = value
            updated["download_status"] = result["status"]
            updated["notes"] = result.get("error", "") or record["notes"]
            merged.append(updated)
        else:
            merged.append(record)
    return merged


def source_record(url: str) -> dict[str, str]:
    parsed = urlparse(url)
    provider = document_providers.infer_provider(url)
    return {
        "document_id": document_id(url),
        "url": url,
        "final_url": "",
        "host": parsed.netloc,
        "document_type": classify_source(url),
        "provider": provider["provider"],
        "vendor": provider["vendor"],
        "source_quality": provider["source_quality"],
        "status": "source-recorded",
        "download_status": "not-downloaded",
        "http_status": "",
        "content_type": "",
        "etag": "",
        "last_modified": "",
        "size_bytes": "",
        "sha256": "",
        "saved_path": "",
        "revision": "unknown",
        "document_date": "unknown",
        "notes": "Use official/vendor/distributor evidence before relying on mirrors.",
    }


def document_id(url: str) -> str:
    kind = classify_source(url)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    return f"{kind}-{digest}"


def required_documents() -> list[dict[str, str]]:
    return [
        {"type": "datasheet", "why": "pinout, package, electrical limits, memory, ordering code"},
        {"type": "reference_manual", "why": "registers, clocks, interrupts, DMA, peripheral behavior"},
        {"type": "errata", "why": "silicon defects and required workarounds"},
        {"type": "board_schematic", "why": "actual pin use, power rails, boot straps, debug connector"},
        {"type": "application_notes", "why": "layout and peripheral-specific implementation notes"},
    ]


def document_type_aliases(required_type: str) -> set[str]:
    aliases = {
        "board_schematic": {"board_schematic", "schematic", "board_manual"},
        "application_notes": {"application_notes", "application_note"},
    }
    return aliases.get(required_type, {required_type})


def coverage_status(required_type: str, documents: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    aliases = document_type_aliases(required_type)
    found = [item for item in documents if item.get("document_type") in aliases]
    downloaded = [item for item in found if item.get("download_status") == "downloaded"]
    if downloaded:
        return "downloaded", downloaded
    if found:
        return "source-recorded", found
    return "missing", []


def document_coverage(documents: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for required in required_documents():
        status, matches = coverage_status(required["type"], documents)
        rows.append(
            {
                "type": required["type"],
                "why": required["why"],
                "status": status,
                "found_count": len(matches),
                "documents": [
                    {
                        "document_id": item.get("document_id", ""),
                        "document_type": item.get("document_type", ""),
                        "provider": item.get("provider", ""),
                        "source_quality": item.get("source_quality", ""),
                        "url": item.get("url", ""),
                        "final_url": item.get("final_url", ""),
                        "http_status": item.get("http_status", ""),
                        "content_type": item.get("content_type", ""),
                        "size_bytes": item.get("size_bytes", ""),
                        "sha256": item.get("sha256", ""),
                        "saved_path": item.get("saved_path", ""),
                        "revision": item.get("revision", "unknown"),
                        "document_date": item.get("document_date", "unknown"),
                    }
                    for item in matches
                ],
            }
        )
    return {
        "schema_version": 1,
        "status": "complete" if all(row["status"] == "downloaded" for row in rows) else "incomplete",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "required": rows,
        "missing": [row["type"] for row in rows if row["status"] == "missing"],
    }


def render_source_map(data: dict[str, Any]) -> str:
    lines = [
        "# Chip Source Map",
        "",
        f"- Part: `{data['part']}`",
        f"- Board: {data.get('board') or 'unknown'}",
        f"- Documents directory: `{data['documents_dir']}`",
        "",
        "## Required Documents",
        "",
    ]
    for item in data["required_documents"]:
        lines.append(f"- `{item['type']}`: {item['why']}")
    lines.extend(["", "## Sources", ""])
    if data["documents"]:
        lines.append("| ID | Type | Status | Provider | Quality | SHA256 | URL | Notes |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for item in data["documents"]:
            lines.append(
                f"| {item.get('document_id', '')} | {item['document_type']} | {item['download_status']} | "
                f"{item.get('provider', '')} | {item.get('source_quality', '')} | {str(item.get('sha256', ''))[:12]} | "
                f"{item['url']} | {item['notes']} |"
            )
    else:
        lines.append("- No sources recorded yet.")
    if data.get("document_coverage"):
        lines.extend(["", "## Coverage", ""])
        lines.append(f"- Status: `{data['document_coverage']['status']}`")
        if data["document_coverage"].get("missing"):
            lines.append(f"- Missing: {', '.join(data['document_coverage']['missing'])}")
        else:
            lines.append("- Missing: none")
    if data.get("vendor_search_hints"):
        lines.extend(["", "## Vendor Search Hints", ""])
        for item in data["vendor_search_hints"]:
            lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Rules",
            "",
            "- Prefer manufacturer and authorized distributor documents.",
            "- Save only validated PDFs under `documents/`.",
            "- Mark missing evidence as `unknown`; do not fill pinouts or electrical limits from memory.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_document_coverage(coverage: dict[str, Any]) -> str:
    lines = [
        "# Document Coverage",
        "",
        f"- Status: `{coverage['status']}`",
        f"- Missing: {', '.join(coverage.get('missing') or []) or 'none'}",
        "",
        "| Required | Status | Found | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for row in coverage["required"]:
        evidence = ", ".join(
            f"{item.get('document_id', '')} ({item.get('source_quality', '')}, {str(item.get('sha256', ''))[:12] or 'no-hash'})"
            for item in row["documents"]
        )
        lines.append(f"| {row['type']} | {row['status']} | {row['found_count']} | {evidence or 'none'} |")
    lines.extend(["", "## Rules", "", "- Missing rows must stay unknown in summaries and pin advice."])
    return "\n".join(lines) + "\n"


def render_manual_summary_skeleton(data: dict[str, Any]) -> str:
    part = data["part"]
    board = data.get("board") or "unknown"
    return f"""# Manual Summary

- Part: `{part}`
- Board: {board}
- Evidence status: source map created, manual details not yet extracted.

## Quick Start

- Power rails: unknown
- Clock source: unknown
- Reset and boot: unknown
- Debug/programming: unknown
- First safe firmware test: build-only, then flash after safety checklist passes.

## Pin And Package Notes

- Package: unknown
- Debug pins: unknown
- Boot pins: unknown
- Voltage-domain restrictions: unknown

## Peripherals

| Peripheral | Pins | Clock/DMA/IRQ | CubeMX/HAL notes | Risks |
| --- | --- | --- | --- | --- |

## Electrical Limits

- Absolute maximum ratings: unknown
- Recommended operating conditions: unknown
- GPIO source/sink limits: unknown
- ADC input limits: unknown

## Errata

| Issue | Impact | Workaround | Source |
| --- | --- | --- | --- |

## Next Evidence Actions

- Locate official datasheet.
- Locate official reference manual.
- Locate errata.
- Locate board schematic or user manual when a board is involved.
"""


def render_safety_checklist(data: dict[str, Any]) -> str:
    return f"""# Hardware Safety Checklist

- Part: `{data['part']}`
- Board: {data.get('board') or 'unknown'}

## Before Flash Or Hardware Output

- [ ] Exact chip/package confirmed.
- [ ] Target voltage confirmed.
- [ ] Current limit confirmed.
- [ ] Debug probe and target identity confirmed.
- [ ] Flash/erase scope confirmed.
- [ ] Recovery path confirmed.
- [ ] External loads and fragile inputs identified.
- [ ] SWD/JTAG/boot access preserved.
"""


def render_cubemx_config_skeleton(data: dict[str, Any]) -> str:
    return f"""# CubeMX Configuration Notes

- Part: `{data['part']}`
- Board: {data.get('board') or 'unknown'}

## Pin Requests

No pin requests recorded yet.

## Configuration Evidence

- CubeMX `.ioc`: unknown
- Schematic cross-check: unknown
- Datasheet/reference manual cross-check: unknown

## Rules

- Use `python tools\\hardware_butler.py advise-pin --root <project> --pin <pin> --function <function>` before changing CubeMX settings.
- Mark alternate-function availability as `needs verification` unless confirmed by package pin data or the existing `.ioc`.
- Keep SWD/JTAG, boot, reset, oscillator, and power pins recoverable during bring-up.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a chip bring-up dossier")
    parser.add_argument("--part", required=True)
    parser.add_argument("--board", default="")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--search", action="store_true", help="Discover PDF links from search-source pages or built-in vendor hints before downloading")
    parser.add_argument("--search-source", action="append", default=[], help="HTML page, index file, or PDF URL to search; omit to use built-in vendor hints")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--no-extract", action="store_true", help="Do not extract PDF text or rewrite manual-summary.md")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    part = normalize_part(args.part)
    out_dir = Path(args.out_dir) if args.out_dir else runtime_context.workspace_root() / "docs" / "chip" / part
    if args.search:
        data = search_and_download_documents(part, out_dir, board=args.board, search_sources=args.search_source or args.source)
    elif args.download:
        data = download_documents(part, out_dir, board=args.board, sources=args.source, extract_text=not args.no_extract)
    else:
        data = create_dossier(part, out_dir, board=args.board, sources=args.source)
    if args.as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render_source_map(data))


if __name__ == "__main__":
    main()
