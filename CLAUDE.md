# NextBoard — Hardware Solution Plugin

面向嵌入式产品硬件方案设计的 AI 辅助工作流插件。

## 快速开始

调用 `$hardware-solution` 技能，输入产品需求，获得可评审、可落地的硬件方案。

## 平台支持

- Claude Code：通过 `.claude-plugin/`、`skills/`、`agents/`、`hooks/` 使用；会话启动 hook 只注入短提醒，不注入完整 skill 内容。
- Codex：通过 `.codex-plugin/plugin.json` 和 `skills/` 使用；如果 Codex 不支持 `agents/` 或 `hooks/`，仍可按 skill 内的评审维度完成自检。

## 项目结构

- `skills/hardware-solution/SKILL.md` — 技能入口，定义工作方式和流程
- `skills/hardware-solution/references/` — 参考文档（工作流、输出模板、评审清单、供应链风险、验证门控）
- `agents/hardware-reviewer.md` — 硬件评审子代理定义
- `hooks/` — Claude Code 会话启动提醒

## 输出质量要求

- 器件参数必须来自数据手册或分销商页面，禁止凭记忆回答。
- 每个关键选择必须说明取舍，不能只列器件。
- 风险清单不能为空，高风险项必须有验证动作。
- 方案输出前必须通过 `references/verification-gates.md` 中的门控检查。

## 贡献规范

- 修改 skill 或 reference 文档需要提供修改前后的对比说明。
- 新增参考文档需要在 SKILL.md 的流程部分添加引用入口。
- 不接受没有实际硬件设计场景验证的修改。
