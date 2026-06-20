# Adversarial Iteration 003: Safe Discovery Runner

## Goal

Move past static plans and let the butler execute safe discovery commands automatically.

## Safety Position

Allowed by default:

- Read-only inspection commands.
- Backend discovery commands.
- Build log classification commands without placeholders.

Blocked by default:

- Commands declaring writes.
- Commands requiring confirmation.
- Commands with hardware side effects.
- Commands with placeholders.
- Commands that do not use the current trusted Python interpreter.
- Commands whose script or subcommand is not on the hard safe allowlist.

## Implemented

- `tools/command_runner.py`
  - Reads `tools/build_plan.py`.
  - Filters commands by phase.
  - Skips unsafe commands with explicit reasons.
  - Applies a hard allowlist for supported safe Python scripts and subcommands.
  - Requires planned commands to use `sys.executable` instead of a PATH-resolved `python`.
  - Executes allowlisted scripts through normalized absolute script paths.
  - Forces UTF-8 child-process and CLI output for Windows paths with non-ASCII characters.
  - Captures stdout, stderr, return code, duration, and status.

- `tools/build_plan.py`
  - Emits the current trusted Python interpreter path for all generated Python commands.

- `tests/validate_hardware_butler.py`
  - Regresses CubeMX detection, plan shape, trusted Python usage, safe discovery execution, hard allowlist blocking, and config write confirmation.

- `tools/hardware_butler.py run-plan`
  - Exposes safe plan execution from the unified CLI.

## Verification Target

Run the CubeMX fixture through build-discovery:

```powershell
python tools\hardware_butler.py run-plan --root tests\fixtures\cubemx-basic --phase build-discovery --json
```

## Verification Result

Passed on 2026-06-07.

- Command: `python tools\hardware_butler.py run-plan --root tests\fixtures\cubemx-basic --phase build-discovery --json`
- Result summary: `ok=2`, `error=0`, `timeout=0`, `skipped=4`
- Executed safely: `Scan Keil projects`, `List Keil targets`
- Skipped safely: inspect phase commands, build-plan command, placeholder diagnose command
- Report: `docs/inspections/cubemx-basic/discovery-run.md`

Additional safety checks passed after hard allowlist review:

- `python tools\hardware_butler.py run-plan --root tests\fixtures\cubemx-basic --json`
  - Result summary: `ok=3`, `error=0`, `timeout=0`, `skipped=3`
  - Confirmed default all-phase mode runs only dossier-free detection and build discovery.
- `python tools\hardware_butler.py run-plan --root tests\fixtures\cubemx-basic --phase build-plan --allow-writes --allow-confirmation --json`
  - Result summary: `ok=0`, `error=0`, `timeout=0`, `skipped=6`
  - Confirmed `embeddedskills/workflow/scripts/workflow_run.py build` is still blocked because it is not on the safe runner allowlist.
- `python tools\command_runner.py --root tests\fixtures\cubemx-basic --json`
  - Result summary: `ok=3`, `error=0`, `timeout=0`, `skipped=3`
  - Confirmed the direct runner entrypoint handles UTF-8 JSON output.
- `python tests\validate_hardware_butler.py`
  - Passed 6 validation checks, including rejection of a bare `python` executable in safe runner input.
