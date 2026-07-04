# Architecture Map

这页用一张心智地图解释项目，不展开历史细节。目标是让新用户知道“从哪里进、每层负责什么、哪些动作被安全门控”。

## 一句话

Hardware Butler 是一个安全优先的嵌入式硬件开发工作台：先收集证据和生成计划，再把构建、烧录、调试、串口、CAN、网络等动作交给受控后端。

## 四层结构

| 层 | 目录 | 负责什么 | 默认是否触碰硬件 |
| --- | --- | --- | --- |
| 入口层 | `tools/hardware_butler.py`, `gui/hardware_agent_ui.py` | CLI/GUI、命令分组、第一天指南、工作台模型。 | 否 |
| 证据层 | `tools/project_*`, `tools/evidence_*`, `tools/chip_dossier.py` | 项目扫描、CubeMX/构建识别、芯片资料、证据索引、问答。 | 否 |
| 计划层 | `tools/build_plan.py`, `tools/config_proposal.py`, `tools/hardware_action_plan.py`, `tools/bench_runbook.py` | 生成构建发现计划、配置提案、硬件动作计划、台架 runbook。 | 否 |
| 执行后端层 | `embeddedskills/` | Keil/GCC/EIDE、J-Link/OpenOCD/probe-rs、串口、CAN、网络、workflow。 | 只有经过门控后才允许 |

`nextboard/` 是硬件方案和评审层，负责器件选型、BOM 风险、PCB/原理图约束和报告。

## 主要数据流

```text
真实项目 <project-root>
  -> doctor / auto / brain / ask
  -> docs/inspections/<project-name>/ 报告
  -> .hardware-butler/project-state.json 状态
  -> next-step 推荐下一条安全命令
  -> bench-runbook / plan-action 生成硬件动作证据包
  -> embeddedskills 后端 dry-run / sim / gated execution
```

默认流程停在“报告、计划、dry-run、仿真、推荐动作”。真实 flash、erase、reset、debug、总线写入和长时间观测仍是 `planned-gated`。

## 硬件理解闭环

“透彻理解硬件”不是靠模型记忆，而是把每个结论落到证据：

```text
本地项目证据
  -> chip-dossier / summarize-manual 绑定芯片资料
  -> advise-pin / patch-ioc dry-run 验证 CubeMX 和引脚复用
  -> firmware-plan / firmware-patch dry-run 找到固件实现边界
  -> bench-runbook / plan-action 汇总台架证据和确认条件
```

每个结论都应该能标成 `confirmed`、`inferred` 或 `needs verification`。没有资料或本地证据时，正确输出是 unknown，而不是猜一个看似合理的硬件参数。

完整流程见 [HARDWARE_UNDERSTANDING.md](HARDWARE_UNDERSTANDING.md)。

## embeddedskills 运行时

工具通过 `tools/runtime_context.py` 查找 embeddedskills 运行时，顺序是：

1. `HW_BUTLER_EMBEDDEDSKILLS_ROOT` 环境变量指向的外部 checkout。
2. 根目录 `embeddedskills/`，适合本地开发或 submodule。
3. `plugins/hardware-development-butler/scripts/embeddedskills/`，适合打包插件运行时。

用这个命令看当前命中的位置：

```powershell
python tools\hardware_butler.py doctor --root <project-root> --json
```

检查项 `embeddedskills.runtime` 会给出 `path`、`source` 和是否可用。

安装和 runtime 选择的完整说明见 [INSTALL.md](INSTALL.md)。

## 安全网络

| 机制 | 位置 | 作用 |
| --- | --- | --- |
| 安全命令 allowlist | `tools/command_runner.py` | 只允许只读/发现类脚本通过 safe runner。 |
| 确认 token | `tools/hardware_action_plan.py`, `embeddedskills/safety_gate.py` | 把动作、目标、后端、电压电流、产物 hash、擦除范围等绑定在一起。 |
| 执行器门控 | `tools/hardware_action_executor.py` | 默认只允许 fake/sim/safe build；真实硬件后端继续阻断。 |
| 台架 runbook | `tools/bench_runbook.py` | 在碰硬件前汇总证据、预检和 dry-run 输出。 |
| 审计日志 | `.embeddedskills/safety-log.jsonl` | 记录 token 消费和执行摘要，不暴露原始 token。 |

## 新手只需要记住

1. 先跑 `guide`，再跑 `doctor`。
2. 想省命令就打开 GUI。
3. `auto` 和 `next-step` 是第一天主线。
4. 任何真实硬件动作都必须先有 plan/runbook/token。
5. 架构很宽，但入口只有一个：`python tools\hardware_butler.py ...`。
