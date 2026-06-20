# 硬件Agent - 新手入门指南

## 🤔 这是什么？

**硬件Agent** 是一个**智能硬件开发助手**，帮你自动完成嵌入式开发中的重复性工作。

### 简单来说

想象你有一个**会写代码的助手**，它能：
- 📋 自动整理项目文档
- 💡 告诉你怎么配置引脚
- ⚙️ 帮你生成固件代码
- 🔧 检查你的代码有没有问题
- 📱 甚至能帮你烧录固件到开发板

**就像Copilot，但专门为硬件工程师设计！**

---

## 👥 这个工具适合谁？

### ✅ 适合你，如果你：
- 🎓 刚开始学习STM32等单片机开发
- 🏢 在公司做嵌入式开发，每天重复相同操作
- 📚 经常需要查芯片手册找配置方法
- 😫 觉得写固件代码很枯燥
- 🐛 调试时不知道从哪里开始
- 📝 需要整理项目文档但懒得写

### ❌ 可能不适合，如果你：
- 🚀 只做纯软件开发（不涉及硬件）
- 🎮 做的是游戏、网站等非嵌入式项目

---

## 🎯 能帮你做什么？

### 1️⃣ **自动整理项目**

**场景**：你接手一个别人的STM32项目，乱七八糟，不知道从哪看起

**传统方式**：
- 😫 一个个文件打开看
- 😫 手动整理文档
- 😫 花2-3小时才能搞清楚

**用硬件Agent**：
```bash
hardware-butler onboard --root 项目文件夹
```
**结果**：5分钟后自动生成：
- 📋 项目总览文档
- 📱 板级配置说明
- 🔧 固件架构图
- ⚙️ 构建方法

---

### 2️⃣ **智能引脚配置**

**场景**：你想用PB6和PB7连接I2C传感器，但不知道怎么配置

**传统方式**：
- 😫 翻开800页的数据手册
- 😫 查找I2C章节
- 😫 对照引脚表
- 😫 在CubeMX里一个个设置

**用硬件Agent**：
```bash
hardware-butler advise-pin --pin PB6 --function i2c
```
**结果**：立即告诉你：
```
✅ PB6应该配置为：I2C1_SCL
✅ 复用功能：AF4
✅ 模式：开漏输出
⚠️ 注意：需要外部上拉电阻
```

---

### 3️⃣ **自动生成代码**

**场景**：你想写个代码让LED闪烁，但不记得HAL库函数怎么用

**传统方式**：
- 😫 查HAL库文档
- 😫 找例程参考
- 😫 复制粘贴改改
- 😫 还可能有bug

**用硬件Agent**：
```bash
hardware-butler firmware-patch --feature "gpio-led-blink" --write
```
**结果**：自动生成：
- ✅ `led_app.c` - 完整的LED控制代码
- ✅ `led_app.h` - 头文件
- ✅ 在`main.c`里自动添加调用代码
- ✅ 代码符合你的项目规范

---

### 4️⃣ **AI搜索芯片手册** ⭐新功能

**场景**：你想知道"STM32F407的I2C最大时钟频率是多少"

**传统方式**：
- 😫 打开1000页的PDF手册
- 😫 搜索"I2C"找到几十处结果
- 😫 一个个点开看
- 😫 花15分钟才找到答案

**用硬件Agent**：
```bash
hardware-butler query "STM32F407的I2C最大时钟频率是多少"
```
**结果**：3秒钟得到答案：
```
📖 答案：STM32F407的I2C支持以下时钟频率：
- 标准模式：最高100 kHz
- 快速模式：最高400 kHz
- 快速模式Plus：最高1 MHz

置信度：92%
来源：数据手册第587页
```

---

### 5️⃣ **一键烧录固件** ⭐新功能

**场景**：固件编译好了，要烧录到开发板

**传统方式**：
- 😫 打开J-Link软件
- 😫 选择芯片型号
- 😫 找到hex文件
- 😫 点烧录，等待...

**用硬件Agent**：
```python
from tools.backends.pyocd_backend import PyOCDBackend

backend = PyOCDBackend()
backend.flash("firmware.hex", "stm32f407vgtx")
```
**结果**：自动完成，还告诉你：
```
✅ 烧录成功
✅ 写入256KB
✅ 耗时1.2秒
✅ 校验通过
```

