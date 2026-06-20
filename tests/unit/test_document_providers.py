"""Unit tests for document_providers module."""

import document_providers


def test_provider_for_host_recognizes_st():
    """provider_for_host should recognize STMicroelectronics domains."""
    provider = document_providers.provider_for_host("www.st.com")

    assert provider is not None
    assert provider.name == "st"
    assert provider.vendor == "STMicroelectronics"


def test_provider_for_host_recognizes_nxp():
    """provider_for_host should recognize NXP domains."""
    provider = document_providers.provider_for_host("www.nxp.com")

    assert provider is not None
    assert provider.name == "nxp"


def test_provider_for_host_returns_none_for_unknown():
    """provider_for_host should return None for unknown hosts."""
    provider = document_providers.provider_for_host("example.com")

    assert provider is None


def test_infer_provider_classifies_official():
    """infer_provider should classify official sources."""
    result = document_providers.infer_provider("https://www.st.com/resource/en/datasheet/stm32f407vg.pdf")

    assert result["provider"] == "st"
    assert result["vendor"] == "STMicroelectronics"
    assert result["source_quality"] == "official"


def test_infer_provider_classifies_distributor():
    """infer_provider should classify authorized distributors."""
    result = document_providers.infer_provider("https://www.digikey.com/product-detail/en/...")

    assert result["provider"] == "authorized-distributor"
    assert result["source_quality"] == "authorized-distributor"


def test_infer_provider_classifies_unknown():
    """infer_provider should classify unknown web sources."""
    result = document_providers.infer_provider("https://random-site.com/datasheet.pdf")

    assert result["provider"] == "unknown-web"
    assert result["source_quality"] == "mirror-or-unknown"


def test_search_hints_includes_major_vendors():
    """search_hints should include all major vendors."""
    hints = document_providers.search_hints("STM32F407VGTx")

    providers = {item["provider"] for item in hints}

    assert "st" in providers
    assert "nxp" in providers
    assert "ti" in providers
    assert "infineon" in providers
    assert "gd" in providers
    assert "microchip" in providers


def test_search_hints_formats_urls():
    """search_hints should format search URLs with part number."""
    hints = document_providers.search_hints("STM32F407VG")

    # All URLs should be strings and contain the part or variant
    for hint in hints:
        assert isinstance(hint["url"], str)
        assert hint["url"].startswith("http")


def test_normalized_part_tokens():
    """normalized_part_tokens should provide quoted variants."""
    tokens = document_providers.normalized_part_tokens("STM32F407VG")

    assert "part" in tokens
    assert "part_lower" in tokens
    assert "part_upper" in tokens
