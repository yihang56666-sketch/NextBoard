"""Optional API-backed document search for chip and board evidence.

The module never stores API keys. Providers are configured through environment
variables and return source URLs that the chip dossier downloader still validates
as PDFs before saving.
"""

from __future__ import annotations

import json
import os
from typing import Any, Mapping
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_TIMEOUT_S = 20
EXA_ENDPOINT = "https://api.exa.ai/search"
DEFAULT_PRESET = "chip-docs"
SEARCH_PRESETS = {
    "chip-docs": {
        "label": "Chip documents",
        "terms": "datasheet reference manual errata application note programming manual PDF",
        "include_domains": [
            "st.com",
            "nxp.com",
            "ti.com",
            "infineon.com",
            "microchip.com",
            "gd32mcu.com",
            "renesas.com",
            "analog.com",
        ],
    },
    "board-docs": {
        "label": "Board documents",
        "terms": "schematic board manual user guide getting started hardware design PDF",
        "include_domains": [
            "st.com",
            "nxp.com",
            "ti.com",
            "infineon.com",
            "microchip.com",
            "github.com",
            "oshwhub.com",
        ],
    },
    "part-risk": {
        "label": "Part risk documents",
        "terms": "datasheet errata lifecycle PCN EOL replacement distributor PDF",
        "include_domains": [
            "digikey.com",
            "mouser.com",
            "arrow.com",
            "st.com",
            "nxp.com",
            "ti.com",
            "infineon.com",
            "microchip.com",
        ],
    },
}


def configured_providers(env: Mapping[str, str] | None = None) -> list[str]:
    search_env: Mapping[str, str] = os.environ if env is None else env
    providers = []
    if search_env.get("EXA_API_KEY") or search_env.get("EXA_SEARCH_API_KEY"):
        providers.append("exa")
    if search_env.get("DOC_SEARCH_API_URL"):
        providers.append("generic")
    return providers


def search_documents(
    part: str,
    *,
    providers: list[str] | None = None,
    preset: str = DEFAULT_PRESET,
    query_extra: str = "",
    max_results: int = 8,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    search_env: Mapping[str, str] = os.environ if env is None else env
    max_results = max(1, min(max_results, 20))
    selected = providers or configured_providers(search_env)
    preset_config = search_preset(preset)
    query = build_query(part, query_extra, preset=preset)
    provider_results = []
    urls: list[str] = []

    if not selected:
        return {
            "schema_version": 1,
            "status": "api-not-configured",
            "query": query,
            "preset": preset_config,
            "providers": [],
            "urls": [],
            "notes": [
                "Set EXA_API_KEY for Exa search, or DOC_SEARCH_API_URL and optional DOC_SEARCH_API_KEY for a generic search API."
            ],
        }

    for provider in selected:
        if provider == "exa":
            result = search_exa(
                query,
                max_results=max_results,
                timeout_s=timeout_s,
                env=search_env,
                include_domains=list(preset_config["include_domains"]),
            )
        elif provider == "generic":
            result = search_generic(query, max_results=max_results, timeout_s=timeout_s, env=search_env)
        else:
            result = {"provider": provider, "status": "unsupported-provider", "urls": []}
        provider_results.append(result)
        for url in result.get("urls", []):
            if isinstance(url, str) and url not in urls:
                urls.append(url)

    status = provider_status(provider_results, urls)
    return {
        "schema_version": 1,
        "status": status,
        "query": query,
        "preset": preset_config,
        "providers": provider_results,
        "urls": urls,
    }


def provider_status(provider_results: list[dict[str, Any]], urls: list[str]) -> str:
    if urls:
        return "ok"
    statuses = {str(item.get("status", "")) for item in provider_results}
    if statuses and statuses <= {"api-not-configured"}:
        return "api-not-configured"
    if "error" in statuses:
        return "error"
    if statuses and statuses <= {"unsupported-provider"}:
        return "unsupported-provider"
    return "no-results"


def search_preset(name: str) -> dict[str, Any]:
    preset_id = name if name in SEARCH_PRESETS else DEFAULT_PRESET
    config = SEARCH_PRESETS[preset_id]
    return {
        "id": preset_id,
        "label": config["label"],
        "terms": config["terms"],
        "include_domains": list(config["include_domains"]),
    }


def build_query(part: str, query_extra: str = "", *, preset: str = DEFAULT_PRESET) -> str:
    preset_config = search_preset(preset)
    terms = [
        part.strip(),
        str(preset_config["terms"]),
        query_extra.strip(),
    ]
    return " ".join(item for item in terms if item)


def search_exa(
    query: str,
    *,
    max_results: int,
    timeout_s: int,
    env: Mapping[str, str],
    include_domains: list[str],
) -> dict[str, Any]:
    api_key = env.get("EXA_API_KEY") or env.get("EXA_SEARCH_API_KEY")
    if not api_key:
        return {"provider": "exa", "status": "api-not-configured", "urls": []}
    payload = json.dumps(
        {
            "query": query,
            "numResults": max_results,
            "type": "auto",
            "includeDomains": include_domains,
        }
    ).encode("utf-8")
    request = Request(
        EXA_ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
        },
        method="POST",
    )
    return fetch_json_urls("exa", request, timeout_s=timeout_s)


def search_generic(query: str, *, max_results: int, timeout_s: int, env: Mapping[str, str]) -> dict[str, Any]:
    endpoint = env.get("DOC_SEARCH_API_URL", "")
    if not endpoint:
        return {"provider": "generic", "status": "api-not-configured", "urls": []}
    separator = "&" if "?" in endpoint else "?"
    url = f"{endpoint}{separator}{urlencode({'q': query, 'limit': str(max_results)})}"
    headers = {}
    if env.get("DOC_SEARCH_API_KEY"):
        headers["Authorization"] = f"Bearer {env['DOC_SEARCH_API_KEY']}"
    request = Request(url, headers=headers, method="GET")
    return fetch_json_urls("generic", request, timeout_s=timeout_s)


def fetch_json_urls(provider: str, request: Request, *, timeout_s: int) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=timeout_s) as response:  # noqa: S310 - user-configured search endpoint
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except (OSError, URLError, json.JSONDecodeError) as exc:
        return {"provider": provider, "status": "error", "error": str(exc), "urls": []}
    urls = extract_urls(payload)
    return {"provider": provider, "status": "ok" if urls else "no-results", "urls": urls}


def extract_urls(payload: Any) -> list[str]:
    urls: list[str] = []

    def add(value: Any) -> None:
        if isinstance(value, str) and value.startswith(("http://", "https://")) and value not in urls:
            urls.append(value)

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key in ("url", "link", "href", "pdf", "document_url"):
                add(value.get(key))
            for key in ("results", "items", "documents", "data"):
                if key in value:
                    walk(value[key])
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)
    return urls
