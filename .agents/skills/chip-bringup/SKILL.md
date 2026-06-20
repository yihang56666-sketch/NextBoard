---
name: chip-bringup
description: Chip datasheet, reference manual, schematic, CubeMX, pin/peripheral configuration, FreeRTOS firmware, and safe hardware bring-up workflow. Use when the user wants to develop with a specific MCU/SoC/chip or board; find and download chip manuals, datasheets, errata, app notes, reference schematics, or development-board documents; summarize manuals for quick start; explain how to configure GPIO/I2C/SPI/UART/CAN/ADC/PWM/timers/clocks/interrupts/DMA in STM32CubeMX or similar tools; implement a requested pin or peripheral function in generated firmware; or plan/build/flash/debug a board while avoiding electrical damage.
---

# Chip Bring-Up

Use this skill as the bridge between hardware evidence and firmware execution. It sits between:

- `nextboard`: chip evidence, schematic reasoning, power/clock/reset/boot/debug safety.
- `embeddedskills`: build, flash, debug, serial/CAN/network observe tooling.
- `hardware-development-butler`: project dossier, CubeMX `.ioc`, build plan, config proposal, log classification.

## Operating Sequence

1. Establish the target: exact chip or board model, package if known, board power source, debugger/programmer, firmware project root, and requested function.
2. Collect evidence before advising pinouts or electrical limits. Read `references/source-and-download-policy.md` when documents must be searched or downloaded. Prefer the CLI:
   - `python tools\hardware_butler.py chip-dossier --part <part> --source <url> --download --json`
3. Build a chip dossier in the project docs:
   - `docs/chip/<part>/source-map.md`
   - `docs/chip/<part>/manual-summary.md`
   - `docs/chip/<part>/cubemx-config.md`
   - `docs/chip/<part>/safety-checklist.md`
   - downloaded PDFs under `docs/chip/<part>/documents/`
4. Summarize manuals with `references/manual-summary-template.md`. Mark every unknown or unverified claim as unknown; do not fill with memory.
   - For extracted text, use `python tools\hardware_butler.py summarize-manual --part <part> --document <manual-text>`.
5. For CubeMX or visual configuration requests, read `references/cubemx-pin-config-guide.md` and use `python tools\hardware_butler.py advise-pin --root <project> --pin <pin> --function <function>` before answering with exact settings, alternatives, conflicts, and reasons.
6. For implementation requests after generated code exists, read `references/firmware-rtos-implementation.md` and use `python tools\hardware_butler.py firmware-plan --root <project> --feature <name> --pin <pin> --function <function>`. Keep changes inside user-code areas or explicit app files.
7. Before build/flash/debug/observe or any hardware-changing action, read `references/hardware-safety-gates.md` and use `python tools\hardware_butler.py plan-action --root <project> --action <action> ...`. Require explicit confirmation for the exact device, action, voltage/power conditions, and rollback path.

## Output Rules

- Cite the source for chip parameters: datasheet, reference manual, errata, application note, schematic, board manual, CubeMX `.ioc`, or measured log.
- Separate `confirmed`, `inferred`, and `needs verification`.
- Explain "why this configuration" and "what else can be configured" for each pin/peripheral.
- Include damage-risk notes for output pins, alternate functions, voltage domains, current limits, open-drain buses, pull-ups, external loads, boot pins, and debug pins.
- Never claim that a chip, package, pin mux, voltage limit, flash algorithm, or boot mode is correct unless verified from documents or local project evidence.

## Routing

- Need architecture, part choice, schematic, BOM, power tree, PCB, or datasheet source quality: use `nextboard/skills/hardware-solution`.
- Need Keil/GCC/EIDE build, J-Link/OpenOCD/probe-rs flash/debug, serial/CAN/network observe: use the corresponding `embeddedskills` skill.
- Need first-pass project evidence: use `plugins/hardware-development-butler/skills/hardware-development-butler` or `tools/hardware_butler.py onboard`.
- Need a single chip from zero to working firmware: stay in this skill and call the other roles only at their boundaries.
