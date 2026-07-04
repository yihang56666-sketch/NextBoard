# Beginner Guide

这页给第一次接触 Hardware Butler 的用户看。目标不是让你一次学完所有硬件开发流程，而是用最少命令确认三件事：项目能被识别、下一步是安全的、什么时候才需要真实硬件证据。

## 这个工具做什么

Hardware Butler 是一个安全优先的嵌入式硬件开发工作台。它会先读取本地工程证据，生成报告和计划，再把构建、烧录、调试、串口、CAN、网络等动作交给受控后端。

它适合这些场景：

- 接手一个 STM32/CubeMX/Keil/CMake 工程，想先弄清楚项目结构。
- 想知道 MCU、封装、引脚、构建后端和固件入口的证据在哪里。
- 想生成不碰硬件的台架 runbook 或硬件动作计划。
- 想把真实 flash/debug/observe 保持在确认 token 和安全审计之后。

它不会在第一天流程里自动烧录、擦除、复位、调试、发串口/CAN 报文或扫描网络。

## 5 分钟体验

先安装本地工作区：

```powershell
python -m pip install -e .
```

没有真实板卡工程时，用内置 fixture 体验完整安全路径：

```powershell
python tools\hardware_butler.py guide --root tests\fixtures\cubemx-basic
python tools\hardware_butler.py doctor --root tests\fixtures\cubemx-basic --json
python tools\hardware_butler.py brain --root tests\fixtures\cubemx-basic --json
python tools\hardware_butler.py auto --root tests\fixtures\cubemx-basic --out-dir docs\inspections\cubemx-basic --json
python tools\hardware_butler.py next-step --root tests\fixtures\cubemx-basic --json
```

这个 fixture 是一个最小 CubeMX/Keil 示例。`doctor` 可能报告 Keil、J-Link、OpenOCD、probe-rs 或构建产物缺失，这些是可选台架工具 warning，不代表入门体验失败。

## 分析你自己的项目

把 `<project-root>` 换成真实项目路径：

```powershell
python tools\hardware_butler.py guide --root <project-root>
python tools\hardware_butler.py doctor --root <project-root> --json
python tools\hardware_butler.py auto --root <project-root> --out-dir docs\inspections\<project-name> --json
python tools\hardware_butler.py next-step --root <project-root> --json
```

第一天跑到 `next-step` 能给出一条安全建议就够了。此时你应该知道：

- 项目是否被识别为 Keil/GCC/EIDE/CubeMX 等后端。
- 生成的报告在哪里。
- 下一步是否会触碰真实硬件。
- 如果要触碰硬件，还缺哪些证据和确认。

## 你会看到哪些输出

`auto` 会把报告写到你传入的 `--out-dir`：

| 输出 | 用途 |
| --- | --- |
| `onboarding-manifest.json` | 入驻结果摘要。 |
| `project-dossier.md` | 项目结构和关键文件。 |
| `board-profile.md` | MCU、板卡和外设线索。 |
| `firmware-profile.md` | 固件入口、源码布局和生成代码边界。 |
| `build-plan.md` | 安全构建发现计划。 |
| `config-proposal.md` | `.embeddedskills/config.json` 提案。 |

工具还会在项目内写入 `.hardware-butler\project-state.json`，用于记录当前工作流状态和下一步推荐。

## 想用 GUI

安装 GUI 依赖：

```powershell
python -m pip install -e ".[ui]"
```

启动：

```powershell
python gui\hardware_agent_ui.py
```

GUI 适合先选项目、刷新状态、查看报告和点击推荐安全动作。真实硬件动作仍然必须走计划、确认 token 和审计流程。

## 想深入理解硬件

按这条证据链推进：

```powershell
python tools\hardware_butler.py brain --root <project-root> --json
python tools\hardware_butler.py ask --root <project-root> --question "MCU 型号和封装证据在哪里" --json
python tools\hardware_butler.py chip-dossier --part STM32F407VGTx --json
python tools\hardware_butler.py advise-pin --root <project-root> --pin PB7 --function i2c --json
python tools\hardware_butler.py firmware-plan --root <project-root> --feature i2c-sensor-read --json
python tools\hardware_butler.py bench-runbook --root <project-root> --action build-flash --json
```

硬件结论应该能标成 `confirmed`、`inferred` 或 `needs verification`。没有 datasheet、原理图、CubeMX、源码、构建日志或台架记录支撑时，不要把猜测写成事实。

## 真实硬件前的底线

执行真实 flash/debug/observe 之前，至少确认：

- MCU 型号、封装和板卡身份。
- 电源电压、电流限制、外部负载和电平转换。
- 探针型号、连接方向、SWD/JTAG/串口接口占用。
- 固件产物路径、hash、擦除范围和回滚固件。
- `bench-runbook` 和 `plan-action` 输出已经审核。
- 确认 token 没有被绕过，审计日志可追踪。

生成动作计划的示例：

```powershell
python tools\hardware_butler.py plan-action --root <project-root> --action flash --target <mcu> --artifact <firmware> --json
```

## 下一步阅读

- [START_HERE.md](START_HERE.md) - 第一天推荐路径。
- [ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md) - 一页理解架构和安全网络。
- [HARDWARE_UNDERSTANDING.md](HARDWARE_UNDERSTANDING.md) - 从资料、CubeMX、固件到台架的硬件理解闭环。
- [COMMANDS.md](COMMANDS.md) - 按任务查命令。
