# CubeMX Pin Configuration Guide

Use this guide when the user asks how to configure a pin or peripheral in STM32CubeMX or a similar visual configurator.

## Answer Structure

For each requested function, provide:

1. Exact target: chip, package, board, pin, signal, voltage domain.
2. CubeMX location: pinout view, peripheral page, clock page, NVIC, DMA, GPIO, middleware.
3. Required settings: mode, alternate function, pull-up/down, speed, output type, initial level, DMA, interrupt, timer, clock.
4. Why those settings: electrical reason, protocol reason, HAL/LL reason, FreeRTOS reason if relevant.
5. Alternatives: other pins, other peripheral instances, polling vs interrupt vs DMA, push-pull vs open-drain.
6. Risks: pin conflict, boot/debug conflict, board schematic conflict, level mismatch, missing pull-up, load current, signal integrity.
7. Generated code impact: expected `MX_*_Init` function, HAL handle, callback, user-code insertion points.

## Common Configuration Rules

### GPIO Output

- Use push-pull for directly driving logic inputs or LEDs through proper resistors.
- Use open-drain when multiple devices share a line or when level shifting through pull-ups is required.
- Set a safe initial level before enabling external loads.
- Do not drive pins connected to another active output unless the schematic proves it is safe.

### I2C

- Use open-drain with external or board-provided pull-ups.
- Verify pull-up voltage is safe for every device on the bus.
- Enable timing based on the actual peripheral clock, not only the desired bus speed.
- Prefer interrupt or DMA only when transactions are long or latency matters; simple bring-up can start with blocking calls.

### SPI

- Match CPOL/CPHA and bit order to the slave datasheet.
- Make chip-select a GPIO unless the hardware NSS mode is clearly required.
- Use DMA for continuous sampling, display refresh, or high-throughput transfers.
- Check voltage level and maximum SCK frequency against the slave and board wiring.

### UART

- Match baud, parity, stop bits, and flow control to the connected device.
- Prefer interrupt or DMA receive for command streams and logs.
- Keep one UART or RTT/SWO path available for diagnostics.

### ADC

- Confirm input voltage never exceeds the analog supply or documented limit.
- Configure sampling time based on source impedance.
- Use DMA for continuous multi-channel sampling.
- Account for reference voltage, calibration, and analog layout noise.

### PWM/Timers

- Derive period and duty cycle from the timer clock after prescaler.
- Use hardware PWM for stable waveforms instead of task-loop toggling.
- Confirm output polarity and safe startup duty before enabling a driver, motor, heater, LED array, or power stage.

### EXTI/Interrupts

- Choose edge trigger based on the external circuit and debounce needs.
- Keep ISR work short; notify a task when using FreeRTOS.
- Assign priorities compatible with RTOS interrupt priority rules.

### DMA

- Use DMA for high-rate ADC, SPI, UART, I2S, display, or sensor streams.
- Confirm buffer lifetime and cache coherency on MCUs with data cache.
- Use callbacks or task notifications for completion instead of busy waiting.

## Conflict Checks

Always check:

- Pin already used by board schematic.
- Pin reserved for SWD/JTAG, reset, boot, oscillator, USB, external memory, or power functions.
- Peripheral instance clock enabled.
- Alternate function matches the exact package pin.
- Middleware conflicts with the same timer/DMA/IRQ.
- CubeMX regenerated code will preserve changes only inside `USER CODE` sections.
