from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import chip_dossier


def test_api_search_falls_back_to_vendor_hints_when_api_has_no_urls(tmp_path: Path) -> None:
    index_dir = tmp_path / "index"
    index_dir.mkdir()
    pdf_path = index_dir / "STM32F407VGTx-datasheet.pdf"
    shutil.copy2(REPO_ROOT / "tests" / "fixtures" / "docs" / "sample-datasheet.pdf", pdf_path)
    index = index_dir / "index.html"
    index.write_text(f'<html><a href="{pdf_path.resolve().as_uri()}">datasheet</a></html>', encoding="utf-8")

    original_hints = chip_dossier.vendor_search_hints
    original_search = chip_dossier.document_search_api.search_documents
    chip_dossier.vendor_search_hints = lambda part: [index.as_uri()]
    chip_dossier.document_search_api.search_documents = lambda *args, **kwargs: {
        "schema_version": 1,
        "status": "api-not-configured",
        "urls": [],
        "providers": [],
    }
    try:
        dossier = chip_dossier.search_and_download_documents(
            "STM32F407VGTx",
            tmp_path / "out",
            search_sources=[],
            api_search=True,
        )
    finally:
        chip_dossier.vendor_search_hints = original_hints
        chip_dossier.document_search_api.search_documents = original_search

    assert dossier["search"]["api_search"]["status"] == "api-not-configured"
    assert dossier["search"]["search_sources"] == [index.as_uri()]
    assert dossier["download_results"][0]["status"] == "downloaded"
