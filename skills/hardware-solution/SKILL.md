---
name: hardware-solution
description: "Use when the user needs embedded hardware architecture, MCU/SoC selection, power tree design, interface planning, sensor/actuator selection, RF/connectivity, BOM risk assessment, PCB/layout constraints, schematic-ready proposals, validation plans, or hardware design review."
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
2. 先给用户一个"需求澄清选择题"：用 2-4 个具体选项确认优先级、成本/功耗/周期取向、国内/海外/混合供应链偏好。**所有标记为"待确认"的约束项必须逐一向用户确认，不能默认跳过或自行假设。** 用户选择或授权基于假设推进后，才能进入深入选型。
3. 如果是从零设计，先输出 3 类候选架构并比较取舍：国产芯片/国产供应链优先、海外主流生态优先、混合折中方案。若某类不适用，必须说明原因；如果是评审已有方案，直接进入风险审查和改进建议。
4. 关键器件建议必须附带：采购链接（国内电商平台或分销商页面 URL，优先淘宝/立创商城/嘉立创 > 授权分销商 > 原厂官网）、datasheet 下载链接（优先 AllDatasheet > 立创商城 > 半导小芯 > 原厂官网）、封装文件下载链接（优先立创 EDA 封装库/华秋 DFM 封装库 > 嘉立创封装库 > SnapEDA/Ultra Librarian > 原厂）。无法提供时标注"需联网查证"。
5. Gate 3 通过后，询问用户使用的 EDA 工具，然后批量下载已选器件的 datasheet（PDF）和对应格式的封装文件，保存至 `docs/hardware/datasheets/` 和 `docs/hardware/footprints/` 目录。下载失败的标注原因并提供手动下载链接。
6. 需要交付正式方案时，使用 [references/output-template.md](references/output-template.md) 的结构输出。
7. 需要评审原理图、PCB、BOM 或量产风险时，读取 [references/review-checklists.md](references/review-checklists.md)。
8. 涉及关键芯片选型、供应链、认证或替代料时，读取 [references/sourcing-and-risk.md](references/sourcing-and-risk.md)；涉及国产芯片、国内元器件渠道或国产替代时，同时读取 [references/domestic-sources.md](references/domestic-sources.md)。
9. 每个阶段结束前，读取 [references/verification-gates.md](references/verification-gates.md) 确认门控通过。
10. 评审通过后询问用户是否需要输出模块原理图。如果用户确认需要，先提供展示方式选项供用户选择（结构化连接表 / ASCII 框图 / KiCad 网表），然后按用户选择的方式和指定的模块范围输出。通过 Gate 6 后交付。

## 文件输出规则

有表格产出的阶段必须输出为 markdown 文件，保存在用户项目的 `docs/hardware/` 目录下（目录不存在时创建）。文件命名规则：

| 阶段 | 文件名 | 内容 |
|------|--------|------|
| 1. 需求冻结 | `01-requirements.md` | 工程约束表、优先级选择、确认记录 |
| 2. 架构候选 | `02-architecture.md` | 候选架构对比表、用户选择结论 |
| 4. 关键选型 | `03-components.md` | 器件建议表（含采购链接、datasheet 链接、封装下载链接）、替代方案 |
| 4.5 资料下载 | `datasheets/*.pdf` + `footprints/*` | 已选器件的 datasheet PDF 和封装文件 |
| 5. 约束输出 | `04-constraints.md` | 接口矩阵、电源树、PCB/机械/DFM 约束 |
| 6. 验证计划 | `05-validation.md` | EVT/DVT/PVT 测试项表 |
| 7. 决策门 | `06-decisions.md` | 已确定/待确认/高风险三类事项 |
| 8. 模块原理图 | `07-schematics.md` 或 `07-schematics.net` | 按用户选择的方式输出 |

交付正式方案时（步骤 5），同时按 output-template 结构输出完整方案文件 `hardware-solution.md`。

每个文件顶部包含项目名称、日期、阶段编号。后续阶段更新时追加或覆盖对应文件。

## 输出原则