---

### 6️⃣ **对话式操作** ⭐新功能

**场景**：你懒得记命令，想用自然语言操作

**用硬件Agent**：
```bash
hardware-butler chat "帮我烧录固件到STM32F407"
```
**Agent回答**：
```
好的，让我帮你操作：

1. 检查调试器... ✅ 找到J-Link
2. 烧录固件... ✅ 成功
3. 复位芯片... ✅ 完成

全部完成！需要我做其他操作吗？
```

---

## 🎬 5分钟快速体验

### 第1步：安装

```bash
# 1. 下载项目
git clone https://github.com/你的仓库/hardware-agent
cd hardware-agent

# 2. 安装（很简单）
pip install -r requirements.txt

# 搞定！就这么简单 ✅
```

### 第2步：检查

```bash
# 运行健康检查
python tools/hardware_butler.py doctor
```

**看到这个就说明安装成功了**：
```
✅ Python版本：OK
✅ 工具完整性：OK
✅ 环境配置：OK
```

### 第3步：试试第一个功能

```bash
# 分析一个STM32项目（用你自己的项目路径）
python tools/hardware_butler.py onboard --root C:/你的STM32项目
```

**5分钟后，打开生成的文档**：
```
📁 docs/inspections/你的项目名/
  ├── project-dossier.md     <- 打开看看！
  ├── board-profile.md
  └── firmware-profile.md
```

**恭喜！你已经会用硬件Agent了！** 🎉

---

## 💬 常见问题（新手版）

### Q1: 我不会Python，能用吗？
**A**: 能！大部分功能都是命令行，复制粘贴就能用。

### Q2: 支持哪些芯片？
**A**: 主要支持STM32系列，理论上所有ARM Cortex-M芯片都可以。

### Q3: 会不会很难？
**A**: 不会！本指南就是为零基础写的。跟着做一遍就会了。

### Q4: 免费吗？
**A**: 基础功能完全免费。AI功能需要Anthropic API key（每个月有一定免费额度）。

### Q5: 我的项目会被上传到网上吗？
**A**: 不会！所有操作都在你电脑本地进行。

### Q6: 出错了怎么办？
**A**: 运行这个命令看详细错误：
```bash
python tools/hardware_butler.py doctor --verbose
```

### Q7: 需要什么硬件？
**A**:
- **不需要硬件**：文档整理、代码生成等功能
- **需要调试器**：烧录固件（J-Link、ST-Link等）

### Q8: 我只想试试，不想安装一堆东西
**A**: 没问题！安装很简单，只需要：
- Python 3.10+ （你可能已经有了）
- 运行一行命令：`pip install -r requirements.txt`

---

## 🎓 从零开始的3个小教程

### 教程1：5分钟整理一个项目

**你需要**：一个STM32项目文件夹

**步骤**：
```bash
# 1. 进入硬件agent目录
cd hardware-agent

# 2. 运行onboard
python tools/hardware_butler.py onboard --root "你的项目路径"

# 3. 等5分钟，喝口水 ☕

# 4. 打开生成的文档
# Windows: start docs\inspections\项目名\project-dossier.md
# Mac: open docs/inspections/项目名/project-dossier.md
```

**完成！** 你现在有一份完整的项目文档了。

---

### 教程2：3分钟生成LED闪烁代码

**你需要**：一个STM32 CubeMX项目

**步骤**：
```bash
# 1. 规划代码
python tools/hardware_butler.py firmware-plan \
  --root "你的项目路径" \
  --feature "gpio-led-blink"

# 2. 生成代码
python tools/hardware_butler.py firmware-patch \
  --root "你的项目路径" \
  --feature "gpio-led-blink" \
  --write

# 3. 打开项目，看看生成的代码
# Core/Src/led_app.c  <- 这里！
```

**完成！** 你有了完整的LED控制代码。

---

### 教程3：1分钟查芯片手册

**你需要**：芯片数据手册PDF

**步骤**：
```bash
# 1. 把数据手册放到这里
mkdir -p docs/chip/STM32F407
# 复制你的PDF到 docs/chip/STM32F407/

# 2. 问问题
python tools/backends/chip_manual_rag.py \
  docs/chip/STM32F407 \
  "I2C的时钟频率怎么配置？"

# 3. 得到答案！
```

