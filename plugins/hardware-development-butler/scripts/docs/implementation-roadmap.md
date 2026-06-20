# Implementation Roadmap

## Product Position

当前工作区已经从半成品推进为安全 MVP，可用于真实项目的前半段和无硬件验证闭环：

- 项目 onboarding、CubeMX/后端识别、构建计划、allowlist 安全发现。
- 芯片资料包、PDF 校验下载、来源地图、文档覆盖率、证据行手册摘要。
- CubeMX 引脚/外设建议和受控 `.ioc` patch。
- FreeRTOS/HAL 实现计划、app 层模块生成、CubeMX `USER CODE` 集成。
- action plan、确认 token、artifact hash、bench-preflight、workflow dry-run、仿真后端和 safety-audit。
- Codex plugin 打包、源/包同步校验和插件内运行时验证。

真实 `flash/debug/observe` 仍然是 `planned-gated`，不是已完成物理自动化。real flash/debug/observe remains planned-gated until backend-specific bench validation proves device identity, voltage/current evidence, artifact hash binding, rollback logging, and bounded observation.

## Shipped Capability Matrix

| Area | Status | Current Evidence |
| --- | --- | --- |
| Workspace shape | shipped | `nextboard/`, `embeddedskills/`, `.agents/skills/chip-bringup/`, `tools/hardware_butler.py` |
| Safe onboarding | shipped | `onboard`, `inspect`, `detect`, `plan-build`, `run-plan`, `doctor`, `status` |
| Chip documents | shipped-limited | `chip-dossier`, `document_providers`, PDF validation, `document-coverage.*`, source map |
| Manual summary | shipped-limited | `summarize-manual`, PDF/text extraction, evidence rows, unknown handling |
| CubeMX advice | shipped-limited | `.ioc` semantic indexes, optional `pin-capabilities.json` package evidence, conflict/risk/advice output |
| CubeMX patch | shipped-limited | dry-run default, `--write --confirm-write`, backups, TOCTOU revalidation |
| FreeRTOS/HAL implementation | shipped-limited | `firmware-plan`, `firmware-patch`, `firmware-integrate`, app files and `USER CODE` only |
| Hardware action safety | shipped-limited | confirmation token, child token, artifact hash, safety gate, safety audit |
| Workflow pre-bench path | shipped-limited | `bench-runbook`, `bench-preflight`, actual `workflow_run.py --dry-run --json`, no token consumption |
| Simulator backends | shipped-limited | build-flash/build-debug/observe simulation and audit log |
| Plugin packaging | shipped | `plugins/hardware-development-butler/`, `package_hardware_butler_plugin.py`, `validate_package.py` |
| Real hardware flash/debug/observe | planned-gated | Requires backend-specific bench executor validation before enabling |

`shipped-limited` 表示工具可用，但输出必须继续区分 confirmed / inferred / needs verification，且不能把未验证的芯片参数、pin mux、电气极限或真实硬件动作当作已确认事实。

## Remaining Product Hardening

1. Manufacturer document search hardening
   - Add stronger ST/NXP/TI fixtures for official search pages, product pages, direct PDF links, redirects, JS/login rejection and document-type classification.
   - Keep arbitrary web portals as best-effort hints unless a validated PDF is downloaded.

2. Package-aware pin evidence hardening
   - Basic local `pin-capabilities.json` ingestion is shipped-limited.
   - Next step: add MCU/package pin database ingestion or vendor evidence adapters.
   - Continue labeling alternate functions as `verified`, `contradicted`, `inferred`, or `unknown`.
   - Keep `.ioc`-only advice scoped to project evidence.

3. Manual summary depth
   - Improve section extraction for power, clock tree, reset/boot, debug, memory, peripheral setup, electrical limits and errata.
   - Preserve line/page evidence and unknown handling.

4. External project roots
   - Current safe path assumes projects live inside this workspace.
   - Future release should support explicit trusted external roots or a documented import command.

5. Real hardware backend validation
   - Add backend-specific bench executors only after proving device identity, voltage/current evidence, artifact hash binding, rollback logging, bounded observation and safe failure behavior.
   - Until then, physical actions remain `planned-gated`.

## Validation Gates

Root runtime:

```powershell
python tests\validate_hardware_butler.py
```

Plugin packaging and packaged runtime:

```powershell
python tools\package_hardware_butler_plugin.py
python plugins\hardware-development-butler\scripts\tests\validate_hardware_butler.py
python plugins\hardware-development-butler\scripts\validate_package.py
```

Cleanup checks before release:

```powershell
Get-ChildItem -Path . -Recurse -Directory -Filter __pycache__
Test-Path tests\tmp
Test-Path docs\chip
Test-Path plugins\hardware-development-butler\scripts\tests\tmp
Test-Path plugins\hardware-development-butler\scripts\docs\chip
```
