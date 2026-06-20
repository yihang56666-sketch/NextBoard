# Config Proposal And CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the next landing slice for the hardware development butler: dry-run `.embeddedskills/config.json` proposal and a unified CLI facade.

**Architecture:** Build on `tools/build_plan.py`. `tools/config_proposal.py` proposes or explicitly writes project-local `.embeddedskills/config.json`. `tools/hardware_butler.py` exposes safe subcommands for inspect, detect, plan-build, propose-config, and classify-log.

**Tech Stack:** Python standard library, existing butler tools, embeddedskills config schema.

---

### Task 1: Config Proposal

**Files:**
- Create: `tools/config_proposal.py`

- [x] Generate proposed workflow/Keil/GCC/EIDE config from selected backend.
- [x] Keep dry-run as default.
- [x] Require explicit target/preset/config before writing.
- [x] Require `--write --confirm-write` before modifying `.embeddedskills/config.json`.

### Task 2: Unified CLI

**Files:**
- Create: `tools/hardware_butler.py`

- [x] Add `inspect`.
- [x] Add `detect`.
- [x] Add `plan-build`.
- [x] Add `propose-config`.
- [x] Add `classify-log`.

### Task 3: Verification

Run:

```powershell
python -m py_compile tools\config_proposal.py tools\hardware_butler.py
python tools\config_proposal.py --root tests\fixtures\cubemx-basic --json
python tools\config_proposal.py --root tests\fixtures\cubemx-basic --target Blinky --json
python tools\hardware_butler.py plan-build --root tests\fixtures\cubemx-basic --json
python tools\hardware_butler.py propose-config --root tests\fixtures\cubemx-basic --target Blinky --out docs\inspections\cubemx-basic\config-proposal.md
```