**完成！** 不用再翻1000页PDF了。

---

## 🎁 给新手的礼物

### 常用命令速查卡

```bash
# 📋 检查环境
hardware-butler doctor

# 📋 整理项目
hardware-butler onboard --root 项目路径

# 🔧 查看项目状态
hardware-butler status --root 项目路径

# 💡 引脚建议
hardware-butler advise-pin --pin PB6 --function i2c

# 📝 生成代码
hardware-butler firmware-patch --feature led-blink --write

# 🔍 查芯片手册（需要先设置API key）
hardware-butler query "I2C配置方法"

# 🚀 烧录固件（需要调试器）
python -c "from tools.backends.pyocd_backend import PyOCDBackend; \
  PyOCDBackend().flash('firmware.hex', 'stm32f407vgtx')"
```

### 一键复制的完整示例

**场景：我有个STM32项目，想分析并生成LED代码**

```bash
# 复制这整段，替换路径后运行
PROJECT="C:/你的STM32项目路径"

# 1. 检查
python tools/hardware_butler.py doctor

# 2. 分析项目
python tools/hardware_butler.py onboard --root "$PROJECT"

# 3. 生成LED代码
python tools/hardware_butler.py firmware-plan --root "$PROJECT" --feature "gpio-led-blink"
python tools/hardware_butler.py firmware-patch --root "$PROJECT" --feature "gpio-led-blink" --write

echo "✅ 完成！查看生成的代码：$PROJECT/Core/Src/led_app.c"
```

---

## 🚀 进阶：解锁AI功能

### 为什么要用AI功能？

**不用AI**：只能用基础功能（已经很强大了）
**用AI**：解锁超能力 ⚡
- 🤖 对话式操作："帮我烧录固件"
- 📚 智能手册搜索：3秒找到答案
- 💡 更智能的建议

### 怎么开启AI？

**只需2步**：

**第1步：获取API Key**
1. 访问 https://console.anthropic.com
2. 注册账号（有免费额度）
3. 创建API Key
4. 复制Key（类似：`sk-ant-api03-xxx`）

**第2步：设置环境变量**

Windows PowerShell:
```powershell
$env:ANTHROPIC_API_KEY = "你的API-Key"
```

Windows CMD:
```cmd
set ANTHROPIC_API_KEY=你的API-Key
```

Mac/Linux:
```bash
export ANTHROPIC_API_KEY="你的API-Key"
```

**完成！** 现在AI功能可用了。

**测试一下**：
```bash
python tools/backends/langchain_agent.py "你好，列出所有功能"
```

---

## 📖 更多资源

### 新手友好的文档

1. **本文档** - 你正在看的，最简单
2. `docs/FEATURES_AND_USAGE.md` - 完整功能列表
3. `docs/CONFIGURATION.md` - 配置说明
4. `README.md` - 项目概览

### 按需查看

- **我想了解所有功能** → `docs/FEATURES_AND_USAGE.md`
- **我想配置高级选项** → `docs/CONFIGURATION.md`
- **我遇到错误了** → 运行 `hardware-butler doctor --verbose`
- **我想贡献代码** → `CONTRIBUTING.md`（待创建）

---

## 🎉 开始你的硬件Agent之旅！

**记住这3个命令就够了**：

```bash
# 1. 检查环境
hardware-butler doctor

# 2. 分析项目
hardware-butler onboard --root 你的项目

# 3. 查看帮助
hardware-butler --help
```

**其他的，慢慢探索就好！** 😊

---

## 💪 你能做到！

**不要被"AI"、"Agent"这些词吓到**

这就是一个**帮你省时间的工具**：
- ✅ 安装很简单（5分钟）
- ✅ 使用很简单（复制命令就行）
- ✅ 效果很明显（立刻看到结果）

**从第一个命令开始**：
```bash
python tools/hardware_butler.py doctor
```

**就是现在！** 🚀

---

**有问题？** 别担心，这很正常！

**下一步**：
1. 安装试试看
2. 运行第一个命令
3. 有问题就看本文档的"常见问题"部分

**Good luck！你会喜欢上它的** ❤️
