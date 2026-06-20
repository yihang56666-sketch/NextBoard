# Hardware Safety Gates

Use this before any action that can change hardware state, including flashing, erasing, reset/halt/resume, memory writes, bus transmission, power-stage enable, GPIO output enable, or high-current peripheral control.

## Required Confirmation

Ask for or verify:

- Exact board/chip connected.
- Programmer/debugger type and serial number when multiple probes may exist.
- Target voltage and who powers the board.
- Bench supply current limit or USB/source current limit.
- Flash/erase scope: full chip, selected bank, sector, or firmware image only.
- Recovery path: bootloader, SWD under reset, known-good firmware, or backup image.
- Whether external loads are connected: motors, heaters, relays, batteries, high-power LEDs, actuators, sensors with fragile inputs.

## Electrical Damage Checklist

Do not proceed until these are known or intentionally accepted:

- GPIO voltage level is compatible with the connected circuit.
- Output pin is not shorted against another output.
- Current through GPIO is within datasheet limit and board resistor values are known.
- Open-drain bus pull-up voltage is safe for every device.
- Analog input stays within allowed input range.
- Power rails are in the required range and polarity.
- Clock source configuration matches the actual crystal/bypass/population.
- Boot and reset pins are not held in a state that prevents recovery.
- SWD/JTAG pins remain available until firmware is proven recoverable.
- Thermal/current risk is bounded for power switches, drivers, regulators, and loads.

## Action Classes

### Safe By Default

- Read files, parse `.ioc`, summarize manuals, generate reports.
- Run build commands that do not touch hardware.
- Classify logs.

### Confirmation Required

- Write `.embeddedskills/config.json`.
- Flash firmware.
- Erase flash.
- Reset/halt/resume/debug target.
- Read/write target memory.
- Send CAN/UART/SPI/I2C/network traffic to connected hardware.
- Enable GPIO outputs connected to external loads.

### Stop And Ask

Stop if any condition applies:

- Unknown chip/package or uncertain target identity.
- Unknown voltage domain.
- Unknown external load.
- Conflicting schematic and `.ioc`.
- User asks to disable readout protection, mass erase, change option bytes/fuses, or repurpose debug/boot pins.
- Firmware controls motors, heaters, battery charging, mains, high voltage, pyrotechnics, or safety-critical motion.

## Pre-Flash Minimum

Before the first flash:

1. Build succeeds.
2. Firmware image matches the target chip and flash size.
3. Debug probe can read target identity.
4. Target voltage is measured or reported by the probe.
5. User confirms flash scope and board identity.
6. A recovery method is available.

## Post-Action Log

Record each hardware-changing action in `docs/chip/<part>/bringup-log.md`:

- Timestamp.
- Command/action.
- Target identity.
- Power/current conditions.
- Result.
- Evidence/logs.
- Next risk or rollback note.
