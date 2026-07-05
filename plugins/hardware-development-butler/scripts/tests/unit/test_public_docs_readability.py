from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PUBLIC_DOCS = (
    "README.md",
    "docs/BEGINNER_GUIDE.md",
    "docs/START_HERE.md",
    "docs/ARCHITECTURE_MAP.md",
    "docs/HARDWARE_UNDERSTANDING.md",
    "docs/INSTALL.md",
    "docs/COMMANDS.md",
)

CHINESE_ONBOARDING_DOCS = (
    "README.md",
    "docs/BEGINNER_GUIDE.md",
    "docs/START_HERE.md",
    "docs/ARCHITECTURE_MAP.md",
    "docs/HARDWARE_UNDERSTANDING.md",
    "docs/COMMANDS.md",
)

REQUIRED_CHINESE_TERMS = (
    "\u5b89\u5168",  # safety
    "\u786c\u4ef6",  # hardware
    "\u9879\u76ee",  # project
)

MOJIBAKE_SOURCE_TERMS = (
    "\u8fd9\u662f",  # this is
    "\u5b89\u5168",  # safety
    "\u786c\u4ef6",  # hardware
    "\u5de5\u4f5c\u6d41",  # workflow
    "\u8bc1\u636e",  # evidence
    "\u70e7\u5f55",  # flash/program
    "\u8c03\u8bd5",  # debug
)


def _gbk_mojibake_marker(text: str) -> str:
    return text.encode("utf-8").decode("gbk", errors="replace")


def test_public_docs_decode_as_utf8_and_keep_core_terms_readable() -> None:
    for relative in PUBLIC_DOCS:
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")

        assert "Hardware Butler" in text, f"{relative} does not identify the project"

    for relative in CHINESE_ONBOARDING_DOCS:
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")

        for term in REQUIRED_CHINESE_TERMS:
            assert term in text, f"{relative} is missing {term!a}"


def test_public_docs_do_not_contain_common_mojibake_markers() -> None:
    markers = {_gbk_mojibake_marker(term) for term in MOJIBAKE_SOURCE_TERMS}
    markers.discard("")

    for relative in PUBLIC_DOCS:
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")

        assert "\ufffd" not in text, f"{relative} contains Unicode replacement characters"
        for marker in markers:
            assert marker not in text, f"{relative} contains mojibake marker {marker!a}"
