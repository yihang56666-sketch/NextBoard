# Adversarial Iteration Log

## Round 1: Project Inspection MVP

Decision:

- Start with read-only inspection, not direct flash/debug automation.
- Build stable evidence first: project dossier, CubeMX summary, board profile, firmware profile, issues, debug logbook.
- Keep real hardware actions behind explicit confirmation.

Implemented:

- `tools/project_scanner.py`
- `tools/cubemx_ioc_summary.py`
- `tools/build_log_classifier.py`
- `tools/debug_logbook.py`
- `tools/hardware_butler_inspect.py`
- `tools/cube_detect.py`

## Round 2: Safe Build Plan

Adversarial finding:

- A build command may still write generated build outputs and can be wrong when multiple backends or targets exist.
- The butler must recommend commands before executing them.
- Flash/debug must remain outside the build-plan tool.

Decision:

- Add `tools/build_plan.py` as a no-execution command planner.
- Map detected backend to embeddedskills command templates.
- Require explicit target/preset/config selection before build.

Implemented:

- `tools/build_plan.py`

Validation target:

- `tests/fixtures/cubemx-basic` should generate a Keil build plan with read-only scan/target steps and one gated build step.

## Round 3: Safe Discovery Runner

Adversarial finding:

- Static plans are useful, but the butler needs a controlled way to execute safe discovery commands.
- The runner cannot rely only on command metadata; it also needs a hard allowlist.

Implemented:

- `tools/command_runner.py`
- `tools/hardware_butler.py run-plan`

Validation result:

- `python tools\hardware_butler.py run-plan --root tests\fixtures\cubemx-basic --phase build-discovery --json`
- Result: `ok=2`, `error=0`, `timeout=0`, `skipped=4`

## Round 4: Trusted Runner And Onboarding

Adversarial finding:

- The safe runner must not accept PATH-resolved `python` or `py` executable names.
- A real user needs one safe first command instead of manually chaining five commands.

Implemented:

- `tools/build_plan.py` now emits `sys.executable`.
- `tools/command_runner.py` validates the trusted interpreter and normalizes allowlisted scripts.
- `tools/hardware_butler.py onboard` generates the first-pass reports and safe discovery output.
- `tests/validate_hardware_butler.py` locks the safety behavior.

Validation result:

- `python tests\validate_hardware_butler.py`
- Result: 8 checks passed.

## Round 5: Product Checks And Security Hardening

Adversarial finding:

- A mature local product needs self-diagnosis, project status, and capability discovery.
- Config proposals must not silently enable future hardware actions.
- Safe runner allowlists need full argv schema checks, not only script and subcommand checks.
- Product writes need trusted-root and symlink protections.

Implemented:

- `tools/product_doctor.py`
- `tools/safe_io.py`
- `tools/hardware_butler.py capabilities`
- `tools/hardware_butler.py doctor`
- `tools/hardware_butler.py status`
- Safer config proposal, output writes, build-plan rendering, runner environment, and runner output capture.
- Manifest-backed project status that refuses to treat stale or missing discovery reports as ready.

Validation result:

- `python -B tests\validate_hardware_butler.py`
- Result: 15 checks passed.
