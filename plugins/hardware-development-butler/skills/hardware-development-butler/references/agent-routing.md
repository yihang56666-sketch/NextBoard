# Agent Routing

Use the butler as the top-level coordinator. It owns task decomposition, safety gates, report continuity, and final status.

Use `nextboard` for:

- schematic, PCB, BOM, datasheet, manual, and power-tree interpretation
- MCU/SoC, clock, reset, boot mode, debug interface, bus, sensor, actuator, and communication-module reasoning
- hardware risk review and validation planning
- writing board-profile and design-decision records

Use `embeddedskills` for:

- Keil MDK, CMake/GCC, EIDE, Makefile, and CubeMX generated-code tooling
- J-Link, OpenOCD, probe-rs, ST-Link, CMSIS-DAP, DAPLink, RTT, SWO, semihosting
- UART, serial logs, CAN/DBC, network capture, pcap, and interface checks
- build/flash/debug/observe workflow execution after explicit confirmation

Cross-stage loop:

1. Butler collects evidence and writes initial reports.
2. Nextboard checks board assumptions and hardware risks.
3. Embeddedskills validates build/debug/observe paths.
4. Butler writes root cause, fix, verification command, result, and remaining risk.
