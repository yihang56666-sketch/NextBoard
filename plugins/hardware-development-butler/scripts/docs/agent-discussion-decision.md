# Agent Discussion Decision

## Participants

- Product architecture review
- CubeMX / firmware loop review
- Hardware dossier and knowledge-base review
- Delivery risk review

## Consensus

The optimal path is not to merge `nextboard/` and `embeddedskills/` into one large skill, and not to start with risky real-hardware flash/debug automation.

The optimal path is:

```text
STM32 / CubeMX project inspection
  -> project dossier
  -> CubeMX IOC summary
  -> build backend discovery
  -> build log classification
  -> issue/debug logbook
```

This proves the butler can understand a project, create stable evidence, route to the right backend, and explain failures before it touches hardware state.

## Selected MVP

Phase 1 landing target:

1. Read-only scan of a hardware firmware project directory.
2. Detect `.ioc`, Keil, CMake/GCC, EIDE, Makefile, startup files, linker scripts, schematics, manuals, BOMs, datasheets, and logs.
3. Parse CubeMX `.ioc` for MCU, package, project name, toolchain, pins, peripherals, clocks, and middleware.
4. Classify build logs into issue categories.
5. Generate Markdown and JSON dossier files.
6. Keep flash/debug actions behind explicit user confirmation in later phases.

## Rejected Alternatives

### Merge Everything Into One Large Skill

Rejected because it would blur ownership, make upstream updates hard, and turn the system into a prompt-and-script monolith.

### Start With Fully Automated Flash/Debug

Rejected because real hardware actions need strong gates and the product value can be proven first through read-only inspection and build diagnostics.

### Promise All Hardware Platforms Immediately

Rejected because the first valuable loop should be narrow and verifiable. STM32 + CubeMX is the best initial path because it has structured `.ioc` metadata and common Keil/GCC outputs.

## First Implementation Slice

Implemented scripts:

- `tools/project_scanner.py`
- `tools/cube_detect.py`
- `tools/cubemx_ioc_summary.py`
- `tools/build_log_classifier.py`
- `tools/debug_logbook.py`
- `tools/hardware_butler_inspect.py`

## Embedded Toolchain Agent Feedback

The embedded execution agent agreed with the read-only MVP and added a concrete sequencing rule:

1. Detect CubeMX `.ioc` and cross-check build backends.
2. Prefer Keil when `.uvprojx/.uvmpw` and MDK target metadata exist.
3. Prefer CMake/GCC when CMake entries exist.
4. If multiple supported backends exist with similar confidence, ask instead of guessing.
5. Keep flash, erase, write-memory, CAN send, and network scan behind explicit user confirmation.

This feedback is reflected in `tools/cube_detect.py`, which ranks backend candidates before any build/flash action.

## Adversarial Iteration 1

Real sub-agent adversarial review was attempted again, but the platform returned `429 Too Many Requests` / thread-limit errors. The local fallback red-team review identified three concrete weaknesses and fixed them in this iteration:

1. `project_scanner.py` treated all PDFs as schematic/manual/datasheet candidates. It now classifies PDFs by filename evidence.
2. `build_log_classifier.py` treated linker summary failures as generic syntax/type errors. It now emits `linker_failed` for linker summary lines.
3. There was no safe bridge from detection to embeddedskills execution. `tools/build_plan.py` now emits reviewable commands and explicit safety gates instead of running build/flash/debug directly.

Next slice:

- Add backend correlation against embeddedskills Keil/GCC/EIDE scanners.
- Add a safe build-plan runner that recommends commands before executing them.
- Add fixtures for a minimal CubeMX-like project and build logs.

## Adversarial Iteration 2 Decision

The next optimal slice is a safe build-plan generator, not an executor. Even build commands can write outputs and can be wrong when multiple projects, targets, presets, or configurations exist.

Implemented:

- `tools/build_plan.py`

Safety decisions:

- The tool emits commands only; it never executes them.
- It excludes flash/debug commands.
- It requires explicit target/preset/config selection before build.
- It maps only supported MVP backends: Keil, CMake/GCC, and EIDE.
