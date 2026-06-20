# Adversarial Iteration 001: Safe Build Plan Runner

## Goal

Optimize the hardware development butler toward a usable landing project without prematurely touching real hardware state.

## Agent Setup

Requested external sub-agents:

- Embedded execution critic: failed with platform `429 Too Many Requests`.
- Hardware safety critic: not started because the platform reported thread limit.

Fallback used in this session:

- Embedded execution perspective
- Hardware safety perspective
- Product butler perspective

Previous successful embedded-agent feedback from the prior round was also carried forward:

- Detect CubeMX `.ioc` first.
- Cross-check `.uvprojx/.uvmpw`, `CMakeLists.txt`, `CMakePresets.json`, startup files, and linker scripts.
- Prefer Keil when Keil project evidence and MDK metadata exist.
- Prefer CMake/GCC when CMake project evidence exists.
- Do not guess when multiple supported backends have similar confidence.
- Keep flash, erase, write-memory, CAN send, and network scan behind explicit confirmation.

## Options Considered

### Option A: Execute Build Immediately

Rejected for this iteration.

Reason: build writes artifacts and may require environment-specific configuration. The butler should first produce a reviewable plan.

### Option B: Generate A Safe Build Plan

Selected.

Reason: it is useful immediately, stays read-only except optional Markdown output, and creates a controlled bridge from project inspection to embeddedskills execution.

### Option C: Start Flash/Debug Automation

Rejected for this iteration.

Reason: hardware-changing actions need explicit target, probe, reset strategy, image format, and user confirmation.

## Implemented

- `tools/build_plan.py`
  - Imports `tools/cube_detect.py`.
  - Emits structured `argv` commands instead of shell-only strings.
  - Maps selected backend to embeddedskills discovery commands.
  - Marks build execution as confirmation-gated.
  - Lists flash/debug/CAN/network gates explicitly.

- `docs/superpowers/plans/2026-06-07-safe-build-plan-runner.md`
  - Records the implementation slice and verification commands.

- `docs/implementation-roadmap.md`
  - Records the current landing slice under CubeMX bring-up.

- `docs/inspections/cubemx-basic/build-plan.md`
  - Example generated plan for the CubeMX fixture.

## Verification

Commands run:

```powershell
python -m py_compile tools\build_plan.py tools\cube_detect.py tools\hardware_butler_inspect.py
python tools\build_plan.py --root tests\fixtures\cubemx-basic --json
python tools\build_plan.py --root tests\fixtures\cubemx-basic --out docs\inspections\cubemx-basic\build-plan.md
```

Observed result:

- The fixture selected `keil` with score `90`.
- Generated commands include project dossier creation, CubeMX backend detection, Keil project scan, Keil target listing, confirmation-gated workflow build, and build-log classification.
- No generated command has `hardware_side_effect: true`.

## Next Iteration

Implement a config writer in dry-run mode:

- Read `tools/build_plan.py` output.
- Generate a proposed `.embeddedskills/config.json`.
- Do not write it unless the user confirms.
- Validate that Keil target or GCC preset is selected before build.
