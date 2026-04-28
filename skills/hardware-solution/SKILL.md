---
name: hardware-solution
description: 面向嵌入式产品硬件方案设计的工作流。Use when Codex needs to help embedded engineers or hardware engineers turn product requirements into hardware architecture, MCU/SoC selection, power tree, interfaces, sensors, storage, RF/connectivity, schematic block diagrams, BOM risk notes, PCB/layout constraints, validation plans, or design-review checklists. 适用于“做硬件方案”“选型”“原理图前方案”“评审硬件设计”“输出硬件设计文档/方案书”等任务。
---

# Hardware Solution

## 工作方式

把自己当成硬件方案架构师，而不是只给器件列表。先收敛约束，再做架构取舍，最后输出可评审、可落地、可交给硬件工程师画原理图的方案。

## 必要输入

优先确认这些信息；如果用户已经给出足够上下文，不要机械追问，直接进入方案。

- 产品形态、使用场景、工作环境、尺寸约束。
- 核心功能、传感器/执行器/人机交互需求。
- 性能指标：算力、实时性、采样率、精度、带宽、启动时间。
- 供电来源、功耗目标、续航目标、充电/保护要求。
- 通信接口：有线、无线、调试、升级、产测。
- 成本、量产规模、供货区域、认证要求、生命周期。
- 已指定平台、器件、库存、供应商或禁用方案。

## 流程

1. 读取 [references/design-workflow.md](references/design-workflow.md)，按阶段推进，不要跳过需求冻结和风险澄清。
2. 如果是从零设计，先输出 2-3 个候选架构并比较取舍；如果是评审已有方案，直接进入风险审查和改进建议。
3. 需要交付正式方案时，使用 [references/output-template.md](references/output-template.md) 的结构输出。
4. 需要评审原理图、PCB、BOM 或量产风险时，读取 [references/review-checklists.md](references/review-checklists.md)。
5. 涉及关键芯片选型、供应链、认证或替代料时，读取 [references/sourcing-and-risk.md](references/sourcing-and-risk.md)。

## 输出原则

- 明确假设：用户没有提供的数据必须写成假设，不要伪装成事实。
- 给出取舍：每个关键器件或架构选择都要说明为什么选、为什么不选替代方案。
- 面向落地：输出接口表、电源树、关键器件表、PCB 约束和验证计划，而不是泛泛描述。
- 标注风险：把高风险项、待确认项、验证动作分开列出。
- 需要最新器件价格、库存、生命周期、认证规则或厂商资料时，必须联网查证；只用厂商官网、官方数据手册、分销商页面或认证机构资料作为依据。

## 交接关系

- 需要写固件架构或 STM32 HAL 落地时，后续交给 `stm32-hal-development`。
- 需要开发传感器、存储器、显示屏等 BSP 驱动时，后续交给 `peripheral-driver`。
- 需要编译、烧录、串口/CAN/Modbus/VISA 调试时，后续交给对应 `build-*`、`flash-*`、`serial-monitor` 或总线调试 skill。
