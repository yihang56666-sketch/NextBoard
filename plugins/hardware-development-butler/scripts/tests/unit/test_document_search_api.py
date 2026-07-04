from __future__ import annotations

import sys

sys.path.insert(0, "tools")

import document_search_api


def test_search_documents_reports_not_configured_without_api_env() -> None:
    result = document_search_api.search_documents("STM32F407VGTx", env={})

    assert result["status"] == "api-not-configured"
    assert result["urls"] == []
    assert "STM32F407VGTx" in result["query"]


def test_extract_urls_accepts_common_api_shapes() -> None:
    payload = {
        "results": [
            {"url": "https://www.st.com/resource/en/datasheet/stm32f407vg.pdf"},
            {"link": "https://www.st.com/resource/en/reference_manual/rm0090.pdf"},
            {"nested": {"url": "https://ignored.example/doc.pdf"}},
        ],
        "documents": [{"document_url": "https://www.nxp.com/docs/en/data-sheet/example.pdf"}],
    }

    urls = document_search_api.extract_urls(payload)

    assert urls == [
        "https://www.st.com/resource/en/datasheet/stm32f407vg.pdf",
        "https://www.st.com/resource/en/reference_manual/rm0090.pdf",
        "https://www.nxp.com/docs/en/data-sheet/example.pdf",
    ]


def test_build_query_keeps_extra_terms() -> None:
    query = document_search_api.build_query("STM32F407VGTx", "discovery board schematic")

    assert "STM32F407VGTx" in query
    assert "reference manual" in query
    assert "discovery board schematic" in query


def test_search_preset_changes_query_terms() -> None:
    board_query = document_search_api.build_query("STM32F407VGTx", preset="board-docs")
    risk_query = document_search_api.build_query("STM32F407VGTx", preset="part-risk")

    assert "schematic board manual" in board_query
    assert "lifecycle" in risk_query
    assert document_search_api.search_preset("unknown")["id"] == "chip-docs"


def test_search_documents_records_selected_preset_without_api_env() -> None:
    result = document_search_api.search_documents("STM32F407VGTx", preset="part-risk", env={})

    assert result["status"] == "api-not-configured"
    assert result["preset"]["id"] == "part-risk"
    assert "lifecycle" in result["query"]


def test_search_documents_reports_missing_key_for_explicit_provider() -> None:
    result = document_search_api.search_documents("STM32F407VGTx", providers=["exa"], env={})

    assert result["status"] == "api-not-configured"
    assert result["providers"][0]["provider"] == "exa"
    assert result["providers"][0]["status"] == "api-not-configured"
