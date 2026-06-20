# Firmware And RTOS Implementation Guide

Use this guide after the user has a generated project or asks to implement a concrete function on a configured pin/peripheral.

## Implementation Boundaries

- Prefer `Core/Src/*`, `Core/Inc/*`, app-specific files, and CubeMX `USER CODE` sections.
- Do not edit generated HAL driver files unless the user explicitly approves and the change is documented.
- Keep pin/peripheral names consistent with CubeMX-generated handles and labels.
- Keep a minimal rollback path: one commit/diff, one feature flag, or one isolated module.

## Choosing The Execution Model

Use the simplest model that meets timing and safety needs:

| Need | Preferred mechanism |
| --- | --- |
| Low-rate setup or one-shot action | blocking HAL call in init or task |
| Periodic work above millisecond scale | FreeRTOS task with `vTaskDelayUntil` |
| Precise waveform or capture | hardware timer/PWM/input capture |
| High-rate receive/transmit | DMA + callback/task notification |
| External event | EXTI ISR + task notification/queue |
| Shared bus | mutex-protected driver API |
| Multi-step peripheral state machine | dedicated task + queue |
| Timeout/retry | timer or bounded wait with error reporting |

## FreeRTOS Rules

- Do not block inside ISRs.
- From ISR, use `xTaskNotifyFromISR`, `xQueueSendFromISR`, or equivalent ISR-safe APIs.
- Keep interrupt priority below the RTOS syscall ceiling when using RTOS APIs.
- Use one owner task per shared peripheral bus where practical.
- Use queues for commands/data, event groups for state flags, and mutexes for short critical shared resources.
- Avoid unbounded loops without delay, timeout, or watchdog servicing.

## Driver Shape

For each feature, produce:

- Header API with clear init/start/stop/read/write functions.
- Source module that owns HAL handles only by reference; do not duplicate generated handles.
- Error codes or status values for timeout, busy, invalid argument, hardware fault.
- Logging path through UART/RTT/SWO if available.
- Unit-testable pure helpers when protocol packing/parsing is involved.

## Verification Loop

1. Build without hardware action.
2. Review warnings and memory size.
3. Flash only after safety gates pass and user confirms exact target.
4. Observe logs or signals with serial/RTT/CAN/network/instrument evidence.
5. Record symptom, evidence, root cause, fix, verification, and remaining risk in docs.
6. Repeat with the smallest change that can disprove the current hypothesis.

## Safety-Aware Defaults

- For outputs controlling loads, initialize disabled and require explicit enable.
- For motors, heaters, relays, power switches, or high-current LEDs, add software interlocks and safe duty/current limits.
- For communications buses, start at conservative speed and increase only after stable evidence.
- For flash/erase/debug, never assume the attached target is correct; verify device identity first.
