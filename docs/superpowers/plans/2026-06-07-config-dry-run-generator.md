# Config Dry-Run Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a proposed `.embeddedskills/config.json` from CubeMX/backend evidence without writing it unless explicitly requested.

**Architecture:** Add `tools/config_plan.py` as a safe bridge after `tools/build_plan.py`. It reads backend detection, resolves Keil target or GCC preset when unambiguous, emits JSON/Markdown dry-run output, and refuses to overwrite existing config unless `--force` is supplied with `--write`.

**Tech Stack:** Python standard library, existing `tools/cube_detect.py`, XML parsing for Keil targets, JSON parsing for CMake presets.

---

### Task 1: Add Config Proposal Generator

**Files:**
- Create: `tools/config_plan.py`
- Test: command-line JSON and Markdown execution on `tests/fixtures/cubemx-basic`

- [x] **Step 1: Implement dry-run config generation**

Create `tools/config_plan.py` with default dry-run output and optional explicit write.

- [x] **Step 2: Verify syntax**

Run: `python -m py_compile tools\config_plan.py`

- [x] **Step 3: Verify dry-run JSON**

Run: `python tools\config_plan.py --root tests\fixtures\cubemx-basic --json`

Expected: status `ready`, backend `keil`, config contains `workflow.preferred_build=keil`, `keil.project=Blinky.uvprojx`, and `keil.target=Blinky`.

- [x] **Step 4: Verify Markdown output**

Run: `python tools\config_plan.py --root tests\fixtures\cubemx-basic --out docs\inspections\cubemx-basic\config-plan.md`

Expected: Markdown config proposal is written without writing `.embeddedskills/config.json`.
