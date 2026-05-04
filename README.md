# NextBoard — Hardware Solution Plugin

面向嵌入式产品硬件方案设计的 AI Agent工作流。输入产品需求，输出可评审、可落地、可交给硬件工程师画原理图的方案。

-设计一个无人机方案
-设计一个FOC控制器
-设计一个记单词的墨水屏卡片
Agent会自动帮你进行需求确认，实时分析国内外各类芯片技术方案，进行器件选型，下载datasheet，输出BOM表，输出模块原理图，最终整合成技术方案。

## 功能概览

- 结构化的 7 阶段设计流程：需求冻结 → 架构候选 → 系统分解 → 器件选型 → 输出生成 → 评审 → 验证门控
- 三类架构候选对比：国产优先、海外主流、混合折中
- 5 道验证门控，阶段性拦截质量问题
- 独立评审 agent，从完整性、风险、可实施性、成本、验证覆盖 5 个维度打分
- 供应链风险评估与国产替代参考

## 快速开始

在 Claude Code、Codex 或 Cursor 会话中调用：

```
$hardware-solution
```

输入产品需求即可进入设计流程。

## 安装

安装后需重启 AI IDE 会话，让客户端重新加载 skill 列表。

### AI 安装指引

> 本节供 AI 助手（Claude Code、Codex、Cursor 等）阅读。当用户要求安装本插件时，按以下流程引导。

**第一步：确认当前环境**

运行 `./scripts/install.sh --status` 查看是否已安装。

**第二步：引导用户选择安装方式**

向用户说明三种方式的区别，让用户选择：

| 方式 | 适用场景 | 可用组件 | 限制 |
|------|---------|---------|------|
| 全局安装 | 希望所有项目都能用 | skill + agent | hooks 不生效 |
| --plugin-dir | 开发调试或临时使用 | skill + agent + hooks | 每次启动需指定路径 |
| Marketplace | 正式分发 | skill + agent + hooks | 需要 GitHub 访问 |

**第三步：执行安装**

用户选择后，运行对应命令：

```bash
# 全局安装（Claude Code，含 agent）
./scripts/install.sh --global --platform claude

# 全局安装（Codex，skill + agent）
./scripts/install.sh --global --platform codex

# --plugin-dir（单次会话加载，skill + agent + hooks 全部可用）
claude --plugin-dir /path/to/NextBoard

# Marketplace 安装
claude plugin marketplace add LeoKemp223/NextBoard
claude plugin install nextboard-hardware-solution
```

如果 `scripts/install.sh` 不可用（例如用户未克隆本仓库），按下方"手动安装"章节的命令执行。

**第四步：验证**

安装完成后提醒用户重启会话，然后调用 `$hardware-solution` 验证是否生效。

### 交互式安装

```bash
git clone <NextBoard-repo-url>
cd NextBoard
./scripts/install.sh
```

脚本会显示当前安装状态，引导你选择安装方式。

### 手动安装

#### 方式一：全局安装

从 NextBoard 仓库复制文件到全局目录，所有项目都能使用 `$hardware-solution`。

```bash
git clone <NextBoard-repo-url>
cd NextBoard
```

Claude Code：

```bash
# 基础安装（skill）
mkdir -p "$HOME/.claude/skills"
rm -rf "$HOME/.claude/skills/hardware-solution"
cp -r skills/hardware-solution "$HOME/.claude/skills/"

# 增强安装（额外安装独立评审 agent）
mkdir -p "$HOME/.claude/agents"
cp agents/hardware-reviewer.md "$HOME/.claude/agents/"
```

Codex：

```bash
mkdir -p "$HOME/.codex/skills"
rm -rf "$HOME/.codex/skills/hardware-solution"
cp -r skills/hardware-solution "$HOME/.codex/skills/"

mkdir -p "$HOME/.codex/agents"
cp agents/hardware-reviewer.md "$HOME/.codex/agents/"
```

> 全局安装的局限：hooks 无法生效（缺少插件上下文）。

#### 方式二：--plugin-dir（推荐开发调试）

直接从 NextBoard 仓库加载插件，skill + agent + hooks 全部可用，无需复制文件。

```bash
claude --plugin-dir /path/to/NextBoard
```

每次启动 Claude Code 时需要指定 `--plugin-dir` 参数。

#### 方式三：Marketplace 安装