- 明确假设：用户没有提供的数据必须写成假设，不要伪装成事实。
- 给出取舍：每个关键器件或架构选择都要说明为什么选、为什么不选替代方案。
- 面向落地：输出接口表、电源树、关键器件表、PCB 约束和验证计划，而不是泛泛描述。
- 标注风险：把高风险项、待确认项、验证动作分开列出。
- 需要最新器件价格、库存、生命周期、认证规则或厂商资料时，必须联网查证；只用厂商官网、官方数据手册、分销商页面或认证机构资料作为依据。

## 反模式（不要做）

- 不要凭记忆给出器件型号、参数、价格或库存信息。必须联网查证或明确标注为假设。
- 不要跳过需求冻结直接选型。缺失的约束会导致后期返工。
- 不要只列器件清单而不解释架构取舍。"用了什么"不等于"为什么这样设计"。
- 不要输出泛泛描述（"选择合适的 MCU""使用低功耗方案"）。必须给出具体型号、参数和理由。
- 不要在用户没有确认架构方向时就深入选型细节。
- 不要忽略风险评估。风险清单为空意味着评估不充分，不是没有风险。
- 不要假设器件在产、有货、有认证。这些必须查证。

## 常见合理化借口

以下是执行过程中容易出现的"合理化"想法。如果你发现自己在这样想，停下来。

| 想法 | 现实 |
|------|------|
| "这个芯片我很熟，不用查手册" | 参数必须来自 datasheet，记忆不可靠，型号/封装/温度范围经常记错 |
| "风险清单先空着，后面补" | 风险清单不能为空，这是 Gate 5 的硬性门控 |
| "只有一个方案可选，不需要对比" | 至少说明为什么排除了其他方向，单一方案也要有取舍说明 |
| "用户没提功耗要求，跳过电源树" | 电源树是必选输出，缺失约束应标注为假设而不是跳过 |
| "这个需求很明确，不用冻结直接选型" | 需求冻结是 Gate 1，跳过会导致后期返工 |
| "先给个大概方案，细节后面再补" | 输出必须面向落地，泛泛描述不符合输出原则 |
| "国产替代不适用这个场景" | 必须说明为什么不适用，不能默认跳过国产候选 |
| "价格和库存我大概知道" | 价格、库存、生命周期必须联网查证，不能凭印象 |

## 结构化选项

遇到需要用户决策的分歧点时，优先给出 2-4 个具体选项，避免把约束澄清变成开放式闲聊。当关键约束未知且无法合理枚举时，只问一个必要的开放问题。

1. 方案名称
2. 核心差异（一句话）
3. 适用条件
4. 主要风险

示例格式：
- 方案 A：国产 MCU + 国产 RS485/电源器件 — 供应链自主性更好，适合国产替代或成本敏感项目，需验证生态和长期供货
- 方案 B：STM32/MSP430 等海外主流 MCU + 成熟模拟器件 — 生态成熟、开发风险低，适合交付周期紧的项目，需确认供货和价格
- 方案 C：国产主控 + 海外关键模拟/传感器 — 成本、生态和供应风险折中，适合量产前快速收敛，BOM 管理复杂度更高

## 验证门控

每个阶段结束前，读取 [references/verification-gates.md](references/verification-gates.md) 中对应的门控检查项。未通过的项不能进入下一阶段。

完成方案输出后进行独立评审：如果当前平台支持 agents，使用 `hardware-reviewer` agent；如果不支持，则按 [../../agents/hardware-reviewer.md](../../agents/hardware-reviewer.md) 的五个维度在当前会话内自检。评审发现的 CONCERN 和 FAIL 项必须处理或标注为待确认后才能交付。

## 交接关系

- 需要写固件架构或 STM32 HAL 落地时，后续交给 `stm32-hal-development`。
- 需要开发传感器、存储器、显示屏等 BSP 驱动时，后续交给 `peripheral-driver`。
- 需要编译、烧录、串口/CAN/Modbus/VISA 调试时，后续交给对应 `build-*`、`flash-*`、`serial-monitor` 或总线调试 skill。
