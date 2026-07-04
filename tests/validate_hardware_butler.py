"""Validation checks for the hardware butler MVP."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import bench_runbook  # noqa: E402
import build_plan  # noqa: E402
import chip_dossier  # noqa: E402
import command_runner  # noqa: E402
import config_proposal  # noqa: E402
import cube_detect  # noqa: E402
import cubemx_config_advisor  # noqa: E402
import document_providers  # noqa: E402
import document_search_api  # noqa: E402
import firmware_code_patcher  # noqa: E402
import firmware_intent_planner  # noqa: E402
import hardware_action_audit  # noqa: E402
import hardware_action_executor  # noqa: E402
import hardware_action_plan  # noqa: E402
import hardware_butler  # noqa: E402
import manual_summarizer  # noqa: E402
import product_doctor  # noqa: E402
import project_workflow  # noqa: E402
import runtime_context  # noqa: E402
import safe_io  # noqa: E402
import task_workflows  # noqa: E402

EMBEDDED_DIR = runtime_context.embeddedskills_root()
if str(EMBEDDED_DIR) not in sys.path:
    sys.path.insert(0, str(EMBEDDED_DIR))
import safety_gate  # noqa: E402

os.environ.setdefault(runtime_context.ENV_WORKSPACE_ROOT, str(REPO_ROOT))
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "cubemx-basic"
TEST_TMP = REPO_ROOT / "tests" / "tmp" / "hardware-butler"


def repo_path(rel: str) -> Path:
    path = Path(rel)
    if path.parts and path.parts[0] == "embeddedskills":
        return EMBEDDED_DIR.joinpath(*path.parts[1:])
    return REPO_ROOT / path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_cube_detection() -> None:
    result = cube_detect.detect(FIXTURE)
    require(result["selected_backend"]["backend"] == "keil", "fixture should select Keil backend")
    require(result["selected_backend"]["score"] == 90, "Keil fixture score changed unexpectedly")


def test_cubemx_summary_semantic_indexes() -> None:
    import cubemx_ioc_summary

    summary = cubemx_ioc_summary.summarize(FIXTURE / "Blinky.ioc")
    require(summary["normalized_pins"]["PD12"]["function_class"] == "gpio", "PD12 should classify as GPIO")
    require("PD12" in summary["indexes"]["by_function"]["gpio"], "GPIO index should include PD12")
    require(summary["indexes"]["by_label"]["LED_GREEN"] == "PD12", "label index should include LED")
    require("PA13" in summary["indexes"]["reserved_pins"], "SWD pin should be reserved")


def test_chip_dossier_plan_shape() -> None:
    out_dir = TEST_TMP / "chip" / "STM32F407VGTx"
    dossier = chip_dossier.create_dossier(
        part="STM32F407VGTx",
        out_dir=out_dir,
        board="discovery-like board",
        sources=[
            "https://www.st.com/resource/en/datasheet/stm32f407vg.pdf",
            "https://www.st.com/resource/en/reference_manual/rm0090-stm32f4-reference-manual.pdf",
        ],
    )
    require(dossier["status"] == "ok", "chip dossier should be created")
    require(dossier["part"] == "STM32F407VGTx", "part should be preserved")
    require(len(dossier["documents"]) == 2, "source records should be preserved")
    require(Path(dossier["written"]["source_map"]).exists(), "source-map should be written")
    require(Path(dossier["written"]["manual_summary"]).exists(), "manual summary should be written")
    require(Path(dossier["written"]["cubemx_config"]).exists(), "CubeMX config notes should be written")
    require(Path(dossier["written"]["document_coverage_json"]).exists(), "document coverage JSON should be written")
    require(dossier["document_coverage"]["status"] == "incomplete", "coverage should flag missing documents")
    require(dossier["documents"][0]["source_quality"] == "official", "ST source should be classified official")
    cleanup_dir(out_dir)


def test_document_provider_hints_cover_major_vendors() -> None:
    hints = document_providers.search_hints("STM32F407VGTx")
    providers = {item["provider"] for item in hints}
    require({"st", "nxp", "ti", "infineon", "gd", "microchip"}.issubset(providers), "major provider hints missing")
    st = document_providers.infer_provider("https://www.st.com/resource/en/datasheet/stm32f407vg.pdf")
    require(st["source_quality"] == "official", "ST host should be official")


def test_chip_dossier_download_accepts_only_pdf() -> None:
    pdf = (REPO_ROOT / "tests" / "fixtures" / "docs" / "sample-datasheet.pdf").resolve().as_uri()
    html = (REPO_ROOT / "tests" / "fixtures" / "docs" / "not-a-datasheet.html").resolve().as_uri()
    fake_pdf = (REPO_ROOT / "tests" / "fixtures" / "docs" / "fake-prefix.pdf").resolve().as_uri()
    out_dir = TEST_TMP / "chip" / "STM32F407VGTx-download-test"
    dossier = chip_dossier.download_documents(
        part="STM32F407VGTx",
        out_dir=out_dir,
        sources=[pdf, html, fake_pdf],
    )
    statuses = {item["url"]: item["status"] for item in dossier["download_results"]}
    require(statuses[pdf] == "downloaded", "PDF source should be downloaded")
    require(statuses[html] == "rejected-non-pdf", "HTML source should be rejected")
    require(statuses[fake_pdf] == "rejected-non-pdf", "incomplete PDF-like source should be rejected")
    saved = [item for item in dossier["download_results"] if item["status"] == "downloaded"][0]["saved_path"]
    require(Path(saved).read_bytes().startswith(b"%PDF"), "saved document must be a PDF")
    downloaded = [item for item in dossier["documents"] if item["download_status"] == "downloaded"][0]
    require(downloaded["sha256"], "downloaded document should record sha256")
    require(downloaded["final_url"], "downloaded document should record final_url")
    require((out_dir / "document-coverage.json").exists(), "download should write document coverage JSON")
    cleanup_dir(out_dir)


def test_chip_dossier_search_download_extracts_summary() -> None:
    index_dir = TEST_TMP / "search-index"
    index_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = index_dir / "STM32F407VGTx-datasheet.pdf"
    shutil.copy2(REPO_ROOT / "tests" / "fixtures" / "docs" / "sample-datasheet.pdf", pdf_path)
    pdf = pdf_path.resolve().as_uri()
    index = index_dir / "index.html"
    index.write_text(f'<html><a href="{pdf}">STM32F407VGTx datasheet</a></html>', encoding="utf-8")
    out_dir = TEST_TMP / "chip" / "STM32F407VGTx-search-test"
    dossier = chip_dossier.search_and_download_documents(
        part="STM32F407VGTx",
        out_dir=out_dir,
        search_sources=[index.as_uri()],
    )
    require(dossier["download_results"][0]["status"] == "downloaded", "search should discover and download PDF")
    require((out_dir / "manual-summary.md").exists(), "download should rewrite manual summary")
    require((out_dir / "manual-summary.json").exists(), "download should write machine summary")
    cleanup_dir(out_dir)
    cleanup_dir(index_dir)


def test_chip_dossier_auto_search_uses_provider_hints_when_sources_missing() -> None:
    index_dir = TEST_TMP / "auto-search-index"
    index_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = index_dir / "STM32F407VGTx-datasheet.pdf"
    shutil.copy2(REPO_ROOT / "tests" / "fixtures" / "docs" / "sample-datasheet.pdf", pdf_path)
    index = index_dir / "index.html"
    index.write_text(f'<html><a href="{pdf_path.resolve().as_uri()}">STM32F407VGTx datasheet</a></html>', encoding="utf-8")
    out_dir = TEST_TMP / "chip" / "STM32F407VGTx-auto-search-test"
    original_hints = chip_dossier.vendor_search_hints
    chip_dossier.vendor_search_hints = lambda part: [index.as_uri()]
    try:
        dossier = chip_dossier.search_and_download_documents(
            part="STM32F407VGTx",
            out_dir=out_dir,
            search_sources=[],
        )
    finally:
        chip_dossier.vendor_search_hints = original_hints
    require(dossier["search"]["auto_search"], "empty search sources should use provider hints")
    require(dossier["search"]["search_sources"] == [index.as_uri()], "auto search should record effective provider hint sources")
    require(dossier["download_results"][0]["status"] == "downloaded", "auto search should download discovered PDF")
    cleanup_dir(out_dir)
    cleanup_dir(index_dir)


def test_document_search_api_presets_and_missing_provider_status() -> None:
    risk_query = document_search_api.build_query("STM32F407VGTx", preset="part-risk")
    result = document_search_api.search_documents("STM32F407VGTx", providers=["exa"], env={})
    require("lifecycle" in risk_query, "part-risk preset should add lifecycle terms")
    require(result["status"] == "api-not-configured", "explicit provider without key should report api-not-configured")
    require(result["providers"][0]["status"] == "api-not-configured", "provider result should preserve config status")


def test_chip_dossier_api_search_falls_back_to_vendor_hints() -> None:
    index_dir = TEST_TMP / "api-search-fallback-index"
    index_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = index_dir / "STM32F407VGTx-datasheet.pdf"
    shutil.copy2(REPO_ROOT / "tests" / "fixtures" / "docs" / "sample-datasheet.pdf", pdf_path)
    index = index_dir / "index.html"
    index.write_text(f'<html><a href="{pdf_path.resolve().as_uri()}">STM32F407VGTx datasheet</a></html>', encoding="utf-8")
    out_dir = TEST_TMP / "chip" / "STM32F407VGTx-api-search-fallback-test"
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
            part="STM32F407VGTx",
            out_dir=out_dir,
            search_sources=[],
            api_search=True,
        )
    finally:
        chip_dossier.vendor_search_hints = original_hints
        chip_dossier.document_search_api.search_documents = original_search
    require(dossier["search"]["api_search"]["status"] == "api-not-configured", "API search status should be recorded")
    require(dossier["search"]["search_sources"] == [index.as_uri()], "empty API results should fall back to vendor hints")
    require(dossier["download_results"][0]["status"] == "downloaded", "fallback PDF should be downloaded")
    cleanup_dir(out_dir)
    cleanup_dir(index_dir)


def test_cubemx_pin_advisor_gpio() -> None:
    advice = cubemx_config_advisor.advise(FIXTURE, pin="PD12", function="gpio-output")
    require(advice["status"] == "ok", "PD12 advice should be available")
    require(advice["pin"]["name"] == "PD12", "pin name should be preserved")
    require(advice["pin"]["configured_signal"] == "GPIO_Output", "PD12 signal should be parsed")
    settings = {item["setting"]: item["recommendation"] for item in advice["required_settings"]}
    require(settings["GPIO mode"] == "Output Push Pull", "GPIO output should recommend push-pull")
    require(any("current" in risk["risk"].lower() for risk in advice["risks"]), "GPIO output should warn about current")


def test_cubemx_pin_advisor_missing_pin() -> None:
    advice = cubemx_config_advisor.advise(FIXTURE, pin="PB9", function="i2c")
    require(advice["status"] == "needs-configuration", "missing pin should need configuration")
    require(advice["pin"]["name"] == "PB9", "missing pin name should be reported")
    require(any(item["setting"] == "GPIO output type" for item in advice["required_settings"]), "I2C should recommend open-drain")


def test_cubemx_pin_advisor_package_evidence_verified() -> None:
    project = copy_fixture_project("pin-evidence-verified")
    evidence = project / "pin-capabilities.json"
    evidence.write_text(
        json_text(
            {
                "schema_version": 1,
                "part": "STM32F407VGTx",
                "package": "LQFP100",
                "source": {"document": "datasheet", "revision": "rev-test", "page": "table-9"},
                "pins": {
                    "PB7": {
                        "signals": [
                            {"name": "I2C1_SDA", "function": "i2c", "af": "AF4", "evidence": "datasheet table-9"},
                            {"name": "USART1_RX", "function": "uart", "af": "AF7", "evidence": "datasheet table-9"},
                        ],
                        "notes": ["5V tolerance not proven by this fixture"],
                    }
                },
            }
        ),
        encoding="utf-8-sig",
    )
    advice = cubemx_config_advisor.advise(project, pin="PB7", function="i2c", pin_evidence=str(evidence))
    capability = advice["pin_capability_evidence"]
    require(capability["verification_status"] == "verified", "I2C evidence should verify PB7")
    require(capability["support_status"] == "supported", "verified pin should be supported")
    require(capability["available"] is True, "verified pin should be available")
    require(capability["matching_signals"][0]["name"] == "I2C1_SDA", "matching signal should be exposed")
    require(capability["source"]["document"] == "datasheet", "source metadata should be preserved")
    markdown = cubemx_config_advisor.render_markdown(advice)
    require("## Pin Capability Evidence" in markdown and "verified" in markdown, "markdown should expose pin evidence")


def test_cubemx_pin_advisor_package_evidence_relative_to_cwd() -> None:
    project = copy_fixture_project("pin-evidence-relative")
    evidence_dir = Path.cwd() / "tests" / "tmp" / "hardware-butler-cwd-evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence = evidence_dir / "pin-capabilities.json"
    evidence.write_text(
        json_text(
            {
                "schema_version": 1,
                "part": "STM32F407VGTx",
                "package": "LQFP100",
                "pins": {"PB7": {"signals": [{"name": "I2C1_SDA", "function": "i2c", "af": "AF4"}]}},
            }
        ),
        encoding="utf-8",
    )
    relative = str(evidence.relative_to(Path.cwd()))
    advice = cubemx_config_advisor.advise(project, pin="PB7", function="i2c", pin_evidence=relative)
    require(advice["pin_capability_evidence"]["verification_status"] == "verified", "cwd-relative evidence path should load")


def test_cubemx_pin_advisor_package_evidence_contradiction() -> None:
    project = copy_fixture_project("pin-evidence-contradicted")
    evidence = project / "pin-capabilities.json"
    evidence.write_text(
        json_text(
            {
                "schema_version": 1,
                "part": "STM32F407VGTx",
                "package": "LQFP100",
                "source": {"document": "datasheet"},
                "pins": {"PB7": {"signals": [{"name": "USART1_RX", "function": "uart", "af": "AF7"}]}},
            }
        ),
        encoding="utf-8",
    )
    advice = cubemx_config_advisor.advise(project, pin="PB7", function="i2c", pin_evidence=str(evidence))
    capability = advice["pin_capability_evidence"]
    require(advice["status"] == "conflict", "contradicted evidence should make advice conflict")
    require(capability["verification_status"] == "contradicted", "missing requested function should be contradicted")
    require(capability["support_status"] == "not-supported-by-evidence", "contradiction should be explicit")
    require(any(item["conflict"] == "pin_capability_mismatch" for item in advice["conflicts"]), "pin capability mismatch conflict missing")


def test_cubemx_pin_advisor_package_evidence_unknown_without_file() -> None:
    advice = cubemx_config_advisor.advise(FIXTURE, pin="PB9", function="i2c")
    capability = advice["pin_capability_evidence"]
    require(capability["verification_status"] == "unknown", "missing evidence file should remain unknown")
    require(capability["support_status"] == "unknown", "missing evidence file should not claim support")
    require(capability["available"] is None, "unknown evidence should not claim availability")


def test_cubemx_pin_advisor_debug_pin_conflict() -> None:
    advice = cubemx_config_advisor.advise(FIXTURE, pin="PA13", function="gpio-output")
    require(advice["status"] == "conflict", "debug pin reuse should be a conflict")
    markdown = cubemx_config_advisor.render_markdown(advice)
    require("## Conflicts" in markdown and "debug_pin" in markdown, "markdown should expose conflicts")
    require("## Alternatives" in markdown, "markdown should expose alternatives")


def test_cubemx_pin_advisor_blocks_multiple_ioc() -> None:
    project = copy_fixture_project("multi-ioc")
    shutil.copy2(project / "Blinky.ioc", project / "Other.ioc")
    try:
        cubemx_config_advisor.advise(project, pin="PD12", function="gpio-output")
    except ValueError as exc:
        require("Multiple CubeMX .ioc files" in str(exc), "multiple IOC error should be explicit")
    else:
        raise AssertionError("multiple IOC projects should require exact .ioc path")


def test_cubemx_ioc_patch_gpio_dry_run_does_not_write() -> None:
    project = copy_fixture_project("ioc-patch-gpio-dry-run")
    ioc = project / "Blinky.ioc"
    before = ioc.read_text(encoding="utf-8")
    patch = cubemx_config_advisor.propose_ioc_patch(
        project,
        function="gpio-output",
        pin="PB9",
        label="APP_OUT",
    )
    require(patch["status"] == "ready-to-write", "GPIO patch should be ready for empty pin")
    keys = {item["key"]: item["value"] for item in patch["proposed_changes"]}
    require(keys["PB9.Signal"] == "GPIO_Output", "GPIO patch should set signal")
    require(keys["PB9.GPIO_InitState"] == "GPIO_PIN_RESET", "GPIO patch should default to safe reset level")
    require("PB9.Signal=GPIO_Output" in patch["diff_preview"], "patch should include diff preview")
    require(patch["backup_path"].endswith(".before-cubemx-patch"), "patch should plan backup path")
    require(ioc.read_text(encoding="utf-8") == before, "dry-run patch must not write .ioc")


def test_cubemx_ioc_patch_blocks_debug_clock_and_occupied_pins() -> None:
    project = copy_fixture_project("ioc-patch-blocks-risk")
    ioc = project / "Blinky.ioc"
    ioc.write_text(ioc.read_text(encoding="utf-8").rstrip() + "\nPH0.Signal=RCC_OSC_IN\n", encoding="utf-8")
    before = ioc.read_text(encoding="utf-8")
    debug_patch = cubemx_config_advisor.propose_ioc_patch(project, function="gpio-output", pin="PA13")
    clock_patch = cubemx_config_advisor.propose_ioc_patch(project, function="gpio-output", pin="PH0")
    occupied_patch = cubemx_config_advisor.propose_ioc_patch(
        project,
        function="i2c",
        instance="I2C1",
        scl_pin="PB6",
        sda_pin="PD12",
    )
    require(debug_patch["status"] == "blocked-conflict", "debug pin patch should be blocked")
    require(clock_patch["status"] == "blocked-conflict", "clock pin patch should be blocked")
    require(occupied_patch["status"] == "blocked-conflict", "I2C patch should block occupied SDA pin")
    require(ioc.read_text(encoding="utf-8") == before, "blocked patches must not write .ioc")


def test_cubemx_ioc_patch_i2c_requires_complete_bus() -> None:
    project = copy_fixture_project("ioc-patch-i2c-required")
    missing_instance = cubemx_config_advisor.propose_ioc_patch(
        project,
        function="i2c",
        scl_pin="PB6",
        sda_pin="PB7",
    )
    missing_pin = cubemx_config_advisor.propose_ioc_patch(
        project,
        function="i2c",
        instance="I2C1",
        sda_pin="PB7",
    )
    require(missing_instance["status"] == "blocked-missing_instance", "I2C patch should require instance")
    require(missing_pin["status"] == "blocked-missing_i2c_pins", "I2C patch should require both SCL and SDA")


def test_cubemx_ioc_patch_i2c_write_requires_confirmation_and_creates_backup() -> None:
    project = copy_fixture_project("ioc-patch-i2c-write")
    ioc = project / "Blinky.ioc"
    before = ioc.read_text(encoding="utf-8")
    patch = cubemx_config_advisor.propose_ioc_patch(
        project,
        function="i2c",
        instance="I2C1",
        scl_pin="PB6",
        sda_pin="PB7",
        timing="0x00C0EAFF",
    )
    keys = {item["key"]: item["value"] for item in patch["proposed_changes"]}
    require(keys["PB6.Signal"] == "I2C1_SCL", "I2C patch should set SCL")
    require(keys["PB7.Signal"] == "I2C1_SDA", "I2C patch should set SDA")
    require(keys["PB6.GPIO_OType"] == "GPIO_OType_OD", "I2C SCL should be open-drain")
    try:
        cubemx_config_advisor.write_ioc_patch(patch, confirm_write=False)
    except ValueError as exc:
        require("--confirm-write" in str(exc), "write guard should mention confirm-write")
    else:
        raise AssertionError("writing .ioc patch should require confirm-write")
    result = cubemx_config_advisor.write_ioc_patch(patch, confirm_write=True)
    require(result["status"] == "written", "confirmed .ioc patch should write")
    require((project / "Blinky.ioc.before-cubemx-patch").read_text(encoding="utf-8") == before, "write should create backup with original content")
    summary = cubemx_config_advisor.cubemx_ioc_summary.summarize(ioc)
    require(summary["normalized_pins"]["PB6"]["function_class"] == "i2c", "SCL should summarize as I2C")
    require(summary["normalized_pins"]["PB7"]["function_class"] == "i2c", "SDA should summarize as I2C")


def test_cubemx_ioc_patch_write_revalidates_current_state() -> None:
    project = copy_fixture_project("ioc-patch-toctou")
    ioc = project / "Blinky.ioc"
    patch = cubemx_config_advisor.propose_ioc_patch(
        project,
        function="i2c",
        instance="I2C1",
        scl_pin="PB6",
        sda_pin="PB7",
    )
    require(patch["status"] == "ready-to-write", "I2C patch should start ready")
    ioc.write_text(ioc.read_text(encoding="utf-8").rstrip() + "\nPB6.Signal=USART2_TX\n", encoding="utf-8")
    try:
        cubemx_config_advisor.write_ioc_patch(patch, confirm_write=True)
    except ValueError as exc:
        require("changed since preview" in str(exc), "TOCTOU guard should mention changed preview state")
    else:
        raise AssertionError("write_ioc_patch should revalidate current .ioc state before writing")
    require("PB6.Signal=USART2_TX" in ioc.read_text(encoding="utf-8"), "TOCTOU guard must not overwrite changed pin state")
    require(not (project / "Blinky.ioc.before-cubemx-patch").exists(), "blocked TOCTOU write must not create backup")


def test_hardware_action_plan_flash_requires_confirmation() -> None:
    plan = hardware_action_plan.plan_action(
        root=FIXTURE,
        action="flash",
        target="STM32F407VGTx",
        probe="ST-Link",
        voltage="3.3V",
        current_limit="100mA",
        erase_scope="firmware image only",
        recovery="SWD under reset",
    )
    require(plan["status"] == "ready-for-user-confirmation", "complete flash plan should still require confirmation")
    require(plan["hardware_side_effect"], "flash should be marked as hardware side effect")
    require(plan["confirmation_token"].startswith("hwc1-"), "complete hardware plan should include scoped token")
    require("execute" not in plan, "action plan must not execute hardware action")


def test_hardware_action_plan_build_flash_child_token_and_artifact_hash() -> None:
    project = copy_fixture_project("build-flash-child-token")
    artifact = project / "build" / "app.hex"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(":020000040800F2\n:00000001FF\n", encoding="utf-8")
    plan = hardware_action_plan.plan_action(
        root=project,
        action="build-flash",
        target="STM32F407VGTx",
        probe="ST-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        erase_scope="firmware image only",
        recovery="SWD under reset",
        artifact="build/app.hex",
        backend="openocd",
    )
    require(plan["confirmation_record"]["artifact_hash"], "artifact hash should be bound into confirmation record")
    child = plan["child_safety_tokens"][0]
    require(child["action"] == "flash", "build-flash should derive a flash child token")
    gate = safety_gate.check_token(
        "flash",
        child["token"],
        target="STM32F407VGTx",
        probe="ST-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        erase_scope="firmware image only",
        recovery="SWD under reset",
        external_loads="unknown",
        artifact="build/app.hex",
        artifact_hash=plan["confirmation_record"]["artifact_hash"],
        backend="openocd",
    )
    require(gate["allowed"], "child flash token should be valid for embedded safety gate")


def test_hardware_action_plan_child_backend_scope_matrix() -> None:
    cases = [
        ("build-debug", "jlink", "debug", "jlink-gdb"),
        ("build-debug", "openocd", "debug", "openocd-gdb"),
        ("build-debug", "probe-rs", "debug", "probe-rs-gdb"),
        ("observe", "jlink", "observe", "jlink-rtt"),
        ("observe", "openocd", "observe", "openocd-semihosting"),
        ("observe", "probe-rs", "observe", "probe-rs-rtt"),
    ]
    for action, backend, child_action, child_backend in cases:
        plan = hardware_action_plan.plan_action(
            root=FIXTURE,
            action=action,
            target="STM32F407VGTx",
            probe="ST-Link SN123",
            voltage="3.3V",
            current_limit="100mA",
            recovery="SWD under reset",
            backend=backend,
        )
        child = plan["child_safety_tokens"][0]
        require(child["action"] == child_action, f"{action} should derive {child_action} child token")
        require(child["expected_scope"]["backend"] == child_backend, f"{action}/{backend} child backend scope mismatch")


def test_hardware_action_plan_execution_package_workflow_command() -> None:
    project = copy_fixture_project("execution-package-command")
    artifact = project / "build" / "app.hex"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(":020000040800F2\n:00000001FF\n", encoding="utf-8")
    plan = hardware_action_plan.plan_action(
        root=project,
        action="build-flash",
        target="STM32F407VGTx",
        probe="ST-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        erase_scope="firmware image only",
        recovery="SWD under reset",
        artifact="build/app.hex",
        backend="openocd",
    )
    package = plan["execution_package"]
    command = package["workflow_command"]
    argv = command["argv"]
    child = plan["child_safety_tokens"][0]
    require(command["status"] == "prepared-not-executed", "execution package must not run commands")
    require("build-flash" in argv, "workflow command should target build-flash")
    require("--workspace" in argv and str(project.resolve()) in argv, "workflow command should bind workspace")
    require("--flash-backend" in argv and "openocd" in argv, "workflow command should bind flash backend")
    workflow_parent_token = argv[argv.index("--confirm-token") + 1]
    require(workflow_parent_token != plan["confirmation_token"], "workflow command should use embedded safety token, not butler plan token")
    parent_gate = safety_gate.check_token(
        "build-flash",
        workflow_parent_token,
        target="STM32F407VGTx",
        probe="ST-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        erase_scope="firmware image only",
        recovery="SWD under reset",
        external_loads="unknown",
        artifact="build/app.hex",
        artifact_hash=plan["confirmation_record"]["artifact_hash"],
        backend="openocd",
    )
    require(parent_gate["allowed"], "workflow parent token must pass embedded safety gate")
    require("--child-confirm-token" in argv and child["token"] in argv, "workflow command should include child token")
    require("--artifact-hash" in argv and plan["confirmation_record"]["artifact_hash"] in argv, "workflow command should include artifact hash")
    require(package["workflow_parent_token_hash"] == safety_gate.token_hash(workflow_parent_token), "package should expose workflow parent token hash")
    require(package["manual_confirmation"]["artifact_hash"] == plan["confirmation_record"]["artifact_hash"], "manual confirmation should include artifact hash")
    require(command["hardware_side_effect_if_executed"], "prepared workflow command should warn about hardware side effects")


def test_hardware_action_plan_execution_package_observe_backend_command() -> None:
    plan = hardware_action_plan.plan_action(
        root=FIXTURE,
        action="observe",
        target="STM32F407VGTx",
        probe="J-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        recovery="SWD under reset",
        backend="jlink",
    )
    argv = plan["execution_package"]["workflow_command"]["argv"]
    child = plan["child_safety_tokens"][0]
    require("observe" in argv, "workflow command should target observe")
    require("--observe-backend" in argv and "jlink" in argv, "observe command should bind backend")
    require("--child-confirm-token" in argv and child["token"] in argv, "observe command should include child token")
    require(child["expected_scope"]["backend"] == "jlink-rtt", "observe child token should target J-Link RTT")


def test_hardware_action_plan_observe_child_token() -> None:
    plan = hardware_action_plan.plan_action(
        root=FIXTURE,
        action="observe",
        target="STM32F407VGTx",
        probe="ST-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        recovery="SWD under reset",
        backend="workflow-observe-sim",
    )
    require(plan["status"] == "ready-for-user-confirmation", "complete observe plan should require confirmation")
    require(plan["hardware_side_effect"], "observe should be treated as a hardware-side-effect action")
    child = plan["child_safety_tokens"][0]
    require(child["action"] == "observe", "observe should derive an observe child token")
    gate = safety_gate.check_token(
        "observe",
        child["token"],
        target="STM32F407VGTx",
        probe="ST-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        recovery="SWD under reset",
        external_loads="unknown",
        backend="workflow-observe-sim",
    )
    require(gate["allowed"], "child observe token should be valid for embedded safety gate")
    require(any("bounded" in item.lower() for item in plan["preflight_checks"]), "observe plan should include bounded channel preflight")


def test_hardware_action_executor_fake_backend_requires_token() -> None:
    project = copy_fixture_project("fake-backend-token")
    plan = hardware_action_plan.plan_action(
        root=project,
        action="flash",
        target="STM32F407VGTx",
        probe="ST-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        erase_scope="firmware image only",
        recovery="SWD under reset",
        backend="fake",
    )
    blocked = hardware_action_executor.execute_plan(plan, token="bad-token", backend="fake")
    require(blocked["status"] == "blocked-confirmation-required", "bad token should block execution")
    ok = hardware_action_executor.execute_plan(plan, token=plan["confirmation_token"], backend="fake")
    require(ok["status"] == "ok" and ok["backend"] == "fake", "fake backend should accept matching token")
    require(not ok["hardware_side_effect"], "fake backend must not touch hardware")
    replay = hardware_action_executor.execute_plan(plan, token=plan["confirmation_token"], backend="fake")
    require(replay["status"] == "blocked-token-replay", "confirmation token should be one-time use")


def test_hardware_action_executor_rejects_tampered_plan_token() -> None:
    project = copy_fixture_project("tampered-plan-token")
    plan = hardware_action_plan.plan_action(
        root=project,
        action="flash",
        target="STM32F407VGTx",
        probe="ST-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        erase_scope="firmware image only",
        recovery="SWD under reset",
        backend="fake",
    )
    plan["confirmation_token"] = "hwc1-tampered"
    result = hardware_action_executor.execute_plan(plan, token="hwc1-tampered", backend="fake")
    require(result["status"] == "blocked-plan-token-mismatch", "executor must not trust mutable plan token")


def test_hardware_action_executor_rejects_artifact_hash_mismatch() -> None:
    project = copy_fixture_project("artifact-hash-mismatch")
    artifact = project / "firmware.hex"
    artifact.write_text(":00000001FF\n", encoding="utf-8")
    plan = hardware_action_plan.plan_action(
        root=project,
        action="flash",
        target="STM32F407VGTx",
        probe="ST-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        erase_scope="firmware image only",
        recovery="SWD under reset",
        artifact="firmware.hex",
        backend="fake",
    )
    artifact.write_text(":020000040800F2\n:00000001FF\n", encoding="utf-8")
    result = hardware_action_executor.execute_plan(plan, token=plan["confirmation_token"], backend="fake")
    require(result["status"] == "blocked-artifact-hash-mismatch", "changed artifact should block execution")


def test_hardware_action_executor_workflow_build_is_controlled() -> None:
    project = copy_fixture_project("workflow-build-controlled")
    plan = hardware_action_plan.plan_action(
        root=project,
        action="build",
        target="Blinky",
        backend="workflow-build",
    )
    require(plan["controlled_local_action"], "build should be a controlled local action")
    blocked = hardware_action_executor.execute_plan(plan, token="", backend="workflow-build")
    require(blocked["status"] == "blocked-confirmation-required", "controlled build should require token")
    result = hardware_action_executor.execute_plan(plan, token=plan["confirmation_token"], backend="workflow-build")
    require(result["executed"], "workflow build backend should execute after token")
    require(not result["hardware_side_effect"], "workflow build must not be marked as hardware side effect")
    require("log_classification" in result, "build executor should classify output")


def test_hardware_action_executor_workflow_build_flash_sim_consumes_child_token() -> None:
    project = copy_fixture_project("workflow-build-flash-sim")
    artifact = project / "build" / "app.hex"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(":020000040800F2\n:00000001FF\n", encoding="utf-8")
    plan = hardware_action_plan.plan_action(
        root=project,
        action="build-flash",
        target="STM32F407VGTx",
        probe="ST-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        erase_scope="firmware image only",
        recovery="SWD under reset",
        artifact="build/app.hex",
        backend="workflow-build-flash-sim",
    )
    result = hardware_action_executor.execute_plan(
        plan,
        token=plan["confirmation_token"],
        backend="workflow-build-flash-sim",
    )
    require(result["status"] == "ok", "workflow build-flash simulator should complete")
    require(result["child_action"] == "flash", "simulator should consume flash child token")
    require(result["child_audit"]["consumed"], "child token should be audited as consumed")
    events = (project / ".embeddedskills" / "safety-log.jsonl").read_text(encoding="utf-8")
    require("workflow-build-flash-sim" in events, "safety log should include simulator backend")
    audit = hardware_action_audit.audit_report(project)
    require(audit["event_counts"]["token-consumed"] == 2, "audit should show parent and child token consumption")
    require(audit["event_counts"]["execution-result"] >= 1, "audit should show execution result")
    require("workflow-build-flash-sim" in audit["backend_counts"], "audit should summarize simulator backend")
    require(plan["confirmation_record"]["artifact_hash"] in audit["artifact_hashes"], "audit should preserve artifact hash evidence")
    require(plan["confirmation_token"] not in json.dumps(audit, ensure_ascii=False), "audit report must not expose raw parent token")
    require(plan["child_safety_tokens"][0]["token"] not in json.dumps(audit, ensure_ascii=False), "audit report must not expose raw child token")
    replay = hardware_action_executor.execute_plan(
        plan,
        token=plan["confirmation_token"],
        backend="workflow-build-flash-sim",
    )
    require(replay["status"] == "blocked-token-replay", "parent token should remain one-time use")


def test_hardware_action_executor_workflow_observe_sim_consumes_child_token() -> None:
    project = copy_fixture_project("workflow-observe-sim")
    plan = hardware_action_plan.plan_action(
        root=project,
        action="observe",
        target="STM32F407VGTx",
        probe="ST-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        recovery="SWD under reset",
        backend="workflow-observe-sim",
    )
    result = hardware_action_executor.execute_plan(
        plan,
        token=plan["confirmation_token"],
        backend="workflow-observe-sim",
    )
    require(result["status"] == "ok", "workflow observe simulator should complete")
    require(result["child_action"] == "observe", "simulator should consume observe child token")
    require(result["child_audit"]["consumed"], "child observe token should be audited as consumed")
    require(result["observe_samples_count"] == 2, "observe simulator should emit bounded samples")
    require(not result["hardware_side_effect"], "observe simulator must not touch hardware")
    events = [
        line
        for line in (project / ".embeddedskills" / "safety-log.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    require(any("workflow-observe-sim" in line for line in events), "safety log should include observe simulator backend")
    require(any('"action": "observe"' in line and '"event": "token-consumed"' in line for line in events), "safety log should include observe token consumption")
    require(any('"observe_samples_count": 2' in line and '"event": "execution-result"' in line for line in events), "execution audit should include observe sample count")
    replay = hardware_action_executor.execute_plan(
        plan,
        token=plan["confirmation_token"],
        backend="workflow-observe-sim",
    )
    require(replay["status"] == "blocked-token-replay", "observe parent token should remain one-time use")


def test_hardware_action_executor_bench_preflight_does_not_consume_token() -> None:
    project = copy_fixture_project("bench-preflight")
    plan = hardware_action_plan.plan_action(
        root=project,
        action="observe",
        target="STM32F407VGTx",
        probe="ST-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        recovery="SWD under reset",
        backend="workflow-observe-sim",
    )
    preflight = hardware_action_executor.execute_plan(
        plan,
        token=plan["confirmation_token"],
        backend="bench-preflight",
    )
    require(preflight["status"] == "ok", "simulation bench preflight should pass")
    require(not preflight["executed"], "bench preflight must not execute commands")
    require(not preflight["token_consumed"], "bench preflight must not consume parent token")
    checks = {item["name"]: item["status"] for item in preflight["checks"]}
    require(checks["argv_has_parent_token"] == "ok", "preflight should verify parent token in argv")
    require(checks["argv_has_child_token"] == "ok", "preflight should verify child token in argv")
    require(checks["argv_action_matches_plan"] == "ok", "preflight should verify workflow action")
    require(checks["argv_json_enabled"] == "ok", "preflight should require JSON output")
    require("argv" not in preflight["workflow_command"], "bench preflight must not expose raw argv")
    require("<redacted>" in preflight["workflow_command"]["argv_redacted"], "bench preflight should redact token argv values")
    require("hwc1-" not in json.dumps(preflight, ensure_ascii=False), "bench preflight must not leak confirmation token values")
    require(not (project / ".embeddedskills" / "safety-log.jsonl").exists(), "bench preflight must not write safety log")
    result = hardware_action_executor.execute_plan(
        plan,
        token=plan["confirmation_token"],
        backend="workflow-observe-sim",
    )
    require(result["status"] == "ok", "preflight must leave token usable for execution")


def test_hardware_action_executor_bench_preflight_validates_real_command_package() -> None:
    project = copy_fixture_project("bench-preflight-real-package")
    artifact = project / "build" / "app.hex"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(":020000040800F2\n:00000001FF\n", encoding="utf-8")
    plan = hardware_action_plan.plan_action(
        root=project,
        action="build-flash",
        target="STM32F407VGTx",
        probe="ST-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        erase_scope="firmware image only",
        recovery="SWD under reset",
        artifact="build/app.hex",
        backend="openocd",
    )
    preflight = hardware_action_executor.execute_plan(
        plan,
        token=plan["confirmation_token"],
        backend="workflow-command-package",
    )
    require(preflight["status"] in {"ok", "warning"}, "real backend command package should have no blocking preflight errors")
    checks = {item["name"]: item["status"] for item in preflight["checks"]}
    require(checks["argv_artifact_hash_matches_plan"] == "ok", "preflight should verify artifact hash flags")
    require(checks["argv_backend_matches_plan"] == "ok", "preflight should verify backend flag")
    require(checks["argv_flags_known"] == "ok", "preflight should reject unknown workflow flags")
    require(checks["backend_tool_available"] in {"ok", "warn"}, "missing hardware tool should be a preflight warning")
    require(not preflight["hardware_side_effect"], "command package preflight must not touch hardware")


def test_bench_runbook_aggregates_preflight_and_redacts_tokens_without_side_effects() -> None:
    project = copy_fixture_project("bench-runbook-build-flash")
    embedded = project / ".embeddedskills"
    artifact = project / "build" / "app.hex"
    debug = project / "build" / "app.elf"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(":020000040800F2\n:00000001FF\n", encoding="utf-8")
    debug.write_text("ELF fixture\n", encoding="utf-8")
    hardware_action_plan.artifact_sha256(project, "build/app.hex")
    config_path = embedded / "config.json"
    state_path = embedded / "state.json"
    config_path.write_text(
        json_text(
            {
                "workflow": {
                    "preferred_flash": "openocd",
                    "preferred_debug": "openocd",
                    "preferred_observe": "openocd",
                },
                "openocd": {
                    "interface": "stlink.cfg",
                    "target": "stm32f4x.cfg",
                },
            }
        ),
        encoding="utf-8",
    )
    state_path.write_text(
        json_text(
            {
                "last_build": {
                    "flash_file": "build/app.hex",
                    "debug_file": "build/app.elf",
                    "artifacts": {
                        "flash_file": "build/app.hex",
                        "debug_file": "build/app.elf",
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    before_config = config_path.read_text(encoding="utf-8")
    before_state = state_path.read_text(encoding="utf-8")
    runbook = bench_runbook.generate_runbook(
        project,
        action="build-flash",
        target="STM32F407VGTx",
        probe="ST-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        erase_scope="firmware image only",
        recovery="SWD under reset",
        backend="openocd",
    )
    serialized = json.dumps(runbook, ensure_ascii=False)
    parent_token_hash = runbook["action_plan"]["confirmation_token_hash"]
    child_token_hash = runbook["action_plan"]["child_safety_tokens"][0]["token_hash"]
    require(runbook["status"] in {"ready-for-manual-confirmation", "ready-with-bench-warnings"}, "runbook should be ready or warning-only")
    require(not runbook["executed"], "runbook must not execute")
    require(not runbook["token_consumed"], "runbook must not consume token")
    require(runbook["bench_readiness"]["artifacts"]["flash_exists"], "runbook should include bench readiness artifact evidence")
    require(runbook["bench_preflight"]["token_consumed"] is False, "preflight in runbook must not consume token")
    require(runbook["manual_confirmation"]["artifact"] == "build/app.hex", "runbook should use state flash artifact by default")
    require(runbook["manual_confirmation"]["artifact_hash"], "runbook should include artifact hash evidence")
    require("--dry-run" in runbook["workflow_dry_run"]["argv_redacted"], "runbook should expose workflow dry-run argv")
    require("<redacted>" in runbook["workflow_dry_run"]["argv_redacted"], "runbook dry-run argv should redact tokens")
    require(runbook["workflow_dry_run"]["executed"], "runbook should execute workflow dry-run subprocess")
    require(runbook["workflow_dry_run"]["returncode"] == 0, "workflow dry-run subprocess should succeed")
    require(runbook["workflow_dry_run"]["parsed_result"]["status"] == "ok", "runbook should parse workflow dry-run JSON")
    require(runbook["workflow_dry_run"]["parsed_result"]["details"]["dry_run_controls"]["token_consumed"] is False, "workflow dry-run must report no token consumption")
    require(runbook["workflow_dry_run"]["side_effect_check"]["unchanged"], "workflow dry-run must leave config/state/safety-log unchanged")
    require("stdout_tail" not in runbook["workflow_dry_run"] and "stdout_redacted_tail" not in runbook["workflow_dry_run"], "runbook must not expose stdout text")
    require("stderr_tail" not in runbook["workflow_dry_run"] and "stderr_redacted_tail" not in runbook["workflow_dry_run"], "runbook must not expose stderr text")
    require("argv" not in runbook["bench_preflight"]["workflow_command"], "runbook preflight must not expose raw argv")
    require(parent_token_hash and child_token_hash, "runbook should expose token hashes for audit without token values")
    require(parent_token_hash not in {"<redacted>", ""}, "parent token hash should be present")
    require("hwc1-" not in serialized, "runbook must not leak real token values")
    require('"argv":' not in serialized, "runbook must not expose raw argv keys")
    require(config_path.read_text(encoding="utf-8") == before_config, "runbook must not write config")
    require(state_path.read_text(encoding="utf-8") == before_state, "runbook must not write state")
    require(not (embedded / "safety-log.jsonl").exists(), "runbook must not create safety log")


def test_bench_runbook_reports_real_workflow_dry_run_error_without_side_effects() -> None:
    project = copy_fixture_project("bench-runbook-workflow-dry-run-error")
    embedded = project / ".embeddedskills"
    artifact = project / "build" / "app-a.hex"
    state_artifact = project / "build" / "app-b.hex"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(":020000040800F2\n:00000001FF\n", encoding="utf-8")
    state_artifact.write_text(":020000040801F1\n:00000001FF\n", encoding="utf-8")
    config_path = embedded / "config.json"
    state_path = embedded / "state.json"
    config_path.write_text(
        json_text(
            {
                "workflow": {
                    "preferred_build": "keil",
                    "preferred_flash": "openocd",
                },
                "keil": {
                    "project": str((project / "Blinky.uvprojx").resolve()),
                    "target": "Blinky",
                    "log_dir": ".embeddedskills/build",
                },
                "openocd": {
                    "interface": "stlink.cfg",
                    "target": "stm32f4x.cfg",
                },
            }
        ),
        encoding="utf-8",
    )
    state_path.write_text(json_text({"last_build": {"flash_file": "build/app-b.hex"}}), encoding="utf-8")
    before_config = config_path.read_text(encoding="utf-8")
    before_state = state_path.read_text(encoding="utf-8")
    runbook = bench_runbook.generate_runbook(
        project,
        action="build-flash",
        target="STM32F407VGTx",
        probe="ST-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        erase_scope="firmware image only",
        recovery="SWD under reset",
        backend="openocd",
        artifact="build/app-a.hex",
    )
    dry_run = runbook["workflow_dry_run"]
    serialized = json.dumps(runbook, ensure_ascii=False)
    require(runbook["status"] == "blocked-workflow-dry-run-failed", "runbook should block when actual workflow dry-run fails")
    require(dry_run["status"] == "error", "workflow dry-run error should be reported")
    require(dry_run["executed"], "runbook should execute workflow dry-run even when it fails")
    require(dry_run["parsed_result"]["status"] == "error", "workflow dry-run failure should be detected from parsed JSON status")
    require(dry_run["parsed_result"]["error"]["code"] == "artifact_mismatch", "workflow dry-run should report artifact mismatch")
    require("hwc1-" not in serialized, "failed workflow dry-run must not leak token values")
    require("argv" not in dry_run, "failed workflow dry-run must not expose raw argv")
    require('"argv":' not in serialized, "failed workflow dry-run must not expose raw argv keys")
    require("stdout_tail" not in dry_run and "stderr_tail" not in dry_run, "failed workflow dry-run must not expose raw stdout/stderr")
    require("stdout_redacted_tail" not in dry_run and "stderr_redacted_tail" not in dry_run, "failed workflow dry-run must not expose stdout/stderr text")
    require(dry_run["side_effect_check"]["unchanged"], "failed workflow dry-run must report unchanged side-effect files")
    require(config_path.read_text(encoding="utf-8") == before_config, "failed workflow dry-run must not write config")
    require(state_path.read_text(encoding="utf-8") == before_state, "failed workflow dry-run must not write state")
    require(not (embedded / "safety-log.jsonl").exists(), "failed workflow dry-run must not write safety log")


def test_bench_runbook_refuses_unsafe_workflow_dry_run_subprocess() -> None:
    project = copy_fixture_project("bench-runbook-unsafe-dry-run")
    embedded = project / ".embeddedskills"
    result = bench_runbook.execute_workflow_dry_run(
        project,
        [sys.executable, str(EMBEDDED_DIR / "workflow" / "scripts" / "workflow_run.py"), "build-flash", "--json"],
    )
    require(result["status"] == "blocked-workflow-dry-run-unsafe", "runbook should refuse workflow subprocess without --dry-run")
    require(not result["executed"], "unsafe workflow dry-run should not start subprocess")
    require(not (embedded / "safety-log.jsonl").exists(), "unsafe workflow dry-run must not write safety log")


def test_bench_runbook_refuses_missing_json_and_untrusted_workflow_argv() -> None:
    project = copy_fixture_project("bench-runbook-untrusted-dry-run")
    embedded = project / ".embeddedskills"
    trusted = EMBEDDED_DIR / "workflow" / "scripts" / "workflow_run.py"
    original_run = bench_runbook.subprocess.run

    def fail_if_called(*args, **kwargs):
        raise AssertionError("untrusted workflow argv should not start subprocess")

    missing_json = bench_runbook.execute_workflow_dry_run(
        project,
        [sys.executable, str(trusted), "build-flash", "--dry-run"],
    )
    require(missing_json["status"] == "blocked-workflow-dry-run-unsafe", "runbook should require --json before starting subprocess")
    require(not missing_json["executed"], "missing --json dry-run should not start subprocess")
    untrusted = bench_runbook.execute_workflow_dry_run(
        project,
        [sys.executable, str(project / "workflow_run.py"), "build-flash", "--dry-run", "--json"],
    )
    require(untrusted["status"] == "blocked-workflow-dry-run-untrusted-argv", "runbook should require trusted workflow_run.py path")
    require(not untrusted["executed"], "untrusted workflow argv should not start subprocess")
    bench_runbook.subprocess.run = fail_if_called
    try:
        smuggled = bench_runbook.execute_workflow_dry_run(
            project,
            [sys.executable, str(project / "attacker.py"), str(trusted), "build-flash", "--dry-run", "--json"],
        )
    finally:
        bench_runbook.subprocess.run = original_run
    require(smuggled["status"] == "blocked-workflow-dry-run-untrusted-argv", "trusted workflow_run.py must be the executed script, not a later argv value")
    require(not smuggled["executed"], "smuggled trusted path should not start subprocess")
    require(not (embedded / "safety-log.jsonl").exists(), "blocked dry-run must not write safety log")


def test_bench_runbook_preflight_failure_blocks_workflow_subprocess() -> None:
    project = copy_fixture_project("bench-runbook-preflight-block")
    trusted = EMBEDDED_DIR / "workflow" / "scripts" / "workflow_run.py"
    original_run = bench_runbook.subprocess.run

    def fail_if_called(*args, **kwargs):
        raise AssertionError("workflow dry-run subprocess should not start after blocked preflight")

    bench_runbook.subprocess.run = fail_if_called
    try:
        result = bench_runbook.execute_workflow_dry_run(
            project,
            [sys.executable, str(trusted), "build-flash", "--dry-run", "--json"],
            preflight={"status": "blocked-preflight-failed"},
        )
    finally:
        bench_runbook.subprocess.run = original_run
    require(result["status"] == "blocked-workflow-dry-run-preflight", "blocked preflight should block workflow dry-run subprocess")
    require(not result["executed"], "blocked preflight should not execute subprocess")


def test_bench_runbook_rejects_invalid_json_or_missing_dry_run_controls() -> None:
    project = copy_fixture_project("bench-runbook-invalid-json")
    trusted = EMBEDDED_DIR / "workflow" / "scripts" / "workflow_run.py"
    argv = [sys.executable, str(trusted), "build-flash", "--dry-run", "--json"]
    original_run = bench_runbook.subprocess.run

    class FakeProc:
        def __init__(self, stdout: str):
            self.returncode = 0
            self.stdout = stdout
            self.stderr = ""

    cases = [
        ("not-json", "invalid JSON should block even with returncode 0"),
        (json_text({"status": "ok", "details": {}}), "missing dry_run_controls should block"),
        (
            json_text(
                {
                    "status": "ok",
                    "details": {
                        "dry_run_controls": {
                            "dry_run": True,
                            "executed": False,
                            "hardware_side_effect": False,
                            "token_consumed": True,
                            "state_written": False,
                            "config_written": False,
                            "safety_log_written": False,
                        }
                    },
                }
            ),
            "token_consumed true should block",
        ),
    ]
    try:
        for stdout, message in cases:
            bench_runbook.subprocess.run = lambda *args, _stdout=stdout, **kwargs: FakeProc(_stdout)
            result = bench_runbook.execute_workflow_dry_run(project, argv)
            require(result["status"] == "error", message)
            require(result["executed"], "trusted dry-run subprocess should be marked executed for invalid result checks")
    finally:
        bench_runbook.subprocess.run = original_run


def test_bench_runbook_sanitizes_nested_stdout_stderr_and_argv() -> None:
    project = copy_fixture_project("bench-runbook-sanitize-nested")
    trusted = EMBEDDED_DIR / "workflow" / "scripts" / "workflow_run.py"
    argv = [sys.executable, str(trusted), "build-flash", "--dry-run", "--json"]
    payload = {
        "status": "error",
        "stdout": "hwc1-leaked-parent",
        "stderr_tail": "hwc1-leaked-child",
        "argv": ["raw", "argv"],
        "confirm_token": "plain-secret-token",
        "details": {
            "dry_run_controls": {
                "dry_run": True,
                "executed": False,
                "hardware_side_effect": False,
                "token_consumed": False,
                "state_written": False,
                "config_written": False,
                "safety_log_written": False,
                "child_confirm_token": "plain-child-secret",
            },
            "nested": {
                "raw_stdout": "secret output",
                "raw_stderr": "secret error",
                "argv": ["raw"],
                "token": "plain-nested-secret",
                "safe": "hwc1-token-in-string",
            },
        },
    }
    original_run = bench_runbook.subprocess.run

    class FakeProc:
        returncode = 1
        stdout = json_text(payload)
        stderr = ""

    bench_runbook.subprocess.run = lambda *args, **kwargs: FakeProc()
    try:
        result = bench_runbook.execute_workflow_dry_run(project, argv)
    finally:
        bench_runbook.subprocess.run = original_run
    serialized = json.dumps(result, ensure_ascii=False)
    require(result["status"] == "error", "workflow dry-run error should still be reported")
    require("stdout" not in result["parsed_result"], "top-level stdout should be removed from parsed_result")
    require("stderr_tail" not in result["parsed_result"], "top-level stderr_tail should be removed from parsed_result")
    require("argv" not in result["parsed_result"], "top-level argv should be removed from parsed_result")
    require("confirm_token" not in result["parsed_result"], "top-level token fields should be removed from parsed_result")
    require("raw_stdout" not in result["parsed_result"]["details"]["nested"], "nested stdout fields should be removed")
    require("raw_stderr" not in result["parsed_result"]["details"]["nested"], "nested stderr fields should be removed")
    require("token" not in result["parsed_result"]["details"]["nested"], "nested token fields should be removed")
    require("plain-child-secret" not in serialized, "dry_run_controls should not leak extra token fields")
    require("plain-secret-token" not in serialized, "plain token fields should not leak")
    require("plain-nested-secret" not in serialized, "nested plain token fields should not leak")
    require("hwc1-token-in-string" not in serialized, "nested token-like strings should be redacted")
    require("hwc1-<redacted>" in serialized, "redacted token marker should be retained")


def test_bench_runbook_blocks_missing_safety_input_without_side_effects() -> None:
    project = copy_fixture_project("bench-runbook-missing-input")
    embedded = project / ".embeddedskills"
    before_state_exists = (embedded / "state.json").exists()
    runbook = bench_runbook.generate_runbook(
        project,
        action="build-flash",
        target="STM32F407VGTx",
    )
    require(runbook["status"] == "blocked-missing-safety-input", "runbook should surface missing safety inputs")
    require("probe" in runbook["action_plan"]["missing_inputs"], "runbook should include missing probe input")
    require(runbook["workflow_dry_run"]["status"] == "not-available", "blocked runbook should not prepare workflow argv")
    require(not (embedded / "safety-log.jsonl").exists(), "blocked runbook must not create safety log")
    require((embedded / "state.json").exists() == before_state_exists, "blocked runbook must not write state")


def test_workflow_dry_run_build_flash_prepares_commands_without_side_effects() -> None:
    project = copy_fixture_project("workflow-dry-run-build-flash")
    embedded = project / ".embeddedskills"
    artifact = project / "build" / "app.hex"
    debug = project / "build" / "app.elf"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(":020000040800F2\n:00000001FF\n", encoding="utf-8")
    debug.write_text("ELF fixture\n", encoding="utf-8")
    artifact_hash = hardware_action_plan.artifact_sha256(project, "build/app.hex")
    config_path = embedded / "config.json"
    state_path = embedded / "state.json"
    config_path.write_text(
        json_text(
            {
                "workflow": {
                    "preferred_build": "keil",
                    "preferred_flash": "openocd",
                },
                "keil": {
                    "project": "Blinky.uvprojx",
                    "target": "Blinky",
                    "log_dir": ".embeddedskills/build",
                },
                "openocd": {
                    "interface": "stlink.cfg",
                    "target": "stm32f4x.cfg",
                },
            }
        ),
        encoding="utf-8",
    )
    state_path.write_text(
        json_text(
            {
                "last_build": {
                    "flash_file": "build/app.hex",
                    "debug_file": "build/app.elf",
                    "artifacts": {
                        "flash_file": "build/app.hex",
                        "debug_file": "build/app.elf",
                    },
                },
                "sentinel": {"value": "must-not-change"},
            }
        ),
        encoding="utf-8",
    )
    before_config = config_path.read_text(encoding="utf-8")
    before_state = state_path.read_text(encoding="utf-8")

    result = run_workflow_json(
        [
            "build-flash",
            "--workspace",
            str(project),
            "--flash-backend",
            "openocd",
            "--dry-run",
            "--json",
            "--child-confirm-token",
            "child-token",
            "--target",
            "STM32F407VGTx",
            "--probe",
            "ST-Link SN123",
            "--voltage",
            "3.3V",
            "--current-limit",
            "100mA",
            "--erase-scope",
            "firmware image only",
            "--recovery",
            "SWD under reset",
            "--artifact",
            "build/app.hex",
            "--artifact-hash",
            artifact_hash,
            "--child-artifact-hash",
            artifact_hash,
        ],
        cwd=REPO_ROOT,
    )

    require(result["status"] == "ok", "build-flash dry-run should prepare commands")
    build = result["details"]["build"]["details"]
    flash = result["details"]["flash"]["details"]
    require(build["dry_run"] and flash["dry_run"], "dry-run details should be marked")
    build_argv = build["command"]["argv_redacted"]
    flash_argv = flash["command"]["argv_redacted"]
    require(any(str(item).endswith("keil_build.py") for item in build_argv), "build dry-run should expose Keil command")
    require(any(str(item).endswith("openocd_run.py") for item in flash_argv), "flash dry-run should expose OpenOCD command")
    require("--confirm-token" in flash_argv and "<redacted>" in flash_argv, "flash dry-run should redact child token")
    require("child-token" not in json.dumps(result, ensure_ascii=False), "dry-run output must not leak child token")
    require(flash["command"]["safety_args_present"]["confirm_token"], "flash dry-run should report safety token presence")
    require(flash["artifact_source"] == "state.last_build.flash_file", "flash dry-run should identify artifact source")
    require(flash["artifact_hash_verified"] == artifact_hash, "flash dry-run should verify current artifact hash")
    require(flash["hardware_side_effect_if_executed"], "flash command should warn about hardware side effects")
    require(result["details"]["dry_run_controls"]["token_consumed"] is False, "dry-run should report no token consumption")
    require(config_path.read_text(encoding="utf-8") == before_config, "dry-run must not write config preferences")
    require(state_path.read_text(encoding="utf-8") == before_state, "dry-run must not update workflow state")
    require(not (embedded / "safety-log.jsonl").exists(), "dry-run must not consume safety tokens")


def test_workflow_dry_run_observe_prepares_command_without_token_consumption() -> None:
    project = copy_fixture_project("workflow-dry-run-observe")
    embedded = project / ".embeddedskills"
    config_path = embedded / "config.json"
    state_path = embedded / "state.json"
    config_path.write_text(
        json_text(
            {
                "workflow": {
                    "preferred_observe": "openocd",
                },
                "openocd": {
                    "interface": "stlink.cfg",
                    "target": "stm32f4x.cfg",
                },
            }
        ),
        encoding="utf-8",
    )
    state_path.write_text(json_text({"sentinel": {"value": "must-not-change"}}), encoding="utf-8")
    before_state = state_path.read_text(encoding="utf-8")

    result = run_workflow_json(
        [
            "observe",
            "--workspace",
            str(project),
            "--observe-backend",
            "openocd",
            "--dry-run",
            "--json",
            "--child-confirm-token",
            "observe-token",
            "--target",
            "STM32F407VGTx",
            "--probe",
            "ST-Link SN123",
            "--voltage",
            "3.3V",
            "--current-limit",
            "100mA",
            "--recovery",
            "SWD under reset",
        ],
        cwd=REPO_ROOT,
    )

    require(result["status"] == "ok", "observe dry-run should prepare command")
    details = result["details"]
    require(details["backend"] == "openocd", "observe dry-run should preserve backend")
    require(details["dry_run"], "observe dry-run should be marked")
    argv = details["command"]["argv_redacted"]
    require(any(str(item).endswith("openocd_semihosting.py") for item in argv), "observe dry-run should expose OpenOCD semihosting command")
    require("--confirm-token" in argv and "<redacted>" in argv, "observe dry-run should redact child token")
    require("observe-token" not in json.dumps(result, ensure_ascii=False), "observe dry-run output must not leak child token")
    require(details["dry_run_controls"]["safety_log_written"] is False, "observe dry-run should report no safety log writes")
    require(state_path.read_text(encoding="utf-8") == before_state, "observe dry-run must not write state")
    require(not (embedded / "safety-log.jsonl").exists(), "observe dry-run must not consume safety token")


def test_workflow_observe_non_dry_run_is_prepared_gated_without_side_effects() -> None:
    project = copy_fixture_project("workflow-observe-planned-gated")
    embedded = project / ".embeddedskills"
    embedded.mkdir(exist_ok=True)
    config_path = embedded / "config.json"
    config_path.write_text(
        json_text(
            {
                "workflow": {"preferred_observe": "openocd"},
                "openocd": {
                    "interface": "stlink.cfg",
                    "target": "stm32f4x.cfg",
                },
            }
        ),
        encoding="utf-8",
    )
    state_path = embedded / "state.json"
    state_path.write_text(json_text({"last_build": {"debug_file": "build/app.elf"}}), encoding="utf-8")
    before_config = config_path.read_text(encoding="utf-8")
    before_state = state_path.read_text(encoding="utf-8")

    result = run_workflow_json(
        [
            "observe",
            "--workspace",
            str(project),
            "--observe-backend",
            "openocd",
            "--confirm-token",
            "unused-observe-token",
            "--child-confirm-token",
            "unused-child-token",
            "--target",
            "STM32F407VGTx",
            "--probe",
            "ST-Link SN123",
            "--voltage",
            "3.3V",
            "--current-limit",
            "100mA",
            "--recovery",
            "SWD under reset",
            "--json",
        ],
        cwd=REPO_ROOT,
    )

    require(result["status"] == "planned-gated", "observe without --dry-run should remain planned-gated until real observer exists")
    gate = result["details"]["observe_execution_gate"]
    require(gate["token_consumed"] is False, "planned observe must not consume token")
    require(gate["state_written"] is False and gate["config_written"] is False, "planned observe must not write state/config")
    require(config_path.read_text(encoding="utf-8") == before_config, "planned observe must not write config")
    require(state_path.read_text(encoding="utf-8") == before_state, "planned observe must not write state")
    require(not (embedded / "safety-log.jsonl").exists(), "planned observe must not write safety log")
    require("unused-child-token" not in json.dumps(result, ensure_ascii=False), "planned observe output must redact child token")


def test_workflow_dry_run_build_flash_warns_without_last_build_artifact() -> None:
    project = copy_fixture_project("workflow-dry-run-build-flash-missing-artifact")
    embedded = project / ".embeddedskills"
    config_path = embedded / "config.json"
    config_path.write_text(
        json_text(
            {
                "workflow": {
                    "preferred_build": "keil",
                    "preferred_flash": "openocd",
                },
                "keil": {
                    "project": "Blinky.uvprojx",
                    "target": "Blinky",
                    "log_dir": ".embeddedskills/build",
                },
                "openocd": {
                    "interface": "stlink.cfg",
                    "target": "stm32f4x.cfg",
                },
            }
        ),
        encoding="utf-8",
    )
    before_config = config_path.read_text(encoding="utf-8")

    result = run_workflow_json(
        [
            "build-flash",
            "--workspace",
            str(project),
            "--flash-backend",
            "openocd",
            "--dry-run",
            "--json",
        ],
        cwd=REPO_ROOT,
    )

    require(result["status"] == "warning", "missing flash artifact dry-run should warn")
    build = result["details"]["build"]["details"]
    flash = result["details"]["flash"]["details"]
    require(any(str(item).endswith("keil_build.py") for item in build["command"]["argv_redacted"]), "warning dry-run should still expose build command")
    require(not flash["prepared_executable"], "flash step should not be executable without artifact")
    require(flash["missing_artifact"] == "state.last_build.flash_file", "missing artifact should be explicit")
    require(config_path.read_text(encoding="utf-8") == before_config, "warning dry-run must not write config")
    require(not (embedded / "state.json").exists(), "warning dry-run must not create state")
    require(not (embedded / "safety-log.jsonl").exists(), "warning dry-run must not consume token")


def test_workflow_dry_run_blocks_artifact_mismatch() -> None:
    project = copy_fixture_project("workflow-dry-run-artifact-mismatch")
    embedded = project / ".embeddedskills"
    embedded.mkdir(exist_ok=True)
    artifact_a = project / "build" / "app-a.hex"
    artifact_b = project / "build" / "app-b.hex"
    artifact_a.parent.mkdir(parents=True, exist_ok=True)
    artifact_a.write_text(":020000040800F2\n:00000001FF\n", encoding="utf-8")
    artifact_b.write_text(":020000040801F1\n:00000001FF\n", encoding="utf-8")
    config_path = embedded / "config.json"
    config_path.write_text(
        json_text(
            {
                "workflow": {
                    "preferred_build": "keil",
                    "preferred_flash": "openocd",
                },
                "keil": {
                    "project": str((project / "Blinky.uvprojx").resolve()),
                    "target": "Blinky",
                    "log_dir": ".embeddedskills/build",
                },
                "openocd": {
                    "interface": "stlink.cfg",
                    "target": "stm32f4x.cfg",
                },
            }
        ),
        encoding="utf-8",
    )
    (embedded / "state.json").write_text(
        json_text({"last_build": {"flash_file": "build/app-b.hex", "artifacts": {"flash_file": "build/app-b.hex"}}}),
        encoding="utf-8",
    )
    expected_hash = hardware_action_plan.artifact_sha256(project, "build/app-a.hex")
    result = run_workflow_json(
        [
            "build-flash",
            "--workspace",
            str(project),
            "--flash-backend",
            "openocd",
            "--artifact",
            "build/app-a.hex",
            "--artifact-hash",
            expected_hash,
            "--dry-run",
            "--json",
        ],
        cwd=REPO_ROOT,
    )
    require(result["status"] == "error", "artifact mismatch dry-run must block")
    require(result["error"]["code"] == "artifact_mismatch", "artifact mismatch should be explicit")
    require(result["details"]["flash"]["details"]["state_artifact"] == "build/app-b.hex", "state artifact should be reported")
    require(config_path.exists(), "artifact mismatch should not remove config")
    require(not (embedded / "safety-log.jsonl").exists(), "artifact mismatch dry-run must not consume token")


def test_embedded_safety_gate_blocks_hardware_actions() -> None:
    gate = safety_gate.check_token(
        "flash",
        "",
        target="STM32F407VGTx",
        probe="ST-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        erase_scope="firmware image only",
        recovery="SWD under reset",
        backend="openocd",
    )
    require(not gate["allowed"], "hardware action without token should be blocked")
    token = safety_gate.confirmation_token(
        "flash",
        {
            "target": "STM32F407VGTx",
            "probe": "ST-Link SN123",
            "voltage": "3.3V",
            "current_limit": "100mA",
            "erase_scope": "firmware image only",
            "recovery": "SWD under reset",
            "backend": "openocd",
        },
    )
    allowed = safety_gate.check_token(
        "flash",
        token,
        target="STM32F407VGTx",
        probe="ST-Link SN123",
        voltage="3.3V",
        current_limit="100mA",
        erase_scope="firmware image only",
        recovery="SWD under reset",
        backend="openocd",
    )
    require(allowed["allowed"], "matching token should pass safety gate")


def test_embedded_safety_gate_rejects_empty_scope_token() -> None:
    token = safety_gate.confirmation_token("debug", {"backend": "jlink-gdb"})
    gate = safety_gate.check_token("debug", token, backend="jlink-gdb")
    require(not gate["allowed"], "hardware token with empty safety scope should be rejected")
    require("missing_fields" in gate, "missing safety fields should be reported")


def test_embedded_safety_gate_binds_artifact_hash() -> None:
    record = {
        "target": "STM32F407VGTx",
        "probe": "ST-Link SN123",
        "voltage": "3.3V",
        "current_limit": "100mA",
        "erase_scope": "firmware image only",
        "recovery": "SWD under reset",
        "artifact": "build/app.hex",
        "artifact_hash": "sha256-confirmed",
        "backend": "openocd",
    }
    token = safety_gate.confirmation_token("flash", record)
    allowed = safety_gate.check_token("flash", token, **record)
    require(allowed["allowed"], "matching artifact hash should pass safety gate")
    rejected = safety_gate.check_token("flash", token, **{**record, "artifact_hash": "sha256-tampered"})
    require(not rejected["allowed"], "changed artifact hash should invalidate safety token")


def test_embedded_safety_gate_flash_requires_erase_scope() -> None:
    record = {
        "target": "STM32F407VGTx",
        "probe": "ST-Link SN123",
        "voltage": "3.3V",
        "current_limit": "100mA",
        "erase_scope": "",
        "recovery": "SWD under reset",
        "backend": "openocd",
    }
    token = safety_gate.confirmation_token("flash", record)
    gate = safety_gate.check_token("flash", token, **record)
    require(not gate["allowed"], "flash without erase_scope should be blocked")
    require("erase_scope" in gate["missing_fields"], "flash missing erase_scope should be reported")


def test_high_risk_scripts_have_safety_gate() -> None:
    scripts = [
        "embeddedskills/keil/scripts/keil_build.py",
        "embeddedskills/jlink/scripts/jlink_exec.py",
        "embeddedskills/jlink/scripts/jlink_swo.py",
        "embeddedskills/openocd/scripts/openocd_run.py",
        "embeddedskills/probe-rs/scripts/probe_rs_exec.py",
        "embeddedskills/serial/scripts/serial_send.py",
        "embeddedskills/serial/scripts/serial_mux.py",
        "embeddedskills/terminal/scripts/terminal_session.py",
        "embeddedskills/can/scripts/can_send.py",
        "embeddedskills/can/scripts/can_monitor.py",
        "embeddedskills/can/scripts/can_log.py",
        "embeddedskills/can/scripts/can_stats.py",
        "embeddedskills/net/scripts/net_scan.py",
        "embeddedskills/net/scripts/net_ping.py",
        "embeddedskills/net/scripts/net_capture.py",
        "embeddedskills/net/scripts/net_stats.py",
        "embeddedskills/ssh/scripts/ssh_exec.py",
        "embeddedskills/ssh/scripts/ssh_transfer.py",
        "embeddedskills/ssh/scripts/ssh_tunnel.py",
        "embeddedskills/ssh/scripts/ssh_config.py",
        "embeddedskills/workflow/scripts/workflow_run.py",
    ]
    for rel in scripts:
        text = repo_path(rel).read_text(encoding="utf-8", errors="replace")
        require("safety_cli" in text or "safety_gate.check_token" in text, f"missing safety gate in {rel}")
    for rel in (
        "embeddedskills/jlink/scripts/jlink_exec.py",
        "embeddedskills/openocd/scripts/openocd_run.py",
        "embeddedskills/probe-rs/scripts/probe_rs_exec.py",
        "embeddedskills/serial/scripts/serial_send.py",
        "embeddedskills/can/scripts/can_send.py",
        "embeddedskills/net/scripts/net_scan.py",
        "embeddedskills/workflow/scripts/workflow_run.py",
    ):
        text = repo_path(rel).read_text(encoding="utf-8", errors="replace")
        require("consume=True" in text, f"direct safety_gate call should consume token in {rel}")


def test_workflow_child_token_and_artifact_hash_contract() -> None:
    workflow = (EMBEDDED_DIR / "workflow" / "scripts" / "workflow_run.py").read_text(encoding="utf-8", errors="replace")
    require("--child-confirm-token" in workflow, "workflow should accept a child hardware token")
    require("--dry-run" in workflow, "workflow should accept dry-run command preparation")
    require("gate_action and not args.dry_run" in workflow, "workflow dry-run must not consume parent hardware token")
    require("used_backends and not args.dry_run" in workflow, "workflow dry-run must not write config preferences")
    require("and not args.dry_run" in workflow and "update_state_entry" in workflow, "workflow dry-run must not update workflow state")
    require('"confirm_token": args.child_confirm_token' in workflow, "workflow must pass child token to lower hardware scripts")
    require('"artifact_hash": "--artifact-hash"' in workflow, "workflow should forward artifact hash to lower hardware scripts")
    require("artifact_hash=args.artifact_hash" in workflow, "workflow parent gate should bind artifact hash")
    for rel in (
        "embeddedskills/jlink/scripts/jlink_exec.py",
        "embeddedskills/openocd/scripts/openocd_run.py",
        "embeddedskills/probe-rs/scripts/probe_rs_exec.py",
        "embeddedskills/jlink/scripts/jlink_gdb.py",
        "embeddedskills/openocd/scripts/openocd_gdb.py",
        "embeddedskills/probe-rs/scripts/probe_rs_gdb.py",
        "embeddedskills/jlink/scripts/jlink_rtt.py",
        "embeddedskills/openocd/scripts/openocd_semihosting.py",
        "embeddedskills/probe-rs/scripts/probe_rs_rtt.py",
    ):
        script = repo_path(rel).read_text(encoding="utf-8", errors="replace")
        require("artifact_hash=args.artifact_hash" in script, f"script should bind artifact hash: {rel}")
        require("workspace=args.workspace" in script, f"script should consume token in target workspace: {rel}")


def test_hardware_action_plan_blocks_missing_safety_input() -> None:
    plan = hardware_action_plan.plan_action(root=FIXTURE, action="flash", target="STM32F407VGTx")
    require(plan["status"] == "blocked-missing-safety-input", "missing voltage/probe/current should block flash")
    require("voltage" in plan["missing_inputs"], "voltage should be required")


def test_hardware_action_plan_blocks_unknown_action() -> None:
    plan = hardware_action_plan.plan_action(root=FIXTURE, action="toggle-mystery-power")
    require(plan["status"] == "blocked-unsupported-action", "unknown actions must be blocked")
    require(plan["hardware_side_effect"], "unknown actions should be treated as unsafe")


def test_firmware_intent_planner_gpio_rtos() -> None:
    plan = firmware_intent_planner.plan_implementation(
        FIXTURE,
        feature="LED blink",
        pin="PD12",
        function="gpio-output",
        rtos=True,
    )
    require(plan["status"] == "plan-only", "firmware planner should not edit code")
    require("Core/Src/app_led_blink.c" in plan["recommended_files"], "planner should recommend app source file")
    require(plan["freertos"]["enabled"], "planner should include FreeRTOS model")
    require("Drivers/" in plan["cube_generated_boundaries"]["forbidden_by_default"], "planner should forbid driver edits by default")


def test_firmware_intent_planner_respects_missing_rtos() -> None:
    project = copy_fixture_project("bare-metal-basic")
    ioc = project / "Blinky.ioc"
    text = ioc.read_text(encoding="utf-8")
    ioc.write_text("\n".join(line for line in text.splitlines() if not line.startswith("FREERTOS.")) + "\n", encoding="utf-8")
    plan = firmware_intent_planner.plan_implementation(
        project,
        feature="LED blink",
        pin="PD12",
        function="gpio-output",
        rtos=True,
    )
    require(plan["status"] == "plan-only-needs-rtos-configuration", "missing FreeRTOS should be explicit")
    require(not plan["freertos"]["enabled"], "FreeRTOS plan should not be enabled when middleware is absent")


def test_firmware_code_patcher_preview_and_write() -> None:
    project = copy_fixture_project("firmware-patch-basic")
    preview = firmware_code_patcher.preview_patch(
        project,
        feature="LED blink",
        pin="PD12",
        function="gpio-output",
        rtos=True,
    )
    paths = {Path(item["path"]).relative_to(project).as_posix(): item["content"] for item in preview["files"]}
    require("Core/Inc/app_led_blink.h" in paths, "patcher should preview app header")
    require("Core/Src/app_led_blink.c" in paths, "patcher should preview app source")
    require("docs/firmware-patches/app_led_blink.md" in paths, "patcher should preview integration note")
    require("HAL_GPIO_WritePin(GPIOD, GPIO_PIN_12" in paths["Core/Src/app_led_blink.c"], "GPIO patch should target PD12")
    try:
        firmware_code_patcher.write_patch(preview, confirm_write=False)
    except ValueError as exc:
        require("--confirm-write" in str(exc), "write guard should mention --confirm-write")
    else:
        raise AssertionError("firmware patch write should require explicit confirmation")
    written = firmware_code_patcher.write_patch(preview, confirm_write=True)
    require(written["status"] == "written", "confirmed patch should be written")
    require((project / "Core" / "Inc" / "app_led_blink.h").exists(), "header should be written")
    require((project / "Core" / "Src" / "app_led_blink.c").exists(), "source should be written")
    require((project / "docs" / "firmware-patches" / "app_led_blink.md").exists(), "integration note should be written")


def test_firmware_integration_blocks_missing_app_module_and_missing_user_code() -> None:
    project = copy_fixture_project("firmware-integrate-blocked")
    missing_app = firmware_code_patcher.preview_integration_patch(
        project,
        feature="LED blink",
        pin="PD12",
        function="gpio-output",
        rtos=True,
    )
    require(missing_app["status"] == "blocked-missing-app-module", "integration should require app module files first")
    preview = firmware_code_patcher.preview_patch(project, feature="LED blink", pin="PD12", function="gpio-output", rtos=True)
    firmware_code_patcher.write_patch(preview, confirm_write=True)
    missing_user_code = firmware_code_patcher.preview_integration_patch(
        project,
        feature="LED blink",
        pin="PD12",
        function="gpio-output",
        rtos=True,
    )
    require(missing_user_code["status"] == "blocked-missing-user-code-block", "integration should block when main.c lacks USER CODE blocks")


def test_firmware_integration_dry_run_and_confirmed_write_are_user_code_only() -> None:
    project = copy_fixture_project("firmware-integrate-user-code")
    write_cubemx_main(project / "Core" / "Src" / "main.c")
    (project / "Core" / "Src" / "freertos.c").write_text(cubemx_freertos_c(), encoding="utf-8")
    preview = firmware_code_patcher.preview_patch(project, feature="LED blink", pin="PD12", function="gpio-output", rtos=True)
    firmware_code_patcher.write_patch(preview, confirm_write=True)
    main_path = project / "Core" / "Src" / "main.c"
    freertos_path = project / "Core" / "Src" / "freertos.c"
    before_main = main_path.read_text(encoding="utf-8")
    before_freertos = freertos_path.read_text(encoding="utf-8")
    integration = firmware_code_patcher.preview_integration_patch(
        project,
        feature="LED blink",
        pin="PD12",
        function="gpio-output",
        rtos=True,
    )
    require(integration["status"] == "ready-to-write", "integration should be ready with USER CODE blocks")
    require(integration["dry_run"], "integration preview should be dry-run")
    require("app_led_blink.h" in integration["diff_preview"], "integration diff should include app header")
    require(any(item["block"] == "RTOS_THREADS" for item in integration["proposed_changes"]), "FreeRTOS integration should propose task hook")
    require(main_path.read_text(encoding="utf-8") == before_main, "integration dry-run must not change main.c")
    require(freertos_path.read_text(encoding="utf-8") == before_freertos, "integration dry-run must not change freertos.c")
    try:
        firmware_code_patcher.write_integration_patch(integration, confirm_write=False)
    except ValueError as exc:
        require("--confirm-write" in str(exc), "integration write guard should mention confirm-write")
    else:
        raise AssertionError("firmware integration write should require confirm-write")
    written = firmware_code_patcher.write_integration_patch(integration, confirm_write=True)
    require(written["status"] == "written", "confirmed integration should write")
    after_main = main_path.read_text(encoding="utf-8")
    after_freertos = freertos_path.read_text(encoding="utf-8")
    require('#include "app_led_blink.h"' in user_code_body(after_main, "Includes"), "include should be inside USER CODE Includes")
    require("app_led_blink_init();" in user_code_body(after_main, "2"), "init should be inside USER CODE 2")
    require("app_led_blink_start();" in user_code_body(after_main, "2"), "start should be inside USER CODE 2")
    require("osThreadCreate(osThread(app_led_blink), NULL);" in user_code_body(after_freertos, "RTOS_THREADS"), "RTOS task should be inside USER CODE RTOS_THREADS")
    require((main_path.with_suffix(".c.bak")).exists(), "main.c backup should be created")
    second = firmware_code_patcher.write_integration_patch(
        firmware_code_patcher.preview_integration_patch(project, feature="LED blink", pin="PD12", function="gpio-output", rtos=True),
        confirm_write=True,
    )
    require(second["written"] == [], "repeated integration should be idempotent with no rewrites")


def test_firmware_integration_write_revalidates_user_code_blocks() -> None:
    project = copy_fixture_project("firmware-integrate-toctou")
    write_cubemx_main(project / "Core" / "Src" / "main.c")
    (project / "Core" / "Src" / "freertos.c").write_text(cubemx_freertos_c(), encoding="utf-8")
    preview = firmware_code_patcher.preview_patch(project, feature="LED blink", pin="PD12", function="gpio-output", rtos=True)
    firmware_code_patcher.write_patch(preview, confirm_write=True)
    integration = firmware_code_patcher.preview_integration_patch(
        project,
        feature="LED blink",
        pin="PD12",
        function="gpio-output",
        rtos=True,
    )
    require(integration["status"] == "ready-to-write", "integration should start ready")
    main_path = project / "Core" / "Src" / "main.c"
    before = main_path.read_text(encoding="utf-8")
    main_path.write_text(before.replace("/* USER CODE BEGIN 2 */", "/* USER CODE BEGIN REMOVED */"), encoding="utf-8")
    try:
        firmware_code_patcher.write_integration_patch(integration, confirm_write=True)
    except ValueError as exc:
        require("changed since preview" in str(exc), "integration TOCTOU guard should mention changed preview state")
    else:
        raise AssertionError("firmware integration write should revalidate USER CODE blocks")
    after = main_path.read_text(encoding="utf-8")
    require("app_led_blink_init();" not in after, "blocked integration write must not insert into changed file")


def test_firmware_integration_skips_task_when_rtos_not_enabled() -> None:
    project = copy_fixture_project("firmware-integrate-no-rtos")
    ioc = project / "Blinky.ioc"
    ioc.write_text("\n".join(line for line in ioc.read_text(encoding="utf-8").splitlines() if not line.startswith("FREERTOS.")) + "\n", encoding="utf-8")
    write_cubemx_main(project / "Core" / "Src" / "main.c")
    preview = firmware_code_patcher.preview_patch(project, feature="LED blink", pin="PD12", function="gpio-output", rtos=False)
    firmware_code_patcher.write_patch(preview, confirm_write=True)
    integration = firmware_code_patcher.preview_integration_patch(
        project,
        feature="LED blink",
        pin="PD12",
        function="gpio-output",
        rtos=True,
    )
    require(integration["status"] == "ready-to-write", "bare-metal integration should still add include/init/start")
    require(not any(item["block"] == "RTOS_THREADS" for item in integration["proposed_changes"]), "bare-metal integration must not create RTOS task hook")


def test_firmware_code_patcher_generates_peripheral_app_modules() -> None:
    cases = [
        ("i2c sensor", "i2c", "PB7", "HAL_I2C_Master_Transmit", "osMutexCreate", "APP_I2C_SENSOR_TIMEOUT_MS"),
        ("spi display", "spi", "PA5", "HAL_SPI_TransmitReceive", "osMutexCreate", "APP_SPI_DISPLAY_TIMEOUT_MS"),
        ("uart console", "uart", "PA2", "HAL_UART_Receive", "osMessageCreate", "APP_UART_CONSOLE_TIMEOUT_MS"),
        ("adc sample", "adc", "PA0", "HAL_ADC_PollForConversion", "app_adc_sample_status_t", "APP_ADC_SAMPLE_TIMEOUT_MS"),
        ("pwm motor", "pwm", "PA8", "HAL_TIM_PWM_Start", "__HAL_TIM_SET_COMPARE", "APP_PWM_MOTOR_CHANNEL"),
        ("can bridge", "can", "PD0", "HAL_CAN_AddTxMessage", "CAN_TxHeaderTypeDef", "APP_CAN_BRIDGE_TIMEOUT_MS"),
    ]
    for feature, function, pin, hal_call, sync_marker, timeout_marker in cases:
        project = copy_fixture_project(f"firmware-{function}")
        add_ioc_peripheral(project / "Blinky.ioc", function)
        preview = firmware_code_patcher.preview_patch(
            project,
            feature=feature,
            pin=pin,
            function=function,
            rtos=True,
        )
        source = next(item["content"] for item in preview["files"] if item["path"].endswith(".c"))
        header = next(item["content"] for item in preview["files"] if item["path"].endswith(".h"))
        note = next(item["content"] for item in preview["files"] if item["path"].endswith(".md"))
        require(hal_call in source, f"{function} source should call {hal_call}")
        require(sync_marker in source, f"{function} source should include RTOS/error mechanism {sync_marker}")
        require(timeout_marker in source or timeout_marker in header, f"{function} should define timeout/channel marker")
        require("_HAL_ERROR" in header, f"{function} header should expose error status enum")
        require("Error And Recovery Policy" in note, f"{function} integration note should include recovery policy")


def test_firmware_intent_planner_reports_error_timeout_and_hooks() -> None:
    project = copy_fixture_project("firmware-plan-i2c")
    add_ioc_peripheral(project / "Blinky.ioc", "i2c")
    plan = firmware_intent_planner.plan_implementation(
        project,
        feature="sensor read",
        pin="PB7",
        function="i2c",
        rtos=True,
    )
    require(plan["hal"]["handle"] == "hi2c1", "I2C handle should be inferred from IOC")
    require(plan["timeout_ms"] == 100, "I2C timeout should be explicit")
    require(plan["error_policy"]["return_contract"], "error contract should be present")
    require(plan["recovery_policy"], "recovery policy should be present")
    require(any("mutex" in item for item in plan["concurrency_model"]["primitives"]), "I2C should use mutex under RTOS")
    require(plan["integration_hooks"], "integration hooks should be present")


def test_manual_summarizer_extracts_evidence() -> None:
    summary = manual_summarizer.summarize_documents(
        "STM32F407VGTx",
        [REPO_ROOT / "tests" / "fixtures" / "docs" / "sample-manual.txt"],
    )
    require(summary["sections"]["power"], "power evidence should be extracted")
    require(summary["sections"]["clock"], "clock evidence should be extracted")
    require(summary["sections"]["debug"], "debug evidence should be extracted")
    require(summary["sections"]["electrical_limits"], "electrical limit evidence should be extracted")
    markdown = manual_summarizer.render_markdown(summary)
    require("doc-01-" in markdown and "page " in markdown and "line " in markdown, "manual summary should keep document/page/line evidence")
    evidence = summary["sections"]["power"][0]
    require({"document_id", "document_type", "page", "line", "text"}.issubset(evidence), "evidence should be document-scoped")


def test_manual_summarizer_accepts_pdf() -> None:
    summary = manual_summarizer.summarize_documents(
        "STM32F407VGTx",
        [REPO_ROOT / "tests" / "fixtures" / "docs" / "sample-datasheet.pdf"],
    )
    require(summary["documents"][0]["line_count"] > 0, "PDF summary should extract some text")


def test_build_plan_shape() -> None:
    plan = build_plan.generate_plan(FIXTURE)
    labels = [item["label"] for item in plan["commands"]]
    require(plan["status"] == "ready", "build plan should be ready for fixture")
    require(all(item["argv"][0] == sys.executable for item in plan["commands"]), "plan must use trusted Python")
    require("Scan Keil projects" in labels, "missing Keil scan command")
    require("List Keil targets" in labels, "missing Keil target command")
    require("Prepare Keil build" in labels, "missing gated build command")


def test_build_plan_markdown_uses_json_argv() -> None:
    markdown = build_plan.render_markdown(build_plan.generate_plan(FIXTURE))
    require("```powershell" not in markdown, "build plan should not render copyable PowerShell commands")
    require("```json" in markdown, "build plan should render structured argv JSON")


def test_runner_rejects_bare_python_name() -> None:
    argv = ["python", "tools\\cube_detect.py", "--root", str(FIXTURE), "--json"]
    item: dict[str, object] = {
        "phase": "inspect",
        "argv": argv,
    }
    reason = command_runner.allowlist_denial_reason(item)
    require(reason == "command executable is not the trusted Python interpreter", "bare python should be rejected")

    argv[0] = "py"
    reason = command_runner.allowlist_denial_reason(item)
    require(reason == "command executable is not the trusted Python interpreter", "bare py should be rejected")


def test_runner_rejects_untrusted_absolute_python() -> None:
    fake_python = str(Path(sys.executable).with_name("not_trusted_python.exe"))
    item: dict[str, object] = {
        "phase": "inspect",
        "argv": [fake_python, "tools\\cube_detect.py", "--root", str(FIXTURE), "--json"],
    }
    reason = command_runner.allowlist_denial_reason(item)
    require(reason == "command executable is not the trusted Python interpreter", "untrusted absolute python should be rejected")


def test_runner_accepts_absolute_allowlisted_script() -> None:
    script = REPO_ROOT / "tools" / "cube_detect.py"
    item = {
        "phase": "inspect",
        "argv": [sys.executable, str(script), "--root", str(FIXTURE), "--json"],
    }
    reason = command_runner.allowlist_denial_reason(item)
    require(reason == "", "absolute allowlisted script should be accepted")
    canonical = command_runner.canonical_argv(item)  # type: ignore[arg-type]
    require(canonical[0] == str(command_runner.TRUSTED_PYTHON), "canonical argv should use trusted Python")
    require(canonical[1] == str(script.resolve()), "canonical argv should use absolute script path")


def test_runner_path_args_use_workspace_root() -> None:
    previous = os.environ.get(runtime_context.ENV_WORKSPACE_ROOT)
    os.environ[runtime_context.ENV_WORKSPACE_ROOT] = str(FIXTURE.parent)
    try:
        require(command_runner.safe_read_path_arg(str(FIXTURE)), "fixture should be inside configured workspace root")
        require(
            not command_runner.safe_read_path_arg(str(REPO_ROOT / "README.md")),
            "workspace path checks should not fall back to package root",
        )
    finally:
        if previous is None:
            os.environ.pop(runtime_context.ENV_WORKSPACE_ROOT, None)
        else:
            os.environ[runtime_context.ENV_WORKSPACE_ROOT] = previous


def test_runner_rejects_extra_allowlisted_args() -> None:
    item = {
        "phase": "build-discovery",
        "argv": [sys.executable, "embeddedskills\\keil\\scripts\\keil_project.py", "scan", "--root", str(FIXTURE), "--json", "--extra"],
    }
    reason = command_runner.allowlist_denial_reason(item)
    require("argv schema" in reason, "extra args should be rejected by argv schema")


def test_safe_discovery_runner() -> None:
    report = command_runner.run_plan(FIXTURE, phase="build-discovery")
    require(report["summary"] == {"ok": 2, "error": 0, "timeout": 0, "skipped": 4}, "discovery summary changed")
    executed = {item["label"] for item in report["results"] if item["status"] == "ok"}
    require(executed == {"Scan Keil projects", "List Keil targets"}, "unexpected discovery commands executed")


def test_build_stays_blocked_even_with_metadata_flags() -> None:
    report = command_runner.run_plan(FIXTURE, phase="build-plan", allow_writes=True, allow_confirmation=True)
    build_items = [item for item in report["results"] if item["label"] == "Prepare Keil build"]
    require(len(build_items) == 1, "expected one gated Keil build command")
    require(build_items[0]["status"] == "skipped", "safe runner must not execute workflow build")
    require("safe allowlist" in build_items[0]["reason"], "build should be blocked by hard allowlist")


def test_config_write_requires_double_confirmation() -> None:
    proposal = config_proposal.propose_config(FIXTURE, target="Blinky")
    workflow = proposal["proposed_config"]["workflow"]
    require("preferred_flash" not in workflow, "config proposal must not default flash to auto")
    require("preferred_debug" not in workflow, "config proposal must not default debug to auto")
    require("preferred_observe" not in workflow, "config proposal must not default observe to auto")
    try:
        config_proposal.write_config(proposal, confirm_write=False)
    except ValueError as exc:
        require("--confirm-write" in str(exc), "write guard should mention --confirm-write")
    else:
        raise AssertionError("config write should require explicit confirmation")


def test_config_write_requires_ready_status() -> None:
    proposal = {
        "root": str(FIXTURE),
        "status": "needs-input",
        "required_inputs": [],
        "config_path": str(FIXTURE / ".embeddedskills" / "config.json"),
        "proposed_config": {"workflow": {"preferred_build": "keil"}},
    }
    try:
        config_proposal.write_config(proposal, confirm_write=True)
    except ValueError as exc:
        require("proposal status" in str(exc), "write guard should mention proposal status")
    else:
        raise AssertionError("config write should require ready-to-write status")


def test_config_merge_preserves_hardware_preferences() -> None:
    merged = config_proposal.merge_config(
        {"workflow": {"preferred_flash": "disabled", "preferred_debug": "manual"}},
        {"workflow": {"preferred_build": "keil"}},
    )
    require(merged["workflow"]["preferred_flash"] == "disabled", "flash preference should be preserved")
    require(merged["workflow"]["preferred_debug"] == "manual", "debug preference should be preserved")
    require(merged["workflow"]["preferred_build"] == "keil", "build preference should be merged")


def test_product_doctor_commands() -> None:
    project = copy_fixture_project("cubemx-basic-workspace")
    workspace = project.parent
    previous = os.environ.get(runtime_context.ENV_WORKSPACE_ROOT)
    os.environ[runtime_context.ENV_WORKSPACE_ROOT] = str(workspace)
    caps = product_doctor.capabilities()
    commands = {item["command"] for item in caps["capabilities"]}
    require({"onboard", "auto", "next-step", "workbench", "brain", "ask", "task", "doctor", "status", "safety-audit", "bench-runbook", "bench-preflight", "workflow-dry-run", "patch-ioc", "firmware-integrate", "build-flash-sim", "build-debug-sim", "observe-sim"}.issubset(commands), "product commands missing from capability matrix")
    try:
        doctor = product_doctor.doctor(project)
        require(doctor["summary"]["error"] == 0, "doctor should not report errors for fixture")
        require(doctor["bench_readiness"]["status"] in {"needs-bench-input", "ready-with-bench-warnings"}, "doctor should report bench readiness")
        bench_checks = {item["name"]: item["status"] for item in doctor["bench_readiness"]["checks"]}
        require(bench_checks["hardware_backend_not_auto"] == "warn", "fixture auto hardware preferences should be a bench warning")
        out_dir = workspace / "docs" / "inspections" / project.name
        hardware_butler.onboard_project(project, out_dir=out_dir, target="Blinky")
        status = product_doctor.project_status(project)
        require(status["backend"]["backend"] == "keil", "status should report Keil backend")
        require(status["discovery"]["status"] == "ok", "status should read successful discovery manifest")
        require(status["bench_readiness"]["status"] in {"needs-bench-input", "ready-with-bench-warnings"}, "status should include bench readiness")
        require(status["status"] == "ready-with-config-warning", "fixture should report config warning from hardware auto preferences")
    finally:
        if previous is None:
            os.environ.pop(runtime_context.ENV_WORKSPACE_ROOT, None)
        else:
            os.environ[runtime_context.ENV_WORKSPACE_ROOT] = previous


def test_project_workflow_state_and_next_step() -> None:
    project = copy_fixture_project("workflow-state")
    state = project_workflow.collect_project_state(project)
    require(state["schema_version"] == 1, "workflow state should return schema")
    require(state["backend"].get("backend") == "keil", "workflow should expose detected backend")
    require(state["next_step"]["safe_by_default"], "next step must be safe by default")
    require(not state["next_step"]["touches_hardware"], "next step must not touch hardware")
    workbench = project_workflow.build_workbench(project)
    require(workbench["app"] == "hardware-butler-workbench", "workbench should identify connected app model")
    require(workbench["primary_action"]["id"] == workbench["state"]["next_step"]["id"], "workbench primary action should mirror next step")
    require(workbench["actions"][0]["id"] == "refresh", "workbench should start with refresh action")
    require(workbench["reports"], "workbench should expose report summaries")
    path = project_workflow.write_project_state(project, state)
    require(path.exists(), "project workflow state should be persisted")


def test_task_workflows_are_safe_and_intent_based() -> None:
    configure = task_workflows.build_task_plan(FIXTURE, "configure-peripheral", function="i2c", instance="I2C1")
    require(configure["status"] == "ready", "bus peripheral intent should accept instance input")
    require(configure["missing_inputs"] == [], "configured bus peripheral should not require extra input")
    require([item["id"] for item in configure["steps"]] == ["brain", "firmware-plan"], "I2C instance plan should refresh brain and plan firmware")
    collect = task_workflows.build_task_plan(FIXTURE, "collect-evidence", part="STM32F407VGTx")
    chip_step = [item for item in collect["steps"] if item["id"] == "chip-dossier"][0]
    require("--api-preset" in chip_step["argv"] and "chip-docs" in chip_step["argv"], "collect evidence should use chip-docs preset")
    bringup = task_workflows.build_task_plan(FIXTURE, "prepare-bringup")
    require(bringup["safety"]["real_hardware_actions"] == "planned-gated", "bring-up should stay planned-gated")
    require(all(item["safe_by_default"] and not item["touches_hardware"] for item in bringup["steps"]), "task steps must be safe local commands")


def test_product_doctor_bench_readiness_with_artifacts() -> None:
    project = copy_fixture_project("bench-readiness-artifacts")
    embedded = project / ".embeddedskills"
    embedded.mkdir(parents=True, exist_ok=True)
    artifact = project / "build" / "app.hex"
    debug = project / "build" / "app.elf"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(":00000001FF\n", encoding="utf-8")
    debug.write_text("ELF fixture\n", encoding="utf-8")
    (embedded / "config.json").write_text(
        json_text(
            {
                "workflow": {
                    "preferred_flash": "openocd",
                    "preferred_debug": "openocd",
                    "preferred_observe": "openocd",
                },
                "openocd": {
                    "interface": "stlink.cfg",
                    "target": "stm32f4x.cfg",
                },
            }
        ),
        encoding="utf-8",
    )
    (embedded / "state.json").write_text(
        json_text(
            {
                "last_build": {
                    "flash_file": "build/app.hex",
                    "debug_file": "build/app.elf",
                    "artifacts": {
                        "flash_file": "build/app.hex",
                        "debug_file": "build/app.elf",
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    readiness = product_doctor.bench_readiness(project)
    require(readiness["status"] in {"ready-for-bench-preflight", "ready-with-bench-warnings"}, "configured bench readiness should not need input")
    require(readiness["artifacts"]["flash_exists"], "bench readiness should find flash artifact")
    require(readiness["artifacts"]["debug_exists"], "bench readiness should find debug artifact")
    checks = {item["name"]: item["status"] for item in readiness["checks"]}
    require(checks["openocd_config"] == "ok", "OpenOCD config should be recognized")
    require(checks["hardware_backend_selected"] == "ok", "hardware backend preferences should be recognized")


def cleanup_dir(path: Path) -> None:
    root = REPO_ROOT.resolve()
    target = path.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise AssertionError(f"refusing to clean outside repo root: {target}")
    if target.exists():
        shutil.rmtree(target)


def cleanup_generated_state() -> None:
    cleanup_dir(TEST_TMP)
    cleanup_dir(REPO_ROOT / "tests" / "tmp")
    cleanup_dir(REPO_ROOT / "docs" / "chip")
    cleanup_dir(REPO_ROOT / "docs" / "inspections")
    for cache in REPO_ROOT.rglob("__pycache__"):
        cleanup_dir(cache)


def copy_fixture_project(name: str) -> Path:
    target = TEST_TMP / name
    cleanup_dir(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FIXTURE, target)
    return target


def add_ioc_peripheral(ioc: Path, function: str) -> None:
    snippets = {
        "i2c": ["PB7.Signal=I2C1_SDA", "PB6.Signal=I2C1_SCL", "I2C1.IPParameters=Timing", "I2C1.Timing=0x00C0EAFF"],
        "spi": ["PA5.Signal=SPI1_SCK", "PA6.Signal=SPI1_MISO", "PA7.Signal=SPI1_MOSI", "SPI1.IPParameters=VirtualType", "SPI1.VirtualType=VM_MASTER"],
        "uart": ["PA2.Signal=USART2_TX", "PA3.Signal=USART2_RX", "USART2.IPParameters=VirtualMode", "USART2.VirtualMode=VM_ASYNC"],
        "adc": ["PA0.Signal=ADC1_IN0", "ADC1.IPParameters=Rank-0#ChannelRegularConversion", "ADC1.Rank-0#ChannelRegularConversion=1"],
        "pwm": ["PA8.Signal=TIM1_CH1", "TIM1.IPParameters=Channel-PWM Generation1", "TIM1.Channel-PWM Generation1=TIM_CHANNEL_1"],
        "can": ["PD0.Signal=CAN1_RX", "PD1.Signal=CAN1_TX", "CAN1.IPParameters=Prescaler", "CAN1.Prescaler=16"],
    }
    text = ioc.read_text(encoding="utf-8")
    ioc.write_text(text.rstrip() + "\n" + "\n".join(snippets[function]) + "\n", encoding="utf-8")


def write_cubemx_main(path: Path) -> None:
    path.write_text(
        """#include \"main.h\"
