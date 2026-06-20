# Hardware Butler Productization Doctor And Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add product-grade self-diagnosis, capability discovery, and project status commands to make the hardware butler easier to operate as a real local product.

**Architecture:** Keep deterministic product checks in a new `tools/product_doctor.py` module. Keep `tools/hardware_butler.py` as the CLI facade. Extend `tests/validate_hardware_butler.py` with lightweight assertions that do not touch real hardware.

**Tech Stack:** Python standard library, existing `cube_detect`, `config_proposal`, `command_runner`, `build_plan`, Markdown/JSON CLI outputs.

---

### Task 1: Product Doctor Module

**Files:**
- Create: `tools/product_doctor.py`
- Modify: none
- Test: `tests/validate_hardware_butler.py`

- [ ] **Step 1: Create capability matrix functions**

Implement `capabilities()` returning fixed product capabilities with `status`, `safe_by_default`, `command`, and `notes`. Include onboard, inspect, detect, plan-build, run-plan, propose-config, classify-log, doctor, and status.

- [ ] **Step 2: Create environment doctor**

Implement `doctor(root: Path)` that checks Python, core repo paths, embeddedskills scripts, agent role files, Codex config, writable project report path, selected backend, config presence, and safe runner policy.

- [ ] **Step 3: Create project status**

Implement `project_status(root: Path)` that reports backend, CubeMX count, config file presence, report file presence, safe discovery readiness, and next actions.

- [ ] **Step 4: Create Markdown renderers**

Implement `render_capabilities_markdown()`, `render_doctor_markdown()`, and `render_status_markdown()` with compact tables/lists.

### Task 2: CLI Integration

**Files:**
- Modify: `tools/hardware_butler.py`
- Test: `tests/validate_hardware_butler.py`

- [ ] **Step 1: Import product_doctor**

Add `import product_doctor`.

- [ ] **Step 2: Add `capabilities` command**

Expose `python tools\hardware_butler.py capabilities --json`.

- [ ] **Step 3: Add `doctor` command**

Expose `python tools\hardware_butler.py doctor --root <project-root> --json`.

- [ ] **Step 4: Add `status` command**

Expose `python tools\hardware_butler.py status --root <project-root> --json`.

### Task 3: Validation

**Files:**
- Modify: `tests/validate_hardware_butler.py`

- [ ] **Step 1: Add module assertions**

Assert the capability matrix includes `onboard`, `doctor`, and `status`; assert `doctor(FIXTURE)` returns no `error` checks; assert `project_status(FIXTURE)` selects Keil.

- [ ] **Step 2: Run validation**

Run: `python -B tests\validate_hardware_butler.py`
Expected: every check prints `PASS`.

- [ ] **Step 3: Run CLI smoke checks**

Run:

```powershell
python -B tools\hardware_butler.py capabilities --json
python -B tools\hardware_butler.py doctor --root tests\fixtures\cubemx-basic --json
python -B tools\hardware_butler.py status --root tests\fixtures\cubemx-basic --json
```

Expected: exit code 0 for all commands.

### Task 4: Docs And Iteration Record

**Files:**
- Modify: `README.md`
- Modify: `docs/hardware-butler-usage.md`
- Add: `docs/adversarial-iteration-005.md`
- Modify: `docs/adversarial-iteration-log.md`

- [ ] **Step 1: Document product commands**

Add concise usage for `capabilities`, `doctor`, and `status`.

- [ ] **Step 2: Record adversarial iteration**

Document that this round productizes the MVP through self-diagnosis and status reporting, while keeping hardware actions gated.

- [ ] **Step 3: Final verification**

Run the validation and CLI smoke checks again and record results in `docs/adversarial-iteration-005.md`.
