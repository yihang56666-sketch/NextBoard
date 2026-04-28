# NextBoard — Hardware Solution Plugin

面向嵌入式产品硬件方案设计的 AI 辅助工作流插件。

## 快速开始

调用 `$hardware-solution` 技能，输入产品需求，获得可评审、可落地的硬件方案。

## 安装 / 更新 / 删除

以下命令默认在本仓库根目录 `/home/xiaozhi/work/NextBoard` 执行。安装或更新后，需要重启 Codex 或 Claude Code 会话，让客户端重新加载 skill 列表。

安装分两种：

- 基础安装：只安装 `skills/hardware-solution`，保证 `$hardware-solution` 可用。
- 增强安装：在基础安装之外安装 `agents/hardware-reviewer.md`。`hooks/` 默认不复制到全局目录，除非通过插件机制加载本仓库。

### Codex

Codex 基础安装只复制 `skills/hardware-solution`。当前 Codex 使用这个 skill 时，不依赖 `agents/` 和 `hooks/`；如果没有 agent 支持，会按 skill 内的评审维度在当前会话自检。

安装或更新：

```bash
mkdir -p "$HOME/.codex/skills"
rm -rf "$HOME/.codex/skills/hardware-solution"
cp -r skills/hardware-solution "$HOME/.codex/skills/"
```

删除：

```bash
rm -rf "$HOME/.codex/skills/hardware-solution"
```

验证：

```bash
python3 /home/xiaozhi/.codex/skills/.system/skill-creator/scripts/quick_validate.py "$HOME/.codex/skills/hardware-solution"
```

### Claude Code

Claude Code 基础安装只复制 `skills/hardware-solution`。这足够触发 `$hardware-solution`。

基础安装或更新：

```bash
mkdir -p "$HOME/.claude/skills"
rm -rf "$HOME/.claude/skills/hardware-solution"
cp -r skills/hardware-solution "$HOME/.claude/skills/"
```

增强安装：额外安装独立评审 agent。

```bash
mkdir -p "$HOME/.claude/agents"
cp agents/hardware-reviewer.md "$HOME/.claude/agents/"
```

删除基础 skill 和增强 agent：

```bash
rm -rf "$HOME/.claude/skills/hardware-solution"
rm -f "$HOME/.claude/agents/hardware-reviewer.md"
```

### Hooks 说明

`hooks/` 只用于 Claude Code 插件模式下的会话启动提醒，不建议手动复制到全局目录：

- 基础安装不会安装 `hooks/`。
- 增强安装也不会安装 `hooks/`。
- 通过插件机制加载本仓库时，`.claude-plugin/` 会引用 `hooks/hooks.json`，再调用 `hooks/session-start`。

如果只想验证 hook 是否工作，使用下面的开发测试命令即可。

### 本仓库插件开发测试

检查 Codex skill 结构：

```bash
python3 /home/xiaozhi/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/hardware-solution
```

检查 Claude Code session hook 输出：

```bash
CLAUDE_PLUGIN_ROOT="$PWD" hooks/session-start | python3 -m json.tool
```

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
