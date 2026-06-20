# Adversarial Iteration 005: Product Checks And Security Hardening

## Goal

Move the hardware butler from safe MVP toward a productized local tool with self-diagnosis, status reporting, and stronger execution/write boundaries.

## Multi-Agent Findings

Security review identified five maturity gaps:

- Config proposals defaulted future flash/debug/observe preferences to `auto`.
- Product writes could target arbitrary output paths and did not reject symlinks.
- Build plans rendered `subprocess.list2cmdline` as PowerShell snippets.
- Safe runner allowlist checked scripts/subcommands but not full argv schema.
- Child process environment and output capture were too broad.

## Implemented

- `tools/product_doctor.py`
  - Adds `capabilities`, `doctor`, and `status` reports.
  - Detects optional local tool executables without invoking hardware actions.
  - Warns when existing config has hardware preferences set to `auto`.
  - Reads `onboarding-manifest.json` before treating safe discovery as complete.

- `tools/safe_io.py`
  - Restricts product writes to trusted roots.
  - Rejects symlink write paths.
  - Uses atomic writes and optional backups.

- `tools/config_proposal.py`
  - Proposes only build-related workflow configuration by default.
  - Preserves existing flash/debug/observe preferences.
  - Uses safe writes and backs up existing config before confirmed writes.

- `tools/command_runner.py`
  - Adds exact argv schema checks for every safe allowlist entry.
  - Uses a minimal child-process environment and `stdin=DEVNULL`.
  - Reads stdout/stderr with bounded in-memory capture.

- `tools/build_plan.py`
  - Renders command argv as JSON instead of PowerShell command text.

- `tools/hardware_butler.py`
  - Exposes `capabilities`, `doctor`, and `status`.
  - Uses safe writes for `--out` and onboarding reports.
  - Writes `onboarding-manifest.json` so `status` can validate discovery results.

- `tests/validate_hardware_butler.py`
  - Expands validation to 15 checks covering product commands, config safety, argv grammar, JSON argv rendering, manifest-backed status, minimal environment, and workspace write rejection.

## Verification Result

Passed on 2026-06-07.

- `python -m py_compile tools\safe_io.py tools\product_doctor.py tools\hardware_butler.py tools\command_runner.py tools\build_plan.py tools\config_proposal.py tools\hardware_butler_inspect.py tools\build_log_classifier.py tools\cubemx_ioc_summary.py tools\debug_logbook.py tests\validate_hardware_butler.py`
- `python -B tests\validate_hardware_butler.py`
  - Passed 15 checks.
- `python -B tools\hardware_butler.py capabilities --json`
  - Reported 10 available safe capabilities and 3 planned gated capabilities.
- `python -B tools\hardware_butler.py doctor --root tests\fixtures\cubemx-basic --json`
  - Status: `warning`
  - Errors: `0`
  - Warning: existing fixture config has hardware preferences set to `auto`.
- `python -B tools\hardware_butler.py status --root tests\fixtures\cubemx-basic --json`
  - Without a manifest, reports `needs-safe-discovery`.
  - After `onboard`, reports Keil backend, successful discovery summary, and `ready-with-config-warning` because the existing fixture config still has hardware preferences set to `auto`.

## Remaining Productization Gates

- Design a separate confirmed-build command with command id, exact config diff, and explicit user confirmation.
- Add process-tree termination if future allowlisted commands may spawn children.
- Add report redaction controls before publishing logs outside the local workspace.
