# 硬件管家工作台功能覆盖

本文用于核查“项目功能是否都结合进去”。结论是：工作台已经把安全主流程连成一个入口，但部分高级能力仍是 CLI 一等能力，尚未做成专门的图形向导。

## 已接入工作台的主流程

这些能力已经通过 `hardware_butler.py workbench` 汇总到 GUI：

| 能力 | GUI 入口 | 后端命令 |
| --- | --- | --- |
| 项目状态总览 | 顶部状态卡 | `workbench`, `status` |
| 构建后端检测 | 流程表和动作表 | `detect` |
| 安全入驻和报告生成 | `自动分析` / `运行推荐` | `auto`, `onboard` |
| 环境检查 | `检查环境` | `doctor` |
| 下一步推荐 | `运行推荐` | `next-step` 逻辑已并入 `workbench` |
| 台架准备手册 | `准备台架手册` | `bench-runbook` |
| 安全审计 | `查看安全审计` | `safety-audit` |
| 报告清单 | 右侧报告表 | `project_workflow.workflow_reports()` |
| 硬件安全边界 | 安全卡和动作拦截 | 真实硬件动作保持 `planned-gated` |

## 已在 CLI 提供但尚未做成专门 GUI 向导

这些能力不是缺失，而是还没有独立的表单式界面：

| 能力 | 当前入口 | 建议后续 GUI 形态 |
| --- | --- | --- |
| 芯片资料包 | `chip-dossier`, `summarize-manual` | 芯片型号输入、资料源列表、下载进度、覆盖率报告 |
| CubeMX 引脚建议 | `advise-pin` | 引脚/外设表单和风险提示面板 |
| `.ioc` 安全补丁 | `patch-ioc` | dry-run 预览、差异确认、备份路径提示 |
| 固件实现计划 | `firmware-plan` | 功能意图表单和生成结果预览 |
| 固件补丁生成 | `firmware-patch`, `firmware-integrate` | 文件列表、USER CODE 区域预览、确认写入 |
| 构建日志分类 | `classify-log` | 日志拖放、错误归类、修复建议 |
| 真实硬件动作执行 | `plan-action`, `execute-action` | 仍应保持确认 token、设备身份、电压电流和回滚证据门控 |

## 安全结论

工作台当前适合作为“每天打开的总控台”：先识别项目，再生成报告，再给出下一步安全动作。它不会直接执行 flash、erase、reset、debug、observe、总线发送或网络扫描这类真实硬件动作。

真正触碰硬件的能力仍然必须走既有的计划和确认令牌流程。这一点是故意保留的安全边界，不应为了“更像一键工具”而绕过。
