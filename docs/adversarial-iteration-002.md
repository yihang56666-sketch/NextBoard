# Adversarial Iteration 002: Config Proposal And Butler CLI

## Goal

Move from inspection/build-plan output toward a usable hardware development butler CLI while keeping all build and hardware-changing actions gated.

## Supervisor Agent Attempt

Requested external supervisor agents:

- `embeddedskills-lab-operator`: blocked by platform thread limit.

Fallback supervision was performed in-session with these review lenses:

- Embedded execution safety
- Hardware side-effect safety
- Product usability

## Decision

Selected implementation:

1. Add a dry-run `.embeddedskills/config.json` proposal generator.
2. Add a unified `hardware_butler.py` CLI facade.
3. Do not execute build, flash, debug, reset, CAN send, or network scan from the facade.

Rejected implementation:

- A command that writes `.embeddedskills/config.json` by default.
- A command that immediately runs `workflow_run.py build`.
- Any automatic flash/debug operation.

## Implemented

- `tools/config_proposal.py`
  - Reads `tools/build_plan.py`.
  - Proposes workflow + backend config.
  - Requires explicit `keil.target`, `gcc.preset`, or `eide.config` before writing.
  - Requires both `--write` and `--confirm-write` to write.
  - Merges with existing config instead of blindly replacing it.

- `tools/hardware_butler.py`
  - Adds `inspect`.
  - Adds `detect`.
  - Adds `plan-build`.
  - Adds `propose-config`.
  - Adds `classify-log`.

## Acceptance Criteria

- Dry-run config proposal must not create `.embeddedskills/config.json`.
- Missing Keil target must report `required_inputs`.
- Providing target must produce `status: ready-to-write`.
- Unified CLI must be able to call build planning and config proposal.
- Build/flash/debug actions must remain outside default execution.

## Verification

Commands run:

```powershell
python -m py_compile tools\config_proposal.py tools\hardware_butler.py tools\build_plan.py tools\cube_detect.py
python tools\config_proposal.py --root tests\fixtures\cubemx-basic --json
python tools\config_proposal.py --root tests\fixtures\cubemx-basic --target Blinky --json
python tools\hardware_butler.py plan-build --root tests\fixtures\cubemx-basic --json
python tools\hardware_butler.py propose-config --root tests\fixtures\cubemx-basic --target Blinky --out docs\inspections\cubemx-basic\config-proposal.md
python tools\hardware_butler.py propose-config --root tests\fixtures\cubemx-basic --target Blinky --write --confirm-write --json
python tools\hardware_butler.py classify-log tests\fixtures\logs\gcc-errors.log --json
```

Observed result:

- Missing target returns `status: needs-input` and `required_inputs: ["keil.target"]`.
- Providing target `Blinky` returns `status: ready-to-write`.
- Explicit `--write --confirm-write` writes `tests/fixtures/cubemx-basic/.embeddedskills/config.json`.
- CLI `plan-build` selects backend `keil` with score `90`.
- CLI `classify-log` returns missing include, linker summary failure, and undefined symbol categories.

## Next Iteration

Add a guarded config writer verification path:

- Write config only for fixture/project after explicit confirmation.
- Run embeddedskills project discovery commands only after config exists.
- Keep build execution behind an additional confirmation gate.
