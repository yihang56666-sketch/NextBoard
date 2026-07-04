# Hardware Understanding Workflow

这页回答一个更深入的问题：怎样用 Hardware Butler 把一块板子从“看起来能用”推进到“证据充分、风险清楚、可以安全使用”。

核心原则很简单：不要凭记忆猜硬件。芯片、封装、引脚复用、电压域、时钟、启动模式、调试接口、外设连接和烧录动作，都必须来自数据手册、参考手册、勘误、应用笔记、原理图、板卡手册、CubeMX `.ioc`、源码、构建日志或台架记录。没有证据的地方标成 `needs verification`，不要补成看似确定的结论。

## 证据地图

| 证据来源 | 典型文件或命令 | 能回答什么 |
| --- | --- | --- |
| 项目本地证据 | `doctor`, `auto`, `brain`, `ask` | 项目结构、CubeMX/构建后端、已有固件入口、板卡线索、证据缺口。 |
| 芯片资料 | `chip-dossier`, `summarize-manual` | 封装、供电范围、引脚能力、外设章节、时钟/复位/启动/调试限制。 |
| 配置证据 | `.ioc`, `advise-pin`, `patch-ioc` dry-run | 引脚占用、复用冲突、调试/时钟保护、可选外设实例。 |
| 固件证据 | `firmware-plan`, `firmware-patch` dry-run | HAL/FreeRTOS 入口、USER CODE 区、app 模块边界、需要写入的最小代码。 |
| 台架证据 | `bench-runbook`, `plan-action`, `safety-audit` | 电源/探针/产物 hash/擦除范围/回滚路径/确认 token 和执行记录。 |

## 从项目到板卡画像

第一步只做本地发现：

```powershell
python tools\hardware_butler.py doctor --root <project-root> --json
python tools\hardware_butler.py auto --root <project-root> --out-dir docs\inspections\<project-name> --json
python tools\hardware_butler.py brain --root <project-root> --json
```

没有真实工程时，可以先用 `tests\fixtures\cubemx-basic` 练习同一条路径：

```powershell
python tools\hardware_butler.py doctor --root tests\fixtures\cubemx-basic --json
python tools\hardware_butler.py brain --root tests\fixtures\cubemx-basic --json
python tools\hardware_butler.py ask --root tests\fixtures\cubemx-basic --question "这个项目识别出了什么 MCU 和封装" --json
```

fixture 只能证明工作流和证据分类，不代表任何真实板卡的电气连接。真实项目仍要用数据手册、原理图、`.ioc`、源码和台架记录重新确认。

然后用 `ask` 只基于本地证据提问：

```powershell
python tools\hardware_butler.py ask --root <project-root> --question "MCU 型号和封装证据在哪里" --json
python tools\hardware_butler.py ask --root <project-root> --question "PB6/PB7 当前被什么功能占用" --json
```

如果回答里出现 `unknown` 或 `needs verification`，这是正常结果。它表示工具没有把不可靠的硬件结论伪装成事实。

## 从芯片资料到可配置外设

先建立芯片资料包，优先使用官方资料：

```powershell
python tools\hardware_butler.py chip-dossier --part STM32F407VGTx --source <official-pdf-url> --download --json
python tools\hardware_butler.py summarize-manual --part STM32F407VGTx --document <manual.pdf> --json
```

如果暂时没有 URL，可以生成资料骨架或使用搜索 API：

```powershell
python tools\hardware_butler.py chip-dossier --part STM32F407VGTx --json
python tools\hardware_butler.py chip-dossier --part STM32F407VGTx --api-search --download --json
```

做引脚或外设决策前，先让工具检查 CubeMX 和本地证据：

```powershell
python tools\hardware_butler.py advise-pin --root <project-root> --pin PB7 --function i2c --json
```

只有当封装、引脚能力、已有占用、外设实例、上拉方式、电压域和外部负载都能解释清楚时，才进入 `.ioc` 或固件修改。

## 从配置到固件实现

先预览配置，不直接写：

```powershell
python tools\hardware_butler.py patch-ioc --root <project-root> --function i2c --instance I2C1 --scl PB6 --sda PB7 --json
```

再生成固件计划：

```powershell
python tools\hardware_butler.py firmware-plan --root <project-root> --feature i2c-sensor-read --pin PB7 --function i2c --json
```

固件补丁默认 dry-run，写入时限制在 app 文件或 USER CODE 区：

```powershell
python tools\hardware_butler.py firmware-patch --root <project-root> --feature i2c-sensor-read --pin PB7 --function i2c --json
python tools\hardware_butler.py firmware-patch --root <project-root> --feature i2c-sensor-read --pin PB7 --function i2c --write --confirm-write --json
```

## 从计划到安全使用

真实硬件动作前，先生成不碰硬件的台架 runbook：

```powershell
python tools\hardware_butler.py bench-runbook --root <project-root> --action build-flash --json
```

然后生成动作计划，检查目标、后端、产物 hash、擦除范围和回滚路径：

```powershell
python tools\hardware_butler.py plan-action --root <project-root> --action flash --target <mcu> --artifact <firmware> --json
```

真实 `flash/debug/observe` 仍然是 `planned-gated`。在没有完成板卡身份、电源限制、探针身份、产物路径、擦除范围和恢复路径确认前，不要绕过 token 或直接调用底层后端。

## “透彻理解”检查表

每次准备使用一块板子时，至少把下面内容分成 `confirmed`、`inferred`、`needs verification` 三类：

| 主题 | 必须能说明什么 |
| --- | --- |
| 芯片和封装 | 精确 part/package、资料来源、封装引脚是否与板卡一致。 |
| 电源和电压域 | 供电来源、允许电压、电流限制、外设电平、是否有 level shifter。 |
| 时钟/复位/启动 | HSE/LSE/PLL 线索、复位脚、BOOT 脚、启动介质和调试保持方式。 |
| 调试接口 | SWD/JTAG/串口下载接口、探针型号、连接方向、是否占用功能脚。 |
| 外设连接 | I2C/SPI/UART/CAN/ADC/PWM 等外设接到哪里，是否需要上拉、终端、电平转换或限流。 |
| 固件入口 | HAL init、FreeRTOS task、USER CODE 区、app 模块、错误处理路径。 |
| 构建和产物 | Keil/GCC/EIDE/CMake 后端、目标配置、输出 ELF/HEX/BIN、产物 hash。 |
| 台架安全 | 电源限制、擦除范围、回滚固件、dry-run 输出、审计日志。 |

## 易损风险

这些项没有证据时，不要执行真实硬件动作：

- 输出脚是否会短接外部驱动或高电流负载。
- I2C/CAN/开漏总线是否有正确上拉、终端和电平。
- ADC 输入是否超出电压域。
- BOOT、NRST、SWD/JTAG、晶振脚是否被误改。
- USB、CAN、RS-485、以太网等接口是否需要隔离、终端或方向控制。
- 烧录动作是否可能擦除 bootloader、校准区、密钥区或恢复路径。

把不确定性暴露出来，才是硬件工作流真正可上线、可复用、可安全扩展的关键。
