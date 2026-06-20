# Safe Build Plan Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a read-only build plan from CubeMX/backend detection without executing build, flash, debug, or bus actions.

**Architecture:** Add a thin `tools/build_plan.py` layer on top of `tools/cube_detect.py`. The script emits JSON/Markdown commands as structured `argv` lists, marks side effects and confirmation gates, and maps supported backends to embeddedskills scanner commands.

**Tech Stack:** Python standard library, existing `tools/cube_detect.py`, embeddedskills script paths.

---

### Task 1: Add Build Plan Generator

**Files:**
- Create: `tools/build_plan.py`
- Test: command-line JSON and Markdown execution on `tests/fixtures/cubemx-basic`

- [x] **Step 1: Create `tools/build_plan.py`**

Implement a read-only planner that imports `cube_detect.detect()`, converts selected backend into scanner commands, and explicitly lists excluded hardware actions.

- [x] **Step 2: Verify Syntax**

Run: `python -m py_compile tools\build_plan.py`

- [x] **Step 3: Verify JSON Output**

Run: `python tools\build_plan.py --root tests\fixtures\cubemx-basic --json`

Expected: status `ready`, selected backend `keil`, at least one Keil scan command, and flash/debug actions listed as confirmation-gated exclusions.

- [x] **Step 4: Verify Markdown Output**

Run: `python tools\build_plan.py --root tests\fixtures\cubemx-basic --out docs\inspections\cubemx-basic\build-plan.md`

Expected: Markdown plan written with selected backend and planned commands.
