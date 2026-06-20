# Hardware Development Butler Blueprint

## Product Goal

做一个面向真实硬件开发的 AI 管家，而不是单点问答工具。它应该能接收一个硬件项目资料夹，理解市面常见 MCU/SoC、开发板、自研板、模块板和工具链生态，并把开发流程推进到可验证结果。

核心目标：

- 收集和理解资料：原理图、PCB、BOM、datasheet、用户手册、应用笔记、CubeMX `.ioc`、固件代码、日志。
- 解释硬件设计：电源、时钟、复位、启动模式、调试接口、外设、总线、传感器、执行器、通信模块。
- 接入固件工程：CubeMX 生成代码、Keil、CMake/GCC、EIDE、Makefile。
- 编译烧录调试闭环：build -> flash -> debug -> observe -> diagnose -> fix -> rebuild -> reflash。
- 沉淀知识：把问题、根因、修复和验证结果写回项目文档。

## Architecture

```text
hardware-development-butler
  -> chip-bringup
       芯片资料检索/下载、手册总结、CubeMX/引脚配置、FreeRTOS 实现、安全 bring-up 门控
  -> nextboard-hardware-architect
       硬件资料理解、方案/原理图/BOM/验证计划、风险判断
  -> embeddedskills-lab-operator
       工程发现、编译、烧录、debug、串口/CAN/网络观测
  -> project memory/docs
       板卡画像、问题库、修复记录、验证记录
```

## Current MVP Reality

The current landing is a safety-first MVP, not a fully autonomous hardware lab.

- Multi-agent supervision is represented by Codex agent roles and adversarial review records; the shipped CLI remains a deterministic local facade.
- Automatic execution is limited to allowlisted discovery and diagnostic commands.
- Build, flash, erase, debug control, bus transmit, and network scan are not executed by the safe runner.
- Real hardware-changing actions require a separate explicit confirmation path before they can be added.
- File-writing documentation actions are separate from hardware-changing actions and must be requested or enabled through explicit flags.

## Capability Modules

### 1. Project Dossier

为每个硬件项目建立资料档案：

- `docs/project-dossier.md`: 已有资料、缺失资料、可信来源、版本
- `docs/board-profile.md`: 芯片、供电、时钟、复位、启动、调试接口、外设
- `docs/firmware-profile.md`: CubeMX、HAL/LL、RTOS、编译器、启动文件、链接脚本
- `docs/debug-logbook.md`: 每次编译/烧录/debug/观测记录
- `docs/issues.md`: 问题、根因、修复、验证、剩余风险

### 2. Hardware Understanding

覆盖常见硬件开发认知：

- MCU/SoC：STM32、GD32、CH32、ESP32、Nordic、NXP、TI、Microchip、Raspberry Pi RP 系列等
- 电源：LDO、DCDC、电池充电、保护、上电时序、电流预算、热风险
- 时钟与复位：HSE/LSE/HSI/PLL、晶振匹配、BOOT0/BOOTSEL、NRST、看门狗
- 调试与下载：SWD、JTAG、UART bootloader、USB DFU、J-Link、ST-Link、CMSIS-DAP、DAPLink
- 外设：GPIO、ADC、DAC、PWM、Timer、I2C、SPI、UART、USB、CAN、Ethernet、SDIO、QSPI
- 系统问题：EMC、ESD、地线、电源纹波、上拉下拉、接口电平、端接、隔离、热设计

### 2.5 Chip Knowledge Base And Handbook

把“我想开发某个芯片”变成可执行入口：

- 按芯片/开发板型号建立 `docs/chip/<part>/` 资料包。
- 搜索并下载 datasheet、reference manual、programming manual、errata、application notes、开发板手册和原理图。
- 总结快速上手要点：供电、电气限制、封装/引脚、时钟、复位、启动、调试、Flash/RAM、外设、DMA/IRQ、勘误和首烧检查。
- 把每个关键结论绑定到来源：官方 PDF、分销商附件、开发板原理图、CubeMX `.ioc` 或日志证据。
- 遇到资料缺失时明确标注 `unknown`，不凭记忆补齐。

### 3. CubeMX/Firmware Integration

优先支持 STM32 CubeMX 导出工程：

- 识别 `.ioc` 中的芯片型号、时钟、外设、引脚、middleware
- 解释用户指定引脚如何配置为 GPIO/I2C/SPI/UART/CAN/ADC/PWM/Timer/USB/Ethernet 等功能，并说明 CubeMX 页面、alternate function、GPIO 模式、上下拉、速度、DMA、NVIC、时钟和 middleware 配置。
- 给出“为什么这么配、还能怎么配、这么配要注意什么”，包括板级原理图冲突、调试/启动引脚占用、电压域、上拉电压、负载电流和信号完整性。
- 识别 Keil、CMake/GCC、Makefile、EIDE 等构建入口
- 检查启动文件、链接脚本、HAL 驱动版本、include 路径、宏定义
- 解析常见编译错误：头文件缺失、重复定义、未定义符号、链接段溢出、库不匹配
- 将修复限制在用户代码区或明确的工程配置文件，避免无意破坏 CubeMX 可再生成结构

### 4. Build/Flash/Debug Loop

由 embeddedskills 执行或推荐命令：

- build：Keil、CMake/GCC、EIDE
- flash：J-Link、OpenOCD、probe-rs
- debug：GDB、J-Link GDB Server、OpenOCD GDB Server、probe-rs GDB
- observe：UART、RTT、SWO、semihosting、CAN、network
- diagnose：把日志和硬件画像合并分析，输出下一步动作

硬件改变动作必须通过安全门控：

- 首次烧录前确认芯片/板卡身份、目标电压、电流限制、调试器、擦写范围和恢复路径。
- 输出引脚、功率负载、总线发送、option bytes/fuses、读保护、mass erase 和复位/调试控制都不能自动执行。
- 对可能损坏芯片或外设的动作，先输出风险、确认项和最小安全测试。

### 5. Issue Repair Pattern

每个问题都按固定结构处理：

| 字段 | 说明 |
| --- | --- |
| Symptom | 用户看到的现象或日志 |
| Evidence | 构建日志、烧录日志、串口/CAN/网络记录、原理图/手册依据 |
| Root cause | 明确根因；不明确时标记假设 |
| Fix | 最小改动或操作建议 |
| Verification | 复测命令、预期结果、实际结果 |
| Risk | 剩余风险和后续验证 |

## MVP Scope

第一期不要追求覆盖所有板子，先把闭环跑顺：

1. STM32 + CubeMX 工程识别
2. Keil 或 CMake/GCC 构建
3. J-Link/ST-Link/OpenOCD/probe-rs 烧录路径选择
4. 串口日志采集和解释
5. 编译错误分类和自动修复建议
6. 固件产物大小分析
7. `docs/` 下自动沉淀 board profile、issues、debug logbook

## Non-Goals For MVP

- 不直接生成复杂 PCB 或完整 EDA 工程。
- 不在没有用户确认时烧录、擦除、写内存或发送总线报文。
- 不承诺覆盖所有厂商专用 IDE。
- 不凭记忆给出器件参数、引脚定义、电气限制。

## Later Extensions

- 原理图 PDF/图片 OCR 与网络表抽取
- KiCad/立创 EDA/JLCEDA MCP 接入
- CubeMX `.ioc` 深度解析脚本
- 自动生成 `.embeddedskills/config.json`
- 常见开发板知识库和芯片系列知识卡
- 逻辑分析仪/示波器/电源仪器接入
- 批量问题回归测试和硬件 bring-up checklist
