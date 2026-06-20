# Hardware Agent Workspace

这是一个面向嵌入式硬件开发的工作区容器，不是单一固件工程。当前可用目标是：先安全地理解项目、收集芯片资料、分析 CubeMX 配置、生成 FreeRTOS/HAL 实现建议与安全补丁，再通过受控计划、预检、dry-run 和仿真路径推进 build/flash/debug/observe。

真实 `flash/debug/observe` 仍是 `planned-gated`：在完成具体后端的板级验证前，运行时不会把物理烧录、擦除、复位、在线调试或长时间观测当作已实现功能。

## Quick Start

把真实项目目录放在本工作区内，然后先跑安全 onboarding：

```powershell
python tools\hardware_butler.py onboard --root <project-root> --out-dir docs\inspections\<project-name> --json
```

`onboard` 只做安全动作：生成项目档案、识别 CubeMX/构建后端、生成 build plan、执行 allowlist 内的发现命令、生成配置提案。它不会 build、flash、erase、debug、发送总线报文、扫描网络，也不会写 `.embeddedskills/config.json`。

当前建议 `<project-root>` 放在本 workspace 内，这样 safe runner 可以强制执行可信路径边界。外部项目请先复制或挂载到本工作区，再执行工具链流程。

## Capability Status

| 能力 | 状态 | 说明 |
| --- | --- | --- |
| 项目 onboarding / inspect / detect / plan-build / run-plan | available | 只执行安全发现与报告生成。 |
| 芯片资料包 `chip-dossier` | available-limited | 支持官方/用户提供来源、内置厂商 hints、PDF 校验、下载、覆盖率记录和摘要生成；JS 门户、登录页和任意厂商深度搜索仍需人工来源或后续增强。 |
| 手册摘要 `summarize-manual` | available-limited | 基于 PDF 或已提取文本做证据行摘要，缺失项保持 unknown；不是完整替代 datasheet/reference manual 阅读。 |
| CubeMX pin advice / `.ioc` patch | available-limited | 基于项目 `.ioc` 和可选 `pin-capabilities.json` 封装引脚证据给出配置、原因、替代和风险；`.ioc` 写入默认 dry-run，只有 `--write --confirm-write` 才写备份和变更。 |
| FreeRTOS/HAL firmware plan / patch / integrate | available-limited | 生成 app 层模块和 CubeMX `USER CODE` 集成；写入需要显式确认，并限制在 app 文件或 user-code 区域。 |
| plan-action / bench-runbook / bench-preflight / workflow dry-run | available-limited | 生成确认 token、artifact hash、预检和 workflow dry-run 证据；不消费真实硬件 token，不写安全日志/状态/配置。 |
| simulator backends / safety-audit | available-limited | 用仿真后端验证 token/audit 链路；`safety-audit` 只读并隐藏原始 token。 |
| real flash/debug/observe | planned-gated | real flash/debug/observe remains planned-gated until backend-specific bench validation proves device identity, voltage/current evidence, artifact hash binding, rollback logging, and bounded observation. |

查看机器可读能力矩阵：

```powershell
python tools\hardware_butler.py capabilities --json
```

## Main Workflow

1. 建立项目档案：

```powershell
python tools\hardware_butler.py onboard --root <project-root> --out-dir docs\inspections\<project-name> --json
```

2. 建立芯片资料包：

```powershell
python tools\hardware_butler.py chip-dossier --part STM32F407VGTx --source <official-pdf-url> --download --json
python tools\hardware_butler.py summarize-manual --part STM32F407VGTx --document docs\chip\STM32F407VGTx\documents\<manual>.pdf
```

3. 分析 CubeMX 引脚/外设：

```powershell
python tools\hardware_butler.py advise-pin --root <project-root> --pin PB7 --function i2c --json
python tools\hardware_butler.py advise-pin --root <project-root> --pin PB7 --function i2c --pin-evidence <pin-capabilities.json> --json
python tools\hardware_butler.py patch-ioc --root <project-root> --function i2c --instance I2C1 --scl PB6 --sda PB7 --json
```

4. 生成 FreeRTOS/HAL 实现计划和安全补丁：

```powershell
python tools\hardware_butler.py firmware-plan --root <project-root> --feature i2c-sensor-read --pin PB7 --function i2c --json
python tools\hardware_butler.py firmware-patch --root <project-root> --feature i2c-sensor-read --pin PB7 --function i2c --json
python tools\hardware_butler.py firmware-integrate --root <project-root> --feature i2c-sensor-read --pin PB7 --function i2c --json
```

5. 生成硬件动作计划和无硬件 runbook：

```powershell
python tools\hardware_butler.py bench-runbook --root <project-root> --action build-flash --target STM32F407VGTx --probe "ST-Link SN123" --voltage 3.3V --current-limit 100mA --erase-scope "firmware image only" --recovery "SWD under reset" --backend openocd --json
python tools\hardware_butler.py safety-audit --root <project-root> --json
```

## Product Checks

```powershell
python tools\hardware_butler.py doctor --root <project-root> --json
python tools\hardware_butler.py status --root <project-root> --json
python tests\validate_hardware_butler.py
```

## Packaged Codex Plugin

插件目录：

```text
plugins/hardware-development-butler/
```

重新同步和校验插件：

```powershell
python tools\package_hardware_butler_plugin.py
python plugins\hardware-development-butler\scripts\validate_package.py
python plugins\hardware-development-butler\scripts\tests\validate_hardware_butler.py
```

插件运行时包含 `tools/`、`embeddedskills/`、`nextboard/`、agent roles、docs 和 tests。直接入口示例：

```powershell
python plugins\hardware-development-butler\skills\hardware-development-butler\scripts\run_hardware_butler.py doctor --root <project-root> --json
python plugins\hardware-development-butler\skills\hardware-development-butler\scripts\run_hardware_butler.py onboard --root <project-root> --out-dir docs\inspections\<project-name> --json
```

## Workspace Layout

| 目录 | 定位 |
| --- | --- |
| `.agents/skills/chip-bringup/` | 芯片资料、手册摘要、CubeMX 配置、FreeRTOS 实现和硬件安全 bring-up 流程。 |
| `nextboard/` | 硬件方案、器件选型、BOM 风险、PCB/原理图约束、评审和报告。 |
| `embeddedskills/` | Keil/GCC/EIDE 构建，J-Link/OpenOCD/probe-rs，串口、CAN、网络和 workflow。 |
| `tools/hardware_butler.py` | 统一 CLI 入口。 |

`embeddedskills/` 当前保留独立 `.git`，不要无意删除；若要纳入父仓库版本管理，应先决定使用 submodule 还是普通目录。
