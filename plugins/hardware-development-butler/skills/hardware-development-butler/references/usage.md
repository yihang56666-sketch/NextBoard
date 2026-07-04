# Hardware Butler Usage

Start with a local project root that contains board documents, CubeMX output, firmware code, or logs.

```powershell
python <skill-dir>\scripts\run_hardware_butler.py doctor --root <project-root> --json
python <skill-dir>\scripts\run_hardware_butler.py onboard --root <project-root> --out-dir docs\inspections\<project-name> --json
python <skill-dir>\scripts\run_hardware_butler.py status --root <project-root> --json
python <skill-dir>\scripts\run_hardware_butler.py brain --root <project-root> --json
python <skill-dir>\scripts\run_hardware_butler.py ask --root <project-root> --question "PD12 接了什么？" --json
python <skill-dir>\scripts\run_hardware_butler.py task --root <project-root> --intent prepare-bringup --json
python <skill-dir>\scripts\run_hardware_butler.py chip-dossier --part STM32F407VGTx --api-search --api-preset chip-docs --download --json
python <skill-dir>\scripts\run_hardware_butler.py chip-dossier --part STM32F407VGTx --api-search --api-preset board-docs --api-query "discovery schematic" --download --json
python <skill-dir>\scripts\run_hardware_butler.py advise-pin --root <project-root> --pin PB7 --function i2c --json
python <skill-dir>\scripts\run_hardware_butler.py advise-pin --root <project-root> --pin PB7 --function i2c --pin-evidence <pin-capabilities.json> --json
python <skill-dir>\scripts\run_hardware_butler.py patch-ioc --root <project-root> --function i2c --instance I2C1 --scl PB6 --sda PB7 --json
python <skill-dir>\scripts\run_hardware_butler.py firmware-integrate --root <project-root> --feature i2c-sensor-read --pin PB7 --function i2c --json
python <skill-dir>\scripts\run_hardware_butler.py bench-runbook --root <project-root> --action build-flash --target STM32F407VGTx --probe "ST-Link SN123" --voltage 3.3V --current-limit 100mA --erase-scope "firmware image only" --recovery "SWD under reset" --backend openocd --json
python <skill-dir>\scripts\run_hardware_butler.py safety-audit --root <project-root> --json
```

Main command meanings:

- `capabilities`: show available and gated product functions.
- `doctor`: check packaged runtime, optional external tools, embeddedskills files, agent role files, backend detection, config, and safe runner policy.
- `onboard`: write dossier, board profile, firmware profile, build plan, discovery report, config proposal, and manifest.
- `brain`: index local project evidence, identify missing schematic/BOM/manual/datasheet material, run deterministic risk checks, and write a project brain report.
- `ask`: answer project questions from indexed local evidence and CubeMX `.ioc` data; unknown board-level facts stay explicit.
- `task`: expand common intents such as evidence collection, hardware risk review, peripheral configuration, build-failure diagnosis, or bring-up preparation into safe local commands.
- `detect`: parse CubeMX `.ioc` and rank Keil/CMake-GCC/EIDE/Makefile evidence.
- `plan-build`: render structured argv plans without executing build commands.
- `run-plan --phase build-discovery`: run only safe allowlisted discovery commands.
- `propose-config`: generate `.embeddedskills/config.json` proposal; write only with `--write --confirm-write`.
- `classify-log`: bucket compiler/linker logs into actionable categories.
- `chip-dossier`: create a chip evidence folder, record official sources, optionally search/download validated PDFs with `chip-docs`, `board-docs`, or `part-risk` presets, and write source map/manual/CubeMX/safety notes.
- `summarize-manual`: summarize extracted datasheet/reference-manual text with evidence line numbers; missing categories stay unknown.
- `advise-pin`: inspect the project `.ioc`, optionally read package pin capability evidence, and explain CubeMX settings, conflicts, alternatives, generated-code impact, and damage-risk notes. Pin capability support is labeled `verified`, `contradicted`, `inferred`, or `unknown`.
- `patch-ioc`: prepare a safe `.ioc` diff for GPIO output or I2C pins; writing requires `--write --confirm-write` and revalidates the current `.ioc` before writing.
- `firmware-plan`: plan a HAL/FreeRTOS implementation without editing CubeMX generated code.
- `firmware-patch`: preview app-layer `Core/Inc/app_*.h`, `Core/Src/app_*.c`, and integration notes by default; writing requires `--write --confirm-write`.
- `firmware-integrate`: patch only CubeMX `USER CODE` blocks to include/init/start generated app modules; writing requires `--write --confirm-write` and revalidates current USER CODE blocks.
- `plan-action`: create a confirmation-gated build/flash/debug/reset/bus action plan and token scope.
- `execute-action`: execute only supported confirmation-token paths; `fake` backend is for dry-run integration and real hardware backends remain blocked unless explicitly implemented.
- `safety-audit`: read `.embeddedskills/safety-log.jsonl` and summarize token hashes, backend counts, execution results, and artifact hashes without exposing token values.
- `bench-runbook`: generate a no-hardware bench execution manual that aggregates readiness, action-plan evidence, preflight checks, artifact hash binding, and an actual `workflow_run.py --dry-run --json` subprocess result. It does not execute hardware actions, consume tokens, or write safety log/state/config.
- `bench-preflight`: validate a prepared workflow command package without consuming tokens, touching hardware, writing safety logs, or exposing raw token argv.
- `workflow-dry-run`: prepare build/flash/debug/observe workflow argv with redacted tokens and no subprocess execution or state/config writes.

Recommended first closed loop:

1. `doctor`
2. `onboard`
3. Review `docs/inspections/<project-name>/`
4. `propose-config` with explicit target/preset/config name
5. User-confirmed build path outside the safe runner
6. `classify-log` on failures
7. Record root cause, fix, verification, and remaining risk

Recommended chip bring-up loop:

1. `chip-dossier --part <chip> --source <official-url> --download`
2. `summarize-manual --part <chip> --document <extracted-text>`
3. `advise-pin --root <project> --pin <pin> --function <function> --pin-evidence <pin-capabilities.json>` when package evidence is available; otherwise missing evidence remains `unknown` or `.ioc`-only `inferred`.
4. `patch-ioc --root <project> --function <function> ... --json`, then write only after reviewing the diff with `--write --confirm-write`
5. Regenerate CubeMX code manually and build once.
6. `firmware-plan --root <project> --feature <feature> --pin <pin> --function <function>`
7. `firmware-patch --root <project> --feature <feature> --pin <pin> --function <function>` to preview, then rerun with `--write --confirm-write` only after reviewing generated app files.
8. `firmware-integrate --root <project> --feature <feature> --pin <pin> --function <function> --write --confirm-write`
9. `bench-runbook --action build-flash` or `bench-runbook --action build-debug` with full safety fields for a no-hardware pre-bench manual.
10. `execute-action --backend fake` or simulator backends for integration rehearsal.
11. `safety-audit --root <project>` to review token consumption and execution-result evidence. Real flash/debug/observe remains planned-gated until backend-specific confirmation and bench evidence are implemented.
