# Adversarial Iteration 004: Trusted Runner And Onboarding

## Goal

Close the remaining safe-runner review gap and make the MVP easier to use on a real project folder.

## Review Finding

The previous runner checked script allowlists but accepted PATH-resolved `python` or `py` executable names. On Windows, that could resolve to an unexpected interpreter and weaken the safe runner boundary.

## Implemented

- `tools/build_plan.py`
  - Emits `sys.executable` for all generated Python commands.

- `tools/command_runner.py`
  - Rejects bare `python` and `py`.
  - Rejects non-trusted absolute Python interpreter paths.
  - Requires the trusted interpreter to match the current `sys.executable`.
  - Normalizes allowlisted scripts to absolute repository-local paths before execution.
  - Keeps `embeddedskills/workflow/scripts/workflow_run.py build` blocked by hard allowlist even when writes and confirmation flags are allowed.

- `tools/hardware_butler.py onboard`
  - Runs first-pass safe onboarding.
  - Writes project reports.
  - Runs only safe build-discovery commands.
  - Generates a config proposal without writing `.embeddedskills/config.json`.

- `tests/validate_hardware_butler.py`
  - Adds regression checks for trusted Python, bare `python`, bare `py`, untrusted absolute Python, absolute allowlisted script normalization, safe discovery, workflow build blocking, and config write confirmation.

## Verification Result

Passed on 2026-06-07.

- `python -m py_compile tools\project_scanner.py tools\cubemx_ioc_summary.py tools\cube_detect.py tools\build_log_classifier.py tools\debug_logbook.py tools\hardware_butler_inspect.py tools\build_plan.py tools\config_proposal.py tools\command_runner.py tools\hardware_butler.py tests\validate_hardware_butler.py`
- `python tests\validate_hardware_butler.py`
  - Passed 8 checks.
- `python tools\hardware_butler.py onboard --root tests\fixtures\cubemx-basic --target Blinky --out-dir docs\inspections\cubemx-basic --json`
  - Status: `ready-for-config-review`
  - Discovery summary: `ok=2`, `error=0`, `timeout=0`, `skipped=4`
  - Config status: `ready-to-write`
  - No build, flash, erase, debug, bus transmit, network scan, or config write was performed.
