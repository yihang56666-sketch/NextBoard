---
name: hardware-development-butler
description: Hardware development butler for embedded projects. Use when Codex needs to onboard or manage a hardware/firmware project; collect schematic, PCB, BOM, datasheet, manual, CubeMX .ioc, Keil, CMake/GCC, EIDE, build logs, debug logs, serial, CAN, network, J-Link, OpenOCD, probe-rs, ST-Link, or CMSIS-DAP evidence; generate board and firmware profiles; propose .embeddedskills/config.json; classify build errors; or coordinate a gated build, flash, debug, observe, diagnose, and fix workflow.
---

# Hardware Development Butler

Use this skill as a safety-first hardware project manager. It combines:

- A packaged CLI runtime under the plugin `scripts/` directory.
- `nextboard` knowledge for hardware design, schematic/BOM risk, board profiles, and validation planning.
- `embeddedskills` tooling for Keil/GCC/EIDE discovery plus gated flash/debug/observe backends.
- Project-local `chip-bringup` workflow, when present, for chip document search/download, manual summaries, CubeMX pin/peripheral configuration, FreeRTOS implementation planning, and hardware safety gates.

## First Pass

1. Identify the project root. Prefer the user's firmware or board-project directory, not the plugin directory.
2. Run a read-only/product check first:

```powershell
python <skill-dir>\scripts\run_hardware_butler.py doctor --root <project-root> --json
```

3. If the root is plausible, run safe onboarding:

```powershell
python <skill-dir>\scripts\run_hardware_butler.py onboard --root <project-root> --out-dir docs\inspections\<project-name> --json
```

4. Read the generated dossier, board profile, firmware profile, build plan, discovery run, and config proposal before recommending build, flash, debug, or hardware changes.

The wrapper sets `HARDWARE_BUTLER_WORKSPACE_ROOT` to the caller's current directory and executes the packaged runtime from the plugin, so report writes stay inside the active workspace.

## Command Guide

Use these packaged commands instead of reimplementing scanners:

```powershell
python <skill-dir>\scripts\run_hardware_butler.py capabilities --json
python <skill-dir>\scripts\run_hardware_butler.py detect --root <project-root> --json
python <skill-dir>\scripts\run_hardware_butler.py plan-build --root <project-root>
python <skill-dir>\scripts\run_hardware_butler.py run-plan --root <project-root> --phase build-discovery --json
python <skill-dir>\scripts\run_hardware_butler.py propose-config --root <project-root> --target <KeilTarget> --json
python <skill-dir>\scripts\run_hardware_butler.py classify-log <build-log-path> --json
python <skill-dir>\scripts\run_hardware_butler.py status --root <project-root> --json
python <skill-dir>\scripts\run_hardware_butler.py patch-ioc --root <project-root> --function gpio-output --pin PD12 --json
python <skill-dir>\scripts\run_hardware_butler.py firmware-integrate --root <project-root> --feature led-blink --pin PD12 --function gpio-output --json
python <skill-dir>\scripts\run_hardware_butler.py bench-runbook --root <project-root> --action build-flash --target <chip> --probe <probe> --voltage <voltage> --current-limit <limit> --erase-scope <scope> --recovery <path> --backend openocd --json
python <skill-dir>\scripts\run_hardware_butler.py safety-audit --root <project-root> --json
```

Write `.embeddedskills/config.json` only when all required inputs are explicit and the user has approved the write:

```powershell
python <skill-dir>\scripts\run_hardware_butler.py propose-config --root <project-root> --target <KeilTarget> --write --confirm-write --json
```

## Safety Rules

- Treat `doctor`, `capabilities`, `detect`, `plan-build`, `status`, and `classify-log` as read-only.
- Treat `inspect` and `onboard` as report-writing commands only.
- Treat `bench-runbook`, `bench-preflight`, and workflow `--dry-run` as no-hardware preparation paths: no subprocess hardware action, no token consumption, no safety log/state/config writes.
- Treat `safety-audit` as read-only; it may reveal token hashes and artifact hashes, but never raw token values.
- Treat `patch-ioc` and `firmware-integrate` as preview-only by default; writing requires `--write --confirm-write` and must stay inside safe `.ioc` keys or CubeMX `USER CODE` blocks.
- Do not build, flash, erase, halt, reset, resume, write memory, transmit CAN frames, or scan networks without explicit user confirmation for the exact device and action.
- Do not claim real flash/debug/observe is implemented by the butler runtime yet. Those paths remain planned-gated unless a backend-specific executor has verified device identity, voltage/current evidence, artifact hash binding, rollback logging, and bounded observation.
- Use `run-plan --phase build-discovery` for automatic execution; the safe runner has a hard allowlist and blocks build/flash/debug/bus actions.
- If evidence is missing or contradictory, write the uncertainty into the project docs instead of guessing pinouts, electrical limits, flash algorithms, or device identity.

## Routing

- For a specific chip/board request such as finding datasheets/manuals/schematics, summarizing a chip manual, explaining CubeMX configuration for a pin/peripheral, or designing a FreeRTOS implementation for an already configured interface, use the project-local `.agents/skills/chip-bringup` workflow when available.
- For schematic interpretation, component selection, BOM risk, power/clock/reset/boot/debug-interface reasoning, read `references/agent-routing.md` and use the `nextboard` role.
- For Keil, CMake/GCC, EIDE, J-Link, OpenOCD, probe-rs, serial, CAN, network, RTT/SWO, or workflow tooling, read `references/agent-routing.md` and use the `embeddedskills` role.
- For product status, packaging, safety boundaries, and task orchestration, stay in the butler role.

## References

- `references/usage.md`: command examples and expected project flow.
- `references/safety-model.md`: execution gates and hardware-action policy.
- `references/agent-routing.md`: when to use nextboard vs embeddedskills.
- `references/runtime-package.md`: packaged runtime layout and validation commands.
