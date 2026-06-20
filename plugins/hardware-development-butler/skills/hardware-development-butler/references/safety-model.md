# Safety Model

The packaged runtime is safe by default.

Read-only commands:

- `capabilities`
- `doctor`
- `detect`
- `plan-build`
- `status`
- `classify-log`

Report-writing commands:

- `inspect`
- `onboard`

Config-writing command:

- `propose-config --write --confirm-write`

The safe runner blocks:

- build execution
- flash and erase
- debug halt, reset, resume, step, and memory/register writes
- CAN transmit
- network scan
- commands with placeholders
- commands declaring writes unless writes are explicitly enabled
- Python commands outside the trusted interpreter
- scripts outside the hard allowlist

Before any hardware-changing action, require explicit confirmation of:

- target board/device
- probe or interface
- exact action
- firmware or memory region when relevant
- expected risk and rollback

If the user asks for automatic build/flash/debug, first produce or verify `.embeddedskills/config.json`, then use the relevant embeddedskills skill for the confirmed backend.
