# Hardware Butler Usage Guide

这份文档描述当前硬件开发管家的可用入口、默认安全边界和推荐闭环。当前版本是可落地的安全 MVP：它能完成资料、配置、代码补丁、计划、预检、dry-run、仿真和审计，但真实硬件动作仍需要后端级板上验证。

## 当前能做什么

- 扫描硬件/固件项目目录，生成项目档案、板级画像、固件画像、构建计划和配置提案。
- 解析 STM32 CubeMX `.ioc`，识别 MCU、封装、工具链、引脚、外设、时钟和中间件。
- 发现 Keil、CMake/GCC、EIDE 构建入口，并只运行 allowlist 内的安全发现命令。
- 创建芯片资料包，记录来源，下载并校验 PDF，拒绝 HTML、跳转页、登录页或伪 PDF。
- 对 PDF 或已提取手册文本生成带证据行的快速摘要，缺失项保持 `unknown`。
- 基于 `.ioc` 和可选 `pin-capabilities.json` 封装引脚证据给出 CubeMX 引脚/外设建议，包括配置项、原因、替代、代码影响和风险；证据状态会标记为 `verified`、`contradicted`、`inferred` 或 `unknown`。
- 预览或写入安全 `.ioc` patch；写入必须同时使用 `--write --confirm-write`，并先创建备份。
- 生成 FreeRTOS/HAL 实现计划、app 层模块和 CubeMX `USER CODE` 集成 patch。
- 生成 build/flash/debug/observe 的 action plan、bench runbook、preflight 和 workflow dry-run。
- 通过仿真后端验证 token、artifact hash 和 audit 链路，不触碰真实硬件。
- 生成 `safety-audit` 只读报告，显示 token hash、backend 计数、执行结果和 artifact hash 证据，不暴露原始 token。

## 安全边界

- 默认不执行 build、flash、erase、debug、CAN 发送、网络扫描或长时间观测。
- `run-plan` 只执行 metadata-safe 和 hard allowlist 内的发现/诊断命令。
- `.embeddedskills/config.json`、`.ioc`、固件 app 文件和 `USER CODE` 写入都需要显式确认参数。
- `bench-runbook` 只执行 `workflow_run.py --dry-run --json` 子进程，用来捕获真实 workflow 配置、状态和 artifact 错误；它不会执行硬件动作、消费 token、写 safety log、写 state 或写 config。
- `bench-preflight` 只验证命令包、token、artifact hash、backend scope 和工具可用性，不执行子进程，不消费 token。
- workflow `--dry-run` 只准备脱敏命令；非 dry-run `observe` 当前返回 `planned-gated`，不会消费 token 或打开观测通道。
- real flash/debug/observe remains planned-gated until backend-specific bench validation proves device identity, voltage/current evidence, artifact hash binding, rollback logging, and bounded observation.

## 推荐闭环

把 `<project-root>` 替换成你的 CubeMX/Keil/CMake/EIDE 工程目录。

```powershell
python tools\hardware_butler.py onboard --root <project-root> --out-dir docs\inspections\<project-name> --json
python tools\hardware_butler.py doctor --root <project-root> --json
python tools\hardware_butler.py status --root <project-root> --json
```

为芯片建立资料包：

```powershell
python tools\hardware_butler.py chip-dossier --part STM32F407VGTx --source <official-pdf-url> --download --json
python tools\hardware_butler.py summarize-manual --part STM32F407VGTx --document docs\chip\STM32F407VGTx\documents\<manual>.pdf
```

分析或预览 CubeMX 配置：

```powershell
python tools\hardware_butler.py advise-pin --root <project-root> --pin PD12 --function gpio-output --json
python tools\hardware_butler.py advise-pin --root <project-root> --pin PB7 --function i2c --json
python tools\hardware_butler.py advise-pin --root <project-root> --pin PB7 --function i2c --pin-evidence <pin-capabilities.json> --json
python tools\hardware_butler.py patch-ioc --root <project-root> --function i2c --instance I2C1 --scl PB6 --sda PB7 --json
```

生成固件实现计划和默认 dry-run patch：

```powershell
python tools\hardware_butler.py firmware-plan --root <project-root> --feature i2c-sensor-read --pin PB7 --function i2c --json
python tools\hardware_butler.py firmware-patch --root <project-root> --feature i2c-sensor-read --pin PB7 --function i2c --json
python tools\hardware_butler.py firmware-integrate --root <project-root> --feature i2c-sensor-read --pin PB7 --function i2c --json
```

确认要写入 app 文件或 `USER CODE` 后再加确认参数：

```powershell
python tools\hardware_butler.py firmware-patch --root <project-root> --feature i2c-sensor-read --pin PB7 --function i2c --write --confirm-write --json
python tools\hardware_butler.py firmware-integrate --root <project-root> --feature i2c-sensor-read --pin PB7 --function i2c --write --confirm-write --json
```

生成无硬件 bench runbook：

```powershell
python tools\hardware_butler.py bench-runbook --root <project-root> --action build-flash --target STM32F407VGTx --probe "ST-Link SN123" --voltage 3.3V --current-limit 100mA --erase-scope "firmware image only" --recovery "SWD under reset" --backend openocd --json
python tools\hardware_butler.py safety-audit --root <project-root> --json
```

## Product Checks

展示当前能力矩阵：

```powershell
python tools\hardware_butler.py capabilities --json
```

检查安装、脚本、agent 文件、可选工具、项目后端、配置和 safe runner 策略：

```powershell
python tools\hardware_butler.py doctor --root <project-root> --json
```

查看项目 onboarding 后的状态：

```powershell
python tools\hardware_butler.py status --root <project-root> --json
```

`doctor` 和 `status` 是只读命令。`status` 使用 `docs/inspections/<project-name>/onboarding-manifest.json` 判断安全发现是否真的跑过；如果 manifest 缺失、过期或存在错误，会返回 `needs-safe-discovery`。

## 内置验证

```powershell
python tests\validate_hardware_butler.py
python tools\package_hardware_butler_plugin.py
python plugins\hardware-development-butler\scripts\tests\validate_hardware_butler.py
python plugins\hardware-development-butler\scripts\validate_package.py
```

验证覆盖 CubeMX 检测、封装引脚证据状态、资料下载和 PDF 校验、手册摘要、`.ioc` patch 门控、FreeRTOS/HAL 计划、USER CODE 集成、action token、artifact hash、workflow dry-run、安全审计、插件同步和包结构。

## 多智能体协作方式

- `hardware-development-butler`: 总管，负责拆分任务、控制风险、串联文档和工具链。
- `nextboard-hardware-architect`: 负责硬件方案、BOM、原理图/PCB 风险和验证计划。
- `embeddedskills-lab-operator`: 负责构建、烧录、调试、串口、CAN、网络和 workflow 工具链。

完整闭环：

```text
需求 -> nextboard 方案与约束
    -> chip-bringup 资料/手册/CubeMX/FreeRTOS/安全门控
    -> embeddedskills build/preflight/dry-run/sim/observe tooling
    -> nextboard 回写风险和设计决策
```
