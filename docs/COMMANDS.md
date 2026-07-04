# Hardware Butler Commands

这是一份按工作流分组的命令速查。命令默认以 PowerShell 形式展示，`<project-root>` 替换为你的真实项目目录。

## 第一轮入口

没有真实工程时，可先把 `<project-root>` 替换成 `tests\fixtures\cubemx-basic` 跑一个无硬件示例。

| 目标 | 命令 | 安全性 |
| --- | --- | --- |
| 打印启动指南 | `python tools\hardware_butler.py guide --root <project-root>` | 只读 |
| 检查环境和项目状态 | `python tools\hardware_butler.py doctor --root <project-root> --json` | 只读 |
| 自动安全入驻 | `python tools\hardware_butler.py auto --root <project-root> --out-dir docs\inspections\<project-name> --json` | 写报告和状态，不碰硬件 |
| 查看下一步 | `python tools\hardware_butler.py next-step --root <project-root> --json` | 只读分析加状态写入 |
| 打开 GUI | `python gui\hardware_agent_ui.py` | GUI 只暴露安全动作 |

## 理解项目

| 目标 | 命令 | 输出 |
| --- | --- | --- |
| 生成项目档案 | `python tools\hardware_butler.py inspect --root <project-root> --out-dir docs\inspections\<project-name> --json` | 项目、板卡、固件报告 |
| 检测 CubeMX 和构建后端 | `python tools\hardware_butler.py detect --root <project-root> --json` | 后端候选、CubeMX 元数据 |
| 查看项目状态 | `python tools\hardware_butler.py status --root <project-root> --json` | 配置、报告、发现、台架状态 |
| 构建项目大脑 | `python tools\hardware_butler.py brain --root <project-root> --json` | 证据健康度和硬件风险 |
| 基于本地证据提问 | `python tools\hardware_butler.py ask --root <project-root> --question "PD12 接了什么" --json` | 只基于本地证据回答 |

## 芯片资料和证据

| 目标 | 命令 | 说明 |
| --- | --- | --- |
| 创建芯片资料包 | `python tools\hardware_butler.py chip-dossier --part STM32F407VGTx --json` | 建立资料目录和摘要骨架 |
| 用搜索 API 收集资料 | `python tools\hardware_butler.py chip-dossier --part STM32F407VGTx --api-search --download --json` | 需要配置搜索 API，否则回退到内置 hints |
| 使用官方 PDF | `python tools\hardware_butler.py chip-dossier --part STM32F407VGTx --source <official-pdf-url> --download --json` | 推荐优先使用官方资料 |
| 摘要手册 | `python tools\hardware_butler.py summarize-manual --part STM32F407VGTx --document <manual.pdf> --json` | 缺失证据保持 unknown |

硬件理解的完整闭环见 [HARDWARE_UNDERSTANDING.md](HARDWARE_UNDERSTANDING.md)：先证据，再配置，再固件，再台架。

## CubeMX 和固件规划

| 目标 | 命令 | 安全性 |
| --- | --- | --- |
| 引脚建议 | `python tools\hardware_butler.py advise-pin --root <project-root> --pin PB7 --function i2c --json` | 只读 |
| 带封装证据的引脚建议 | `python tools\hardware_butler.py advise-pin --root <project-root> --pin PB7 --function i2c --pin-evidence <pin-capabilities.json> --json` | 只读 |
| 预览 `.ioc` 修改 | `python tools\hardware_butler.py patch-ioc --root <project-root> --function i2c --instance I2C1 --scl PB6 --sda PB7 --json` | dry-run |
| 写入 `.ioc` 修改 | `python tools\hardware_butler.py patch-ioc --root <project-root> --function i2c --instance I2C1 --scl PB6 --sda PB7 --write --confirm-write --json` | 只在确认后写入并备份 |
| 固件实现计划 | `python tools\hardware_butler.py firmware-plan --root <project-root> --feature i2c-sensor-read --pin PB7 --function i2c --json` | 只读 |
| 预览固件补丁 | `python tools\hardware_butler.py firmware-patch --root <project-root> --feature i2c-sensor-read --pin PB7 --function i2c --json` | dry-run |
| 写入固件补丁 | `python tools\hardware_butler.py firmware-patch --root <project-root> --feature i2c-sensor-read --pin PB7 --function i2c --write --confirm-write --json` | 限制在 app 文件和 USER CODE 流程 |
| 集成 app 模块 | `python tools\hardware_butler.py firmware-integrate --root <project-root> --feature i2c-sensor-read --json` | 默认 dry-run |

## 构建和配置

| 目标 | 命令 | 说明 |
| --- | --- | --- |
| 生成构建计划 | `python tools\hardware_butler.py plan-build --root <project-root> --json` | 不执行构建 |
| 运行安全发现阶段 | `python tools\hardware_butler.py run-plan --root <project-root> --phase build-discovery --json` | 只跑 allowlist 命令 |
| 生成配置提案 | `python tools\hardware_butler.py propose-config --root <project-root> --json` | 不写配置 |
| 写入配置 | `python tools\hardware_butler.py propose-config --root <project-root> --target <target> --write --confirm-write --json` | 明确确认后写 `.embeddedskills/config.json` |
| 分类构建日志 | `python tools\hardware_butler.py classify-log <build-log.txt> --json` | 只读 |

## 台架和硬件动作

| 目标 | 命令 | 说明 |
| --- | --- | --- |
| 生成无硬件 runbook | `python tools\hardware_butler.py bench-runbook --root <project-root> --action build-flash --json` | 不消费 token，不碰硬件 |
| 生成动作计划 | `python tools\hardware_butler.py plan-action --root <project-root> --action build-flash --target <mcu> --json` | 计划和 token 包 |
| 执行 fake 后端 | `python tools\hardware_butler.py execute-action --plan action.json --confirm-token <token> --backend fake --json` | 仿真执行 |
| 台架预检 | `python tools\hardware_butler.py execute-action --plan action.json --confirm-token <token> --backend bench-preflight --json` | 校验命令包和证据 |
| 安全审计 | `python tools\hardware_butler.py safety-audit --root <project-root> --json` | 只读，隐藏原始 token |

真实 flash/debug/observe 仍是 planned-gated，不要绕过确认流程。

## 意图工作流

| 意图 | 命令 |
| --- | --- |
| 准备 bring-up | `python tools\hardware_butler.py task --root <project-root> --intent prepare-bringup --json` |
| 收集证据 | `python tools\hardware_butler.py task --root <project-root> --intent collect-evidence --part STM32F407VGTx --json` |
| 配置外设 | `python tools\hardware_butler.py task --root <project-root> --intent configure-peripheral --function i2c --instance I2C1 --json` |
| 排查构建 | `python tools\hardware_butler.py task --root <project-root> --intent fix-build --log <build-log.txt> --json` |

## 产品和开发验证

| 目标 | 命令 |
| --- | --- |
| 能力矩阵 | `python tools\hardware_butler.py capabilities --json` |
| 快速发布预检 | `python tools\release_verify.py --profile quick` |
| 完整发布预检 | `python tools\release_verify.py` |
| 单元测试 | `pytest tests/unit/ -v` |
| 集成校验 | `python tests\validate_hardware_butler.py` |
| 插件同步检查 | `pytest tests\unit\test_plugin_sync.py -q --no-cov` |
| 打包插件 | `python tools\package_hardware_butler_plugin.py` |
