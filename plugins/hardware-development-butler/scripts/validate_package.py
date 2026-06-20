"""Lightweight structural validation for the packaged hardware butler plugin."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = PLUGIN_ROOT / "skills" / "hardware-development-butler"
REPO_ROOT = PLUGIN_ROOT.parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_plugin_json() -> None:
    path = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    require(data["name"] == "hardware-development-butler", "plugin name mismatch")
    require(re.match(r"^\d+\.\d+\.\d+$", data["version"]), "version must be semver")
    require(data.get("skills") == "./skills/", "skills path must be ./skills/")
    interface = data.get("interface", {})
    prompts = interface.get("defaultPrompt")
    require(isinstance(prompts, list), "interface.defaultPrompt must be an array")
    require(1 <= len(prompts) <= 3, "defaultPrompt must contain 1-3 prompts")
    require("[TODO:" not in path.read_text(encoding="utf-8"), "plugin.json contains TODO placeholder")
    long_description = interface.get("longDescription", "")
    for term in ("chip", "manual", "CubeMX", "FreeRTOS", "confirmation"):
        require(term.lower() in long_description.lower(), f"plugin longDescription missing capability term: {term}")


def validate_skill() -> None:
    skill = SKILL_ROOT / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    require("[TODO:" not in text, "SKILL.md contains TODO placeholder")
    require(text.startswith("---\n"), "SKILL.md must start with YAML frontmatter")
    require("name: hardware-development-butler" in text, "SKILL.md name missing")
    require("description:" in text, "SKILL.md description missing")
    require((SKILL_ROOT / "agents" / "openai.yaml").exists(), "agents/openai.yaml missing")
    require((SKILL_ROOT / "scripts" / "run_hardware_butler.py").exists(), "skill wrapper missing")
    for name in ("usage.md", "safety-model.md", "agent-routing.md", "runtime-package.md"):
        require((SKILL_ROOT / "references" / name).exists(), f"reference missing: {name}")
    usage = (SKILL_ROOT / "references" / "usage.md").read_text(encoding="utf-8")
    for command in (
        "chip-dossier",
        "summarize-manual",
        "advise-pin",
        "patch-ioc",
        "firmware-plan",
        "firmware-patch",
        "firmware-integrate",
        "plan-action",
        "execute-action",
        "safety-audit",
        "bench-runbook",
        "bench-preflight",
        "workflow-dry-run",
    ):
        require(command in usage, f"usage.md missing command: {command}")
        require(command in text or command in usage, f"SKILL.md/usage.md missing command: {command}")
    validate_boundary_text()


def validate_boundary_text() -> None:
    files = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "docs" / "hardware-butler-usage.md",
        SKILL_ROOT / "SKILL.md",
        SKILL_ROOT / "references" / "usage.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in files if path.exists()).lower()
    require("planned-gated" in combined, "docs must mark real flash/debug/observe as planned-gated")
    require("real flash/debug/observe remains planned-gated" in combined, "docs must explicitly state real flash/debug/observe remains planned-gated")


def validate_runtime() -> None:
    cleanup_generated_bytecode()
    required = [
        "scripts/tools/hardware_butler.py",
        "scripts/pyproject.toml",
        "scripts/requirements.txt",
        "scripts/requirements-dev.txt",
        "scripts/conftest.py",
        "scripts/tools/runtime_context.py",
        "scripts/tools/command_runner.py",
        "scripts/tools/build_plan.py",
        "scripts/tools/bench_runbook.py",
        "scripts/tools/product_doctor.py",
        "scripts/tools/chip_dossier.py",
        "scripts/tools/document_providers.py",
        "scripts/tools/pin_capabilities.py",
        "scripts/tools/cubemx_config_advisor.py",
        "scripts/tools/firmware_intent_planner.py",
        "scripts/tools/firmware_code_patcher.py",
        "scripts/tools/hardware_action_plan.py",
        "scripts/tools/hardware_action_executor.py",
        "scripts/tools/hardware_action_audit.py",
        "scripts/tools/manual_summarizer.py",
        "scripts/embeddedskills/keil/scripts/keil_project.py",
        "scripts/embeddedskills/gcc/scripts/gcc_project.py",
        "scripts/embeddedskills/workflow/scripts/workflow_run.py",
        "scripts/embeddedskills/safety_gate.py",
        "scripts/embeddedskills/safety_cli.py",
        "scripts/nextboard/README.md",
        "scripts/tests/validate_hardware_butler.py",
        "scripts/tests/unit/test_langchain_agent_gate.py",
        "scripts/.codex/config.toml",
        "skills/chip-bringup/SKILL.md",
        "skills/chip-bringup/references/source-and-download-policy.md",
        "skills/chip-bringup/references/manual-summary-template.md",
        "skills/chip-bringup/references/cubemx-pin-config-guide.md",
        "skills/chip-bringup/references/firmware-rtos-implementation.md",
        "skills/chip-bringup/references/hardware-safety-gates.md",
    ]
    for item in required:
        require((PLUGIN_ROOT / item).exists(), f"runtime file missing: {item}")

    forbidden = []
    for path in PLUGIN_ROOT.rglob("*"):
        if is_inaccessible_pytest_tmp(path):
            continue
        if path.name in {
            ".git",
            "__pycache__",
            ".pytest_cache",
            ".tmp-pytest",
            ".tmp-plugin-smoke",
            ".mypy_cache",
            ".ruff_cache",
        }:
            forbidden.append(str(path.relative_to(PLUGIN_ROOT)))
        if path.suffix.lower() in {".pyc", ".pyo"}:
            forbidden.append(str(path.relative_to(PLUGIN_ROOT)))
    for rel in ("scripts/docs/inspections", "scripts/docs/chip", "scripts/tests/tmp"):
        if (PLUGIN_ROOT / rel).exists():
            forbidden.append(rel)
    require(not forbidden, f"forbidden local state found: {forbidden[:5]}")


def cleanup_generated_bytecode() -> None:
    """Remove local state generated by validation or smoke tests."""
    for path in PLUGIN_ROOT.rglob("__pycache__"):
        if path.is_dir():
            shutil.rmtree(path)
    for path in PLUGIN_ROOT.rglob(".tmp-pytest"):
        if path.is_dir():
            try:
                shutil.rmtree(path)
            except PermissionError:
                if not is_inaccessible_pytest_tmp(path):
                    raise
    for path in PLUGIN_ROOT.rglob(".tmp-plugin-smoke"):
        if path.is_dir():
            shutil.rmtree(path)
    for path in PLUGIN_ROOT.rglob(".ruff_cache"):
        if path.is_dir():
            shutil.rmtree(path)
    for path in PLUGIN_ROOT.rglob("*.py[co]"):
        if path.is_file():
            path.unlink()


def is_inaccessible_pytest_tmp(path: Path) -> bool:
    """Recognize Windows sandbox pytest temp roots that cannot be traversed."""
    if path.name != ".tmp-pytest":
        return False
    try:
        path.relative_to(PLUGIN_ROOT / "scripts" / "tests")
    except ValueError:
        return False
    try:
        list(path.iterdir())
    except PermissionError:
        return True
    return False


def validate_source_sync() -> None:
    pairs = [
        ("tools/hardware_butler.py", "scripts/tools/hardware_butler.py"),
        ("tools/hardware_action_plan.py", "scripts/tools/hardware_action_plan.py"),
        ("tools/hardware_action_executor.py", "scripts/tools/hardware_action_executor.py"),
        ("tools/hardware_action_audit.py", "scripts/tools/hardware_action_audit.py"),
        ("tools/bench_runbook.py", "scripts/tools/bench_runbook.py"),
        ("tools/product_doctor.py", "scripts/tools/product_doctor.py"),
        ("tools/pin_capabilities.py", "scripts/tools/pin_capabilities.py"),
        ("tools/backends/langchain_agent.py", "scripts/tools/backends/langchain_agent.py"),
        ("embeddedskills/workflow/scripts/workflow_run.py", "scripts/embeddedskills/workflow/scripts/workflow_run.py"),
        ("embeddedskills/safety_gate.py", "scripts/embeddedskills/safety_gate.py"),
        ("embeddedskills/safety_cli.py", "scripts/embeddedskills/safety_cli.py"),
        ("tests/validate_hardware_butler.py", "scripts/tests/validate_hardware_butler.py"),
        ("tests/unit/test_langchain_agent_gate.py", "scripts/tests/unit/test_langchain_agent_gate.py"),
        ("pyproject.toml", "scripts/pyproject.toml"),
        ("conftest.py", "scripts/conftest.py"),
    ]
    if not (REPO_ROOT / "tools" / "hardware_butler.py").exists():
        return
    mismatches = []
    for source_rel, packaged_rel in pairs:
        source = REPO_ROOT / source_rel
        packaged = PLUGIN_ROOT / packaged_rel
        require(source.exists(), f"source file missing for sync check: {source_rel}")
        require(packaged.exists(), f"packaged file missing for sync check: {packaged_rel}")
        if sha256(source) != sha256(packaged):
            mismatches.append(f"{source_rel} != {packaged_rel}")
    require(not mismatches, f"packaged runtime is out of sync with source: {mismatches[:5]}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    validate_plugin_json()
    validate_skill()
    validate_runtime()
    validate_source_sync()
    print("PASS validate_plugin_json")
    print("PASS validate_skill")
    print("PASS validate_runtime")
    print("PASS validate_source_sync")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
