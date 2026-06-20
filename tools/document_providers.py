"""Vendor-aware document provider hints and source quality scoring."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote, urlparse


@dataclass(frozen=True)
class Provider:
    name: str
    vendor: str
    official_hosts: tuple[str, ...]
    search_urls: tuple[str, ...]


PROVIDERS: tuple[Provider, ...] = (
    Provider(
        "st",
        "STMicroelectronics",
        ("st.com", "www.st.com"),
        (
            "https://www.st.com/en/search.html#q={part}-t=resources-page=1",
            "https://www.st.com/resource/en/datasheet/{part_lower}.pdf",
        ),
    ),
    Provider(
        "nxp",
        "NXP",
        ("nxp.com", "www.nxp.com"),
        ("https://www.nxp.com/search?keyword={part}",),
    ),
    Provider(
        "ti",
        "Texas Instruments",
        ("ti.com", "www.ti.com"),
        (
            "https://www.ti.com/product/{part_upper}",
            "https://www.ti.com/lit/gpn/{part_lower}",
        ),
    ),
    Provider(
        "infineon",
        "Infineon",
        ("infineon.com", "www.infineon.com"),
        ("https://www.infineon.com/cms/en/search.html#!term={part}",),
    ),
    Provider(
        "gd",
        "GigaDevice",
        ("gd32mcu.com", "www.gd32mcu.com", "gigadevice.com", "www.gigadevice.com"),
        ("https://www.gd32mcu.com/en/search?keyword={part}",),
    ),
    Provider(
        "microchip",
        "Microchip",
        ("microchip.com", "www.microchip.com"),
        ("https://www.microchip.com/en-us/search?searchQuery={part}",),
    ),
)


AUTHORIZED_DISTRIBUTOR_HOSTS = (
    "digikey.com",
    "mouser.com",
    "arrow.com",
    "avnet.com",
    "element14.com",
)


def normalized_part_tokens(part: str) -> dict[str, str]:
    part = re.sub(r"[^A-Za-z0-9_.-]+", "-", part.strip()).strip("-")
    return {
        "part": quote(part),
        "part_lower": quote(part.lower()),
        "part_upper": quote(part.upper()),
    }


def provider_for_host(host: str) -> Provider | None:
    host = host.lower().strip(".")
    for provider in PROVIDERS:
        if any(host == item or host.endswith("." + item) for item in provider.official_hosts):
            return provider
    return None


def infer_provider(url: str) -> dict[str, str]:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    provider = provider_for_host(host)
    if provider:
        return {"provider": provider.name, "vendor": provider.vendor, "source_quality": "official"}
    if any(host == item or host.endswith("." + item) for item in AUTHORIZED_DISTRIBUTOR_HOSTS):
        return {"provider": "authorized-distributor", "vendor": "", "source_quality": "authorized-distributor"}
    if parsed.scheme == "file":
        return {"provider": "local-fixture", "vendor": "", "source_quality": "local"}
    if host:
        return {"provider": "unknown-web", "vendor": "", "source_quality": "mirror-or-unknown"}
    return {"provider": "local-path", "vendor": "", "source_quality": "local"}


def search_hints(part: str) -> list[dict[str, str]]:
    tokens = normalized_part_tokens(part)
    hints: list[dict[str, str]] = []
    for provider in PROVIDERS:
        for template in provider.search_urls:
            hints.append(
                {
                    "provider": provider.name,
                    "vendor": provider.vendor,
                    "source_quality": "official-search",
                    "url": template.format(**tokens),
                }
            )
    return hints