/* USER CODE BEGIN Includes */
/* USER CODE END Includes */

int main(void)
{
  HAL_Init();
  MX_GPIO_Init();
  /* USER CODE BEGIN 2 */
  /* USER CODE END 2 */
  while (1)
  {
    /* USER CODE BEGIN 3 */
    /* USER CODE END 3 */
  }
}
""",
        encoding="utf-8",
    )


def cubemx_freertos_c() -> str:
    return """#include \"cmsis_os.h\"

void MX_FREERTOS_Init(void)
{
  /* USER CODE BEGIN RTOS_THREADS */
  /* USER CODE END RTOS_THREADS */
}
"""


def user_code_body(text: str, block: str) -> str:
    begin = f"/* USER CODE BEGIN {block} */"
    end = f"/* USER CODE END {block} */"
    start = text.index(begin) + len(begin)
    finish = text.index(end)
    return text[start:finish]


def json_text(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def run_workflow_json(args: list[str], *, cwd: Path) -> dict:
    cmd = [
        sys.executable,
        str(EMBEDDED_DIR / "workflow" / "scripts" / "workflow_run.py"),
        *args,
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(f"workflow command failed: {proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"workflow command did not return JSON: {exc}\nstdout={proc.stdout}\nstderr={proc.stderr}")
    if not isinstance(data, dict):
        raise AssertionError("workflow command returned non-object JSON")
    return data


def test_hardware_butler_cli_bench_runbook_help_smoke() -> None:
    candidates = [
        REPO_ROOT / "tools" / "hardware_butler.py",
        REPO_ROOT / "plugins" / "hardware-development-butler" / "scripts" / "tools" / "hardware_butler.py",
        REPO_ROOT / "plugins" / "hardware-development-butler" / "skills" / "hardware-development-butler" / "scripts" / "run_hardware_butler.py",
        REPO_ROOT.parent / "skills" / "hardware-development-butler" / "scripts" / "run_hardware_butler.py",
    ]
    commands = [[sys.executable, str(path), "bench-runbook", "--help"] for path in candidates if path.exists()]
    require(bool(commands), "bench-runbook CLI smoke should find at least one CLI entry")
    try:
        for cmd in commands:
            proc = subprocess.run(
                cmd,
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
            )
            require(proc.returncode == 0, f"bench-runbook help smoke failed: {cmd}\nstdout={proc.stdout}\nstderr={proc.stderr}")
            require("--action" in proc.stdout and "--backend" in proc.stdout, "bench-runbook help should expose action/backend flags")
    finally:
        for cache in REPO_ROOT.rglob("__pycache__"):
            cleanup_dir(cache)


def test_safe_write_rejects_workspace_escape() -> None:
    try:
        safe_io.validate_write_path(REPO_ROOT.parent / "outside.md", allowed_roots=[REPO_ROOT])
    except ValueError:
        return
    raise AssertionError("safe write path should reject workspace escape")


def test_runner_minimal_env_does_not_leak_secret() -> None:
    os.environ["HARDWARE_BUTLER_TEST_SECRET"] = "do-not-leak"
    try:
        env = command_runner.minimal_env()
    finally:
        os.environ.pop("HARDWARE_BUTLER_TEST_SECRET", None)
    require("HARDWARE_BUTLER_TEST_SECRET" not in env, "minimal env should not include arbitrary secret variables")


def main() -> None:
    tests = [
        test_cube_detection,
        test_cubemx_summary_semantic_indexes,
        test_chip_dossier_plan_shape,
        test_document_provider_hints_cover_major_vendors,
        test_chip_dossier_download_accepts_only_pdf,
        test_chip_dossier_search_download_extracts_summary,
        test_chip_dossier_auto_search_uses_provider_hints_when_sources_missing,
        test_document_search_api_presets_and_missing_provider_status,
        test_chip_dossier_api_search_falls_back_to_vendor_hints,
        test_cubemx_pin_advisor_gpio,
        test_cubemx_pin_advisor_missing_pin,
        test_cubemx_pin_advisor_package_evidence_verified,
        test_cubemx_pin_advisor_package_evidence_relative_to_cwd,
        test_cubemx_pin_advisor_package_evidence_contradiction,
        test_cubemx_pin_advisor_package_evidence_unknown_without_file,
        test_cubemx_pin_advisor_debug_pin_conflict,
        test_cubemx_pin_advisor_blocks_multiple_ioc,
        test_cubemx_ioc_patch_gpio_dry_run_does_not_write,
        test_cubemx_ioc_patch_blocks_debug_clock_and_occupied_pins,
        test_cubemx_ioc_patch_i2c_requires_complete_bus,
        test_cubemx_ioc_patch_i2c_write_requires_confirmation_and_creates_backup,
        test_cubemx_ioc_patch_write_revalidates_current_state,
        test_hardware_action_plan_flash_requires_confirmation,
        test_hardware_action_plan_build_flash_child_token_and_artifact_hash,
        test_hardware_action_plan_child_backend_scope_matrix,
        test_hardware_action_plan_execution_package_workflow_command,
        test_hardware_action_plan_execution_package_observe_backend_command,
        test_hardware_action_plan_observe_child_token,
        test_hardware_action_executor_fake_backend_requires_token,
        test_hardware_action_executor_rejects_tampered_plan_token,
        test_hardware_action_executor_rejects_artifact_hash_mismatch,
        test_hardware_action_executor_workflow_build_is_controlled,
        test_hardware_action_executor_workflow_build_flash_sim_consumes_child_token,
        test_hardware_action_executor_workflow_observe_sim_consumes_child_token,
        test_hardware_action_executor_bench_preflight_does_not_consume_token,
        test_hardware_action_executor_bench_preflight_validates_real_command_package,
        test_bench_runbook_aggregates_preflight_and_redacts_tokens_without_side_effects,
        test_bench_runbook_reports_real_workflow_dry_run_error_without_side_effects,
        test_bench_runbook_refuses_unsafe_workflow_dry_run_subprocess,
        test_bench_runbook_refuses_missing_json_and_untrusted_workflow_argv,
        test_bench_runbook_preflight_failure_blocks_workflow_subprocess,
        test_bench_runbook_rejects_invalid_json_or_missing_dry_run_controls,
        test_bench_runbook_sanitizes_nested_stdout_stderr_and_argv,
        test_bench_runbook_blocks_missing_safety_input_without_side_effects,
        test_workflow_dry_run_build_flash_prepares_commands_without_side_effects,
        test_workflow_dry_run_observe_prepares_command_without_token_consumption,
        test_workflow_observe_non_dry_run_is_prepared_gated_without_side_effects,
        test_workflow_dry_run_build_flash_warns_without_last_build_artifact,
        test_workflow_dry_run_blocks_artifact_mismatch,
        test_embedded_safety_gate_blocks_hardware_actions,
        test_embedded_safety_gate_rejects_empty_scope_token,
        test_embedded_safety_gate_binds_artifact_hash,
        test_embedded_safety_gate_flash_requires_erase_scope,
        test_high_risk_scripts_have_safety_gate,
        test_workflow_child_token_and_artifact_hash_contract,
        test_hardware_action_plan_blocks_missing_safety_input,
        test_hardware_action_plan_blocks_unknown_action,
        test_firmware_intent_planner_gpio_rtos,
        test_firmware_intent_planner_respects_missing_rtos,
        test_firmware_code_patcher_preview_and_write,
        test_firmware_integration_blocks_missing_app_module_and_missing_user_code,
        test_firmware_integration_dry_run_and_confirmed_write_are_user_code_only,
        test_firmware_integration_write_revalidates_user_code_blocks,
        test_firmware_integration_skips_task_when_rtos_not_enabled,
        test_firmware_code_patcher_generates_peripheral_app_modules,
        test_firmware_intent_planner_reports_error_timeout_and_hooks,
        test_manual_summarizer_extracts_evidence,
        test_manual_summarizer_accepts_pdf,
        test_build_plan_shape,
        test_build_plan_markdown_uses_json_argv,
        test_runner_rejects_bare_python_name,
        test_runner_rejects_untrusted_absolute_python,
        test_runner_accepts_absolute_allowlisted_script,
        test_runner_path_args_use_workspace_root,
        test_runner_rejects_extra_allowlisted_args,
        test_safe_discovery_runner,
        test_build_stays_blocked_even_with_metadata_flags,
        test_config_write_requires_double_confirmation,
        test_config_write_requires_ready_status,
        test_config_merge_preserves_hardware_preferences,
        test_product_doctor_commands,
        test_project_workflow_state_and_next_step,
        test_task_workflows_are_safe_and_intent_based,
        test_product_doctor_bench_readiness_with_artifacts,
        test_hardware_butler_cli_bench_runbook_help_smoke,
        test_safe_write_rejects_workspace_escape,
        test_runner_minimal_env_does_not_leak_secret,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    cleanup_generated_state()


if __name__ == "__main__":
    main()
