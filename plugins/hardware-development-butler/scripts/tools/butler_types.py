"""Type definitions for hardware butler."""

from __future__ import annotations

from typing import Literal, TypedDict


# Document types
class DocumentRecord(TypedDict):
    """Document source record."""
    url: str
    document_type: str
    source_quality: str
    provider: str
    vendor: str
    status: str
    notes: str


class DocumentCoverage(TypedDict):
    """Document coverage assessment."""
    status: Literal["complete", "incomplete", "minimal"]
    missing: list[str]
    present: list[str]
    coverage_percent: float


# Chip dossier
class ChipDossier(TypedDict):
    """Chip documentation dossier."""
    schema_version: int
    status: str
    part: str
    board: str
    out_dir: str
    documents_dir: str
    documents: list[DocumentRecord]
    required_documents: list[str]
    document_coverage: DocumentCoverage
    provider_search_hints: list[dict[str, str]]
    generated_at: str
    written: dict[str, str]


# Project detection
class BackendCandidate(TypedDict):
    """Build backend detection result."""
    backend: Literal["keil", "cmake", "eide", "makefile"]
    score: int
    evidence: list[str]


class CubeDetection(TypedDict):
    """CubeMX project detection."""
    selected_backend: BackendCandidate
    backend_candidates: list[BackendCandidate]
    ioc_path: str | None
    mcu: str | None
    has_cubemx: bool


# Build plan
class CommandStep(TypedDict):
    """Build command step."""
    phase: str
    name: str
    argv: list[str]
    description: str
    safe: bool
    read_only: bool
    allows_extra_args: bool


class BuildPlan(TypedDict):
    """Build execution plan."""
    schema_version: int
    root: str
    backend: str
    steps: list[CommandStep]


# CubeMX pin configuration
class PinConfig(TypedDict):
    """Pin configuration details."""
    pin: str
    function: str
    function_class: str
    mode: str
    pull: str
    speed: str
    alternate_function: int | None
    label: str


class PinAdvice(TypedDict):
    """Pin configuration advice."""
    pin: str
    requested_function: str
    configuration: PinConfig
    alternatives: list[str]
    conflicts: list[str]
    risks: list[str]
    reasons: list[str]


# Hardware action
class HardwareActionPlan(TypedDict):
    """Hardware action safety plan."""
    schema_version: int
    action: str
    target: str
    probe: str
    voltage: str
    current_limit: str
    erase_scope: str
    recovery: str
    external_loads: str
    artifact: str
    artifact_hash: str
    backend: str
    confirmation_token: str
    child_tokens: list[dict[str, str]]


# Firmware intent
class FirmwareIntent(TypedDict):
    """Firmware implementation intent."""
    schema_version: int
    feature: str
    pin: str
    function: str
    rtos_enabled: bool
    app_module_name: str
    implementation_steps: list[str]
    risks: list[str]


# Config proposal
class ConfigProposal(TypedDict):
    """EmbeddedSkills config proposal."""
    schema_version: int
    status: str
    ready: bool
    config: dict[str, str | dict[str, str]]
    missing: list[str]
    warnings: list[str]
