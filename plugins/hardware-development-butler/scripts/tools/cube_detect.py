"""Detect STM32CubeMX projects and rank build backend candidates.

The detector is read-only. It combines CubeMX .ioc metadata with filesystem
evidence so the butler can recommend a next action without guessing when
multiple build backends exist.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import cubemx_ioc_summary  # noqa: E402
import project_scanner  # noqa: E402
import runtime_context  # noqa: E402
import safe_io  # noqa: E402


def detect(root: Path) -> dict[str, Any]:
    root = root.resolve()
    scan_data = project_scanner.scan(root)
    artifacts = scan_data.get("artifacts", {})
    ioc_projects = []

    for item in artifacts.get("cubemx_ioc", []):
        ioc_path = root / item["path"]
        try:
            summary = cubemx_ioc_summary.summarize(ioc_path)
        except OSError as exc:
            summary = {
                "ioc_file": str(ioc_path),
                "error": str(exc),
            }
        except Exception as exc:
            summary = {
                "ioc_file": str(ioc_path),
                "error": f"unexpected error: {exc}",
            }
        ioc_projects.append(summary)

    candidates = rank_backend_candidates(artifacts, ioc_projects)
    selected = choose_candidate(candidates)
    primary_ioc = ioc_projects[0] if ioc_projects else {}
    primary_project = primary_ioc.get("project", {}) if isinstance(primary_ioc.get("project"), dict) else {}

    return {
        "schema_version": 1,
        "root": str(root),
        "cubemx_projects": ioc_projects,
        "backend_candidates": candidates,
        "selected_backend": selected,
        "has_cubemx": bool(ioc_projects),
        "mcu": primary_project.get("mcu", ""),
        "ioc_path": primary_ioc.get("ioc_file", ""),
        "warnings": warnings_for(scan_data, candidates),
        "next_actions": next_actions(selected, candidates),
    }


def rank_backend_candidates(
    artifacts: dict[str, list[dict[str, Any]]], ioc_projects: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    declared = declared_toolchains(ioc_projects)
    candidates: list[dict[str, Any]] = []

    if artifacts.get("keil_project"):
        candidates.append(
            candidate(
                "keil",
                90 if any("mdk" in item or "keil" in item for item in declared) else 82,
                "Keil project files were detected.",
                artifacts["keil_project"],
            )
        )
    if artifacts.get("cmake_project"):
        candidates.append(
            candidate(
                "cmake-gcc",
                86 if any("cmake" in item or "stm32cubeide" in item for item in declared) else 78,
                "CMake project files were detected.",
                artifacts["cmake_project"],
            )
        )
    if artifacts.get("eide_project"):
        candidates.append(
            candidate(
                "eide",
                72,
                "EIDE project metadata was detected.",
                artifacts["eide_project"],
            )
        )
    if artifacts.get("makefile"):
        candidates.append(
            candidate(
                "make",
                48,
                "Makefile was detected, but pure Makefile is outside the first MVP automation boundary.",
                artifacts["makefile"],
                supported=False,
            )
        )

    return sorted(candidates, key=lambda item: item["score"], reverse=True)


def declared_toolchains(ioc_projects: list[dict[str, Any]]) -> set[str]:
    values = set()
    for project in ioc_projects:
        toolchain = project.get("project", {}).get("toolchain", "")
        if toolchain:
            values.add(toolchain.lower())
    return values


def candidate(
    backend: str,
    score: int,
    reason: str,
    evidence: list[dict[str, Any]],
    *,
    supported: bool = True,
) -> dict[str, Any]:
    return {
        "backend": backend,
        "score": score,
        "supported_in_mvp": supported,
        "reason": reason,
        "evidence": evidence[:10],
    }


def choose_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    supported = [item for item in candidates if item["supported_in_mvp"]]
    if not supported:
        return None
    if len(supported) > 1 and supported[0]["score"] == supported[1]["score"]:
        return {
            "backend": "manual-choice-required",
            "score": supported[0]["score"],
            "reason": "Multiple supported backends have the same confidence.",
            "options": supported,
        }
    return supported[0]


def warnings_for(scan_data: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, str]]:
    warnings = []
    if scan_data["summary"]["has_cubemx"] and not candidates:
        warnings.append(
            {
                "code": "cubemx_without_backend",
                "message": "CubeMX .ioc exists, but no Keil, CMake/GCC, EIDE, or Makefile backend was detected.",
            }
        )
    if len([item for item in candidates if item["supported_in_mvp"]]) > 1:
        warnings.append(
            {
                "code": "multiple_supported_backends",
                "message": "Multiple supported build backends were detected; confirm before running build.",
            }
        )
    return warnings


def next_actions(selected: dict[str, Any] | None, candidates: list[dict[str, Any]]) -> list[str]:
    if not candidates:
        return ["Add or locate Keil, CMake/GCC, EIDE, or Makefile build metadata."]
    if selected is None:
        return ["Choose a supported backend before build automation."]
    backend = selected["backend"]
    if backend == "manual-choice-required":
        return ["Ask the user to choose one backend from the options before running build."]
    if backend == "keil":
        return ["Use embeddedskills/keil project scan and target enumeration before build."]
    if backend == "cmake-gcc":
        return ["Use embeddedskills/gcc preset/configure/build flow before flash."]
    if backend == "eide":
        return ["Use embeddedskills/eide project discovery before build."]
    return ["Inspect backend manually before build automation."]


def render_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# CubeMX Backend Detection",
        "",
        f"- Root: `{data['root']}`",
        f"- CubeMX projects: {len(data['cubemx_projects'])}",
        "",
        "## Selected Backend",
        "",
    ]
    selected = data.get("selected_backend")
    if selected:
        lines.append(f"- Backend: `{selected['backend']}`")
        lines.append(f"- Score: {selected['score']}")
        lines.append(f"- Reason: {selected['reason']}")
    else:
        lines.append("- none")
    lines.extend(["", "## Candidates", ""])
    for item in data["backend_candidates"]:
        lines.append(
            f"- `{item['backend']}` score={item['score']} supported={item['supported_in_mvp']}: {item['reason']}"
        )
    if not data["backend_candidates"]:
        lines.append("- none")
    lines.extend(["", "## Warnings", ""])
    for item in data["warnings"]:
        lines.append(f"- {item['code']}: {item['message']}")
    if not data["warnings"]:
        lines.append("- none")
    lines.extend(["", "## Next Actions", ""])
    for action in data["next_actions"]:
        lines.append(f"- {action}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect CubeMX project and build backend candidates")
    parser.add_argument("--root", default=".", help="Project root to inspect")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    data = detect(Path(args.root))
    content = json.dumps(data, ensure_ascii=False, indent=2) if args.as_json and not args.markdown else render_markdown(data)
    if args.out:
        safe_io.safe_write_text(Path(args.out), content, allowed_roots=runtime_context.allowed_write_roots())
    else:
        print(content)


if __name__ == "__main__":
    main()
