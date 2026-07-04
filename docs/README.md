# Documentation Index

这里是文档导航。新手先看主动维护的文档，历史报告只在需要追溯设计过程时再看。

## Active Path

| 文档 | 适合什么时候看 |
| --- | --- |
| [BEGINNER_GUIDE.md](BEGINNER_GUIDE.md) | 完全第一次接触项目，想用 5 分钟跑通安全示例。 |
| [START_HERE.md](START_HERE.md) | 第一天使用项目，想知道先跑什么。 |
| [INSTALL.md](INSTALL.md) | 需要安装、editable CLI、embeddedskills runtime 路径说明。 |
| [ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md) | 想快速理解入口、证据层、计划层、执行后端和安全网络。 |
| [HARDWARE_UNDERSTANDING.md](HARDWARE_UNDERSTANDING.md) | 想把具体板卡从资料、CubeMX、固件到台架安全完整吃透。 |
| [COMMANDS.md](COMMANDS.md) | 已经知道任务，想快速找命令。 |
| [WORKBENCH_TUTORIAL.md](WORKBENCH_TUTORIAL.md) | 想用 GUI 工作台。 |
| [AUTO_WORKFLOW_GUI.md](AUTO_WORKFLOW_GUI.md) | 想理解 `auto` 和 `next-step` 的安全流程。 |
| [WORKBENCH_FEATURE_COVERAGE.md](WORKBENCH_FEATURE_COVERAGE.md) | 想知道 GUI 已接入哪些能力，哪些仍是 CLI-only。 |
| [CONFIGURATION.md](CONFIGURATION.md) | 需要理解 `.embeddedskills/config.json` 和配置写入。 |
| [GITHUB_LAUNCH_CHECKLIST.md](GITHUB_LAUNCH_CHECKLIST.md) | 上线 GitHub 前的结构、验证、安全和仓库设置清单。 |
| [RELEASE_PROCESS.md](RELEASE_PROCESS.md) | 发布分支、验证、打 tag 和 GitHub release 的步骤。 |
| [GITHUB_REPOSITORY_SETTINGS.md](GITHUB_REPOSITORY_SETTINGS.md) | GitHub About、topics、branch protection 等远端设置建议。 |
| [../CHANGELOG.md](../CHANGELOG.md) | 版本变化和首发范围。 |

## Reference

| 文档 | 内容 |
| --- | --- |
| [FEATURES_AND_USAGE.md](FEATURES_AND_USAGE.md) | 较完整的功能说明和旧命令参考。 |
| [hardware-butler-usage.md](hardware-butler-usage.md) | 早期使用说明。 |
| [hardware-butler-blueprint.md](hardware-butler-blueprint.md) | 设计蓝图。 |
| [OPEN_SOURCE_INTEGRATION.md](OPEN_SOURCE_INTEGRATION.md) | 开源工具集成思路。 |
| [VS_TRADITIONAL_WORKFLOW.md](VS_TRADITIONAL_WORKFLOW.md) | 与传统流程对比。 |

## Project Reports And History

这些文档更像阶段性报告，不建议作为新手入口：

| 文档 | 用途 |
| --- | --- |
| `FINAL_REPORT.md` | 阶段最终报告。 |
| `PROGRESS.md` | 进度记录。 |
| `QA_CRITICAL_FINDINGS.md` | QA 关键发现。 |
| `REFACTORING_REPORT.md` | 重构报告。 |
| `MULTI_AGENT_*.md` | 多 agent 实验记录。 |
| `adversarial-iteration-*.md` | 对抗迭代记录。 |
| `superpowers/plans/*.md` | agent 执行计划。 |

## Generated Outputs

这些目录由工具生成，通常不需要手写：

| 路径 | 来源 |
| --- | --- |
| `docs\inspections\<project-name>\` | `onboard` / `auto` 生成的项目报告。 |
| `docs\chip\<part>\` | `chip-dossier` 生成的芯片资料包。 |
| `.hardware-butler\project-state.json` | `auto` / `next-step` 写入的项目状态。 |

## Recommended Reading Order

1. [START_HERE.md](START_HERE.md)
2. [BEGINNER_GUIDE.md](BEGINNER_GUIDE.md)
3. [INSTALL.md](INSTALL.md)
4. [ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md)
5. [HARDWARE_UNDERSTANDING.md](HARDWARE_UNDERSTANDING.md)
6. [COMMANDS.md](COMMANDS.md)
7. [WORKBENCH_TUTORIAL.md](WORKBENCH_TUTORIAL.md) 或 [AUTO_WORKFLOW_GUI.md](AUTO_WORKFLOW_GUI.md)
8. [CONFIGURATION.md](CONFIGURATION.md)
9. 需要背景时再看 Reference 和历史报告
