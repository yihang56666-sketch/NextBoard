# Manual Summary Template

Use this structure for `docs/chip/<part>/manual-summary.md`.

## Identity

- Part number:
- Vendor:
- Package:
- Board, if any:
- Document set used:
- Unverified assumptions:

## Quick Start

- Minimum power rails and voltage range:
- Required decoupling or analog supply notes:
- Clock choices: internal, external crystal, bypass, PLL limits:
- Reset and boot mode:
- Debug/programming interface:
- First safe firmware test:

## Pin And Package Notes

- Pin count/package-specific differences:
- Reserved or special-function pins:
- Boot/debug pins that should not be repurposed early:
- Pins with voltage-domain or analog restrictions:
- High-current, open-drain, 5 V tolerant, or non-5 V tolerant notes:

## Memory And Startup

- Flash:
- SRAM:
- EEPROM/backup/NVRAM:
- Vector table/startup requirements:
- Option bytes/fuses/security bits:

## Clock Tree

- Internal oscillator options:
- External oscillator requirements:
- PLL constraints:
- Peripheral clock dependencies:
- Low-power clock notes:

## Peripherals

For each relevant peripheral:

| Peripheral | Pins | Clock/DMA/IRQ | CubeMX/HAL notes | Risks |
| --- | --- | --- | --- | --- |

## Electrical Limits

- Absolute maximum ratings:
- Recommended operating conditions:
- GPIO source/sink limits:
- ADC input limits:
- External bus voltage/pull-up constraints:
- Thermal/package limits:

## Errata And Workarounds

| Issue | Affected revision | Impact | Workaround | Source |
| --- | --- | --- | --- | --- |

## First Bring-Up Checklist

- Verify board power rails with current limit.
- Confirm chip marking/package matches the selected part.
- Confirm SWD/JTAG/bootloader access before repurposing debug pins.
- Build a minimal blink or serial log image.
- Flash only after user confirms target, voltage, debugger, and erase scope.
- Record result in `docs/chip/<part>/bringup-log.md`.