通过 Claude Code 插件市场安装，适合正式分发。

```bash
# 添加 NextBoard marketplace
claude plugin marketplace add LeoKemp223/NextBoard

# 安装插件
claude plugin install nextboard-hardware-solution
```

### 更新

```bash
# 全局安装：pull 后重新执行安装
cd NextBoard && git pull
./scripts/install.sh --global --platform claude

# --plugin-dir：pull 即可，下次启动自动加载最新版
cd NextBoard && git pull
```

### 卸载

```bash
# 全局卸载
./scripts/install.sh --uninstall

# 项目级卸载
./scripts/install.sh --uninstall-project /path/to/your-project

# 或手动卸载全局安装
rm -rf "$HOME/.claude/skills/hardware-solution"
rm -f "$HOME/.claude/agents/hardware-reviewer.md"
rm -rf "$HOME/.codex/skills/hardware-solution"
rm -f "$HOME/.codex/agents/hardware-reviewer.md"
```

## 项目结构

```
NextBoard/
├── skills/hardware-solution/
│   ├── SKILL.md                        # 技能入口，定义工作流和输出原则
│   └── references/
│       ├── design-workflow.md           # 4 阶段设计工作流
│       ├── output-template.md           # 方案输出标准结构
│       ├── verification-gates.md        # 5 道验证门控
│       ├── review-checklists.md         # 原理图/PCB/BOM/方案评审清单
│       ├── sourcing-and-risk.md         # 供应链风险评估指南
│       └── domestic-sources.md          # 国产芯片与元器件参考
├── agents/
│   └── hardware-reviewer.md             # 独立评审 agent（增强安装）
├── hooks/
│   ├── hooks.json                       # Claude Code 会话启动 hook 配置
│   └── session-start                    # 会话启动提醒脚本
├── scripts/
│   └── install.sh                       # 交互式安装/卸载脚本
├── tests/
│   └── validate.py                      # 结构与内容一致性验证脚本
├── .claude-plugin/                      # Claude Code 插件配置
├── .codex-plugin/                       # Codex 插件配置
├── .cursor-plugin/                      # Cursor 插件配置
├── CLAUDE.md                            # Claude Code / 通用 AI 会话项目指令
└── AGENTS.md                            # Cursor Agent Mode / 通用 Agent 指令
```

## 验证

修改 skill 或 reference 文档后，运行验证脚本检查结构完整性和内容一致性：

```bash
# 验证仓库源文件
python3 tests/validate.py

# 验证已安装的副本
python3 tests/validate.py --installed
```

验证覆盖三层检查：

| 层 | 内容 |
|---|---|
| 结构完整性 | 文件存在、hook 可执行、hook 输出合法 JSON |
| 内容一致性 | SKILL.md 链接可解析、Gate 非空、输出模板覆盖 Gate 4、评审 agent 覆盖 5 维度 |
| 反模式检测 | reference 文档无模糊措辞、无残留占位符 |

## Hooks 说明

`hooks/` 仅在项目级插件模式下自动生效（`.claude-plugin/plugin.json` 声明了 `"hooks": "./hooks/"`）。全局安装不包含 hooks。

手动验证 hook 输出：

```bash
CLAUDE_PLUGIN_ROOT="$PWD" hooks/session-start | python3 -m json.tool
```

## 输出质量要求

- 器件参数必须来自数据手册或分销商页面，禁止凭记忆
- 每个关键选择必须说明取舍，不能只列器件
- 风险清单不能为空，高风险项必须有验证动作
- 方案输出前必须通过 `verification-gates.md` 的 5 道门控

## 贡献规范

- 修改 skill 或 reference 文档需提供修改前后的对比说明
- 新增参考文档需在 SKILL.md 流程部分添加引用入口
- 不接受没有实际硬件设计场景验证的修改
- 提交前运行 `python3 tests/validate.py` 确保验证通过

## 平台支持

| 平台 | 配置文件 | 全局安装 | 项目级插件 |
|------|---------|---------|-----------|
| Claude Code | `.claude-plugin/plugin.json` | skill + agent | skill + agent + hooks |
| Codex | `.codex-plugin/plugin.json` | skill + agent | 不支持插件模式 |
| Cursor | `.cursor-plugin/plugin.json` | skill（手动 cp） | skill + agent + hooks |

## License

MIT
