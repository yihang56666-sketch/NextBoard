# 硬件Agent完整功能清单和使用手册

## 📋 目录

1. [核心功能](#核心功能)
2. [快速开始](#快速开始)
3. [详细功能说明](#详细功能说明)
4. [命令参考](#命令参考)
5. [API参考](#api参考)
6. [使用示例](#使用示例)

---

## 核心功能

### 🎯 主要能力

| 功能分类 | 功能点 | 状态 | 命令/模块 |
|----------|--------|------|-----------|
| **项目管理** | 项目onboarding | ✅ | `hardware-butler onboard` |
| | 项目检查 | ✅ | `hardware-butler inspect` |
| | 项目状态 | ✅ | `hardware-butler status` |
| | 环境检查 | ✅ | `hardware-butler doctor` |
| **CubeMX配置** | 检测CubeMX项目 | ✅ | `hardware-butler detect` |
| | 引脚配置建议 | ✅ | `hardware-butler advise-pin` |
| | .ioc文件修改 | ✅ | `hardware-butler patch-ioc` |
| **芯片资料** | 芯片档案创建 | ✅ | `hardware-butler chip-dossier` |
| | 手册摘要 | ✅ | `hardware-butler summarize-manual` |
| | **AI手册搜索** | ✅ | `chip_manual_rag.py` |
| **固件开发** | 意图规划 | ✅ | `hardware-butler firmware-plan` |
| | 代码生成 | ✅ | `hardware-butler firmware-patch` |
| | CubeMX集成 | ✅ | `hardware-butler firmware-integrate` |
| **构建系统** | 构建计划生成 | ✅ | `hardware-butler plan-build` |
| | 安全执行 | ✅ | `hardware-butler run-plan` |
| | 配置提案 | ✅ | `hardware-butler propose-config` |
| | 日志分类 | ✅ | `hardware-butler classify-log` |
| **硬件操作** | 动作计划 | ✅ | `hardware-butler plan-action` |
| | **真实Flash** | ✅ | `pyocd_backend.py` |
| | **内存读写** | ✅ | `pyocd_backend.py` |
| | **目标复位** | ✅ | `pyocd_backend.py` |
| | 安全审计 | ✅ | `hardware-butler safety-audit` |
| **测试** | 单元测试 | ✅ | `pytest tests/unit/` |
| | 集成测试 | ✅ | `pytest tests/` |
| | **硬件测试** | ✅ | `pytest tests/hardware/` |
| **AI增强** | **自然语言控制** | ✅ | `langchain_agent.py` |
| | **语义手册搜索** | ✅ | `chip_manual_rag.py` |
| | **对话式操作** | ✅ | LangChain Agent |

---

## 快速开始

### 安装

```bash
# 1. 克隆项目
git clone <hardware-agent-repo>
cd hardware-agent

# 2. 安装依赖
pip install -r requirements.txt

# 3. (可选) 安装开发依赖
pip install -r requirements-dev.txt

# 4. 设置环境变量（AI功能需要）
export ANTHROPIC_API_KEY="your-api-key"
export HW_BUTLER_ROOT="$(pwd)"
```

### 第一次使用

```bash
# 1. 检查环境
python tools/hardware_butler.py doctor

# 2. Onboard一个项目
python tools/hardware_butler.py onboard --root /path/to/stm32-project

# 3. 查看项目状态
python tools/hardware_butler.py status --root /path/to/stm32-project

# 4. (可选) 列出调试器
python -c "from tools.backends.pyocd_backend import PyOCDBackend; \
  backend = PyOCDBackend(); \
  probes = backend.list_probes(); \
  print(f'Found {len(probes)} probe(s)')"
```

---

## 详细功能说明

### 1️⃣ 项目管理

#### 1.1 项目Onboarding

**功能**: 自动分析项目，生成结构化文档

```bash
python tools/hardware_butler.py onboard \
  --root /path/to/project \
  --out-dir docs/inspections/my-project
```

**输出**:
- `project-dossier.md` - 项目总览
- `board-profile.md` - 板级配置
- `firmware-profile.md` - 固件架构
- `build-plan.json` - 构建计划

#### 1.2 项目检查

**功能**: 深度检查项目结构

```bash
python tools/hardware_butler.py inspect \
  --root /path/to/project \
  --out-dir docs/inspections/my-project
```

#### 1.3 环境检查

**功能**: 检查工具链、Python环境、路径权限

```bash
python tools/hardware_butler.py doctor --json
```

**输出示例**:
```json
{
  "status": "ok",
  "checks": [
    {"name": "python.version", "status": "ok", "message": "3.13.12"},
    {"name": "core.file:tools/hardware_butler.py", "status": "ok"}
  ]
}
```

---

### 2️⃣ CubeMX配置管理

#### 2.1 检测CubeMX项目

```bash
python tools/hardware_butler.py detect --root /path/to/project
```

**输出**:
```json
{
  "has_cubemx": true,
  "ioc_path": "project.ioc",
  "mcu": "STM32F407VGTx",
  "selected_backend": {"backend": "keil", "score": 100}
}
```

#### 2.2 引脚配置建议

```bash
python tools/hardware_butler.py advise-pin \
  --root /path/to/project \
  --pin PB6 \
  --function i2c
```

**输出**:
```json
{
  "pin": "PB6",
  "recommended_mode": "I2C1_SCL",
  "alternate_function": "AF4",
  "conflicts": [],
  "risks": ["需要配置上拉电阻"]
}
```

#### 2.3 修改.ioc文件

```bash
python tools/hardware_butler.py patch-ioc \
  --root /path/to/project \
  --pin PB7 \
  --mode I2C1_SDA \
  --write
```

---

### 3️⃣ 芯片资料管理

#### 3.1 创建芯片档案

```bash
python tools/hardware_butler.py chip-dossier \
  --part STM32F407VGTx \
  --board "MyBoard-V1" \
  --out-dir docs/chip/STM32F407VG
```

**输出**:
- `dossier.json` - 结构化档案
- `dossier.md` - Markdown文档
- `documents/` - 下载的PDF
- `summaries/` - 手册摘要骨架

#### 3.2 手册摘要

```bash
python tools/hardware_butler.py summarize-manual \
  --pdf docs/chip/STM32F407/datasheet.pdf \
  --part STM32F407VG \
  --out summary.md
```

#### 3.3 AI手册搜索 🆕

```bash
# Python API
python -c "
from pathlib import Path
from tools.backends.chip_manual_rag import ChipManualRAG

rag = ChipManualRAG(Path('docs/chip/STM32F407'))
result = rag.query('如何配置I2C1的时钟频率？')
print(result['answer'])
"

# 或直接运行
python tools/backends/chip_manual_rag.py \
  docs/chip/STM32F407 \
  "I2C1的SCL和SDA应该配置为什么模式？"
```

**功能**:
- ✅ 语义搜索（不只是关键词）
- ✅ 支持PDF/Markdown/文本
- ✅ 自动构建向量索引
- ✅ 缓存索引（7天）
- ✅ 置信度评分
- ✅ 来源引用

---

### 4️⃣ 固件开发

#### 4.1 意图规划

```bash
python tools/hardware_butler.py firmware-plan \
  --root /path/to/project \
  --feature "i2c-sensor-read" \
  --pin PB6
```

**输出**:
```json
{
  "feature": "i2c-sensor-read",
  "implementation_steps": [
    "配置I2C1外设（PB6=SCL, PB7=SDA）",
    "创建sensor_app.c模块",
    "添加读取函数到main.c"
  ],
  "rtos_enabled": true,
  "app_module_name": "sensor_app"
}
```

#### 4.2 代码生成

```bash
python tools/hardware_butler.py firmware-patch \
  --root /path/to/project \
  --feature "gpio-led-blink" \
  --write
```

**生成**:
- `Core/Src/led_app.c`
- `Core/Inc/led_app.h`
- 修改 `main.c` (USER CODE区域)

#### 4.3 CubeMX集成

```bash
python tools/hardware_butler.py firmware-integrate \
  --root /path/to/project \
  --feature "uart-debug" \
  --write
```

---

### 5️⃣ 构建系统

#### 5.1 生成构建计划

```bash
python tools/hardware_butler.py plan-build \
  --root /path/to/project \
  --markdown
```

**输出示例**:
```markdown
# Build Plan

Backend: keil

## Steps
1. **Inspect** - `python tools/hardware_butler_inspect.py`
2. **Build** - `uvision -b project.uvprojx -j0`
3. **Size** - `fromelf --text -z project.axf`
```

#### 5.2 执行构建

```bash
python tools/hardware_butler.py run-plan \
  --root /path/to/project \
  --phase build
```

#### 5.3 配置提案

```bash
python tools/hardware_butler.py propose-config \
  --root /path/to/project \
  --write
```

**生成**: `.embeddedskills/config.json`

---

### 6️⃣ 硬件操作

#### 6.1 动作计划（安全门控）

```bash
python tools/hardware_butler.py plan-action \
  --root /path/to/project \
  --action flash \
  --artifact build/firmware.hex \
  --target STM32F407VGTx \
  --probe "J-Link 123456"
```

**输出**: 包含确认token的计划

#### 6.2 真实硬件Flash 🆕

```python
# Python API
from tools.backends.pyocd_backend import PyOCDBackend

backend = PyOCDBackend(target_override="stm32f407vgtx")

# 列出调试器
probes = backend.list_probes()
for probe in probes:
    print(f"{probe.product_name} - {probe.unique_id}")

# Flash固件
result = backend.flash(
    firmware_path="build/firmware.hex",
    target="stm32f407vgtx",
    verify=True
)

if result.success:
    print(f"✅ Flashed {result.bytes_written} bytes in {result.duration_ms}ms")
else:
    print(f"❌ Failed: {result.error}")

# 读内存
data = backend.read_memory(address=0x08000000, count=256)

# 复位
backend.reset()
```

**支持的调试器**:
- J-Link (所有型号)
- ST-Link V2/V3
- CMSIS-DAP
- DAPLink

---

### 7️⃣ 测试

#### 7.1 单元测试

```bash
# 运行所有单元测试
pytest tests/unit/ -v

# 运行特定测试
pytest tests/unit/test_logger.py -v

# 带覆盖率
pytest tests/unit/ --cov=tools --cov-report=html
```

#### 7.2 集成测试

```bash
# 运行所有测试
python tests/validate_hardware_butler.py

# 特定fixture
pytest tests/ -k "cubemx"
```

#### 7.3 硬件测试 🆕

```bash
# Mock模式（无硬件）
pytest tests/hardware/ -v

# 真实硬件模式
pytest tests/hardware/ -v \
  --target=stm32f407vgtx \
  --port=COM3 \
  -m hardware
```

**测试示例**:
```python
# tests/hardware/test_my_board.py
import pytest

@pytest.mark.hardware
def test_led_blink(dut):
    """Test LED control."""
    dut.write('led on')
    dut.expect('LED ON', timeout=1)

    dut.write('led off')
    dut.expect('LED OFF', timeout=1)
```

---

### 8️⃣ AI增强功能 🆕

#### 8.1 自然语言操作

```bash
# CLI方式
python tools/backends/langchain_agent.py "列出所有连接的调试器"

python tools/backends/langchain_agent.py "烧录固件firmware.hex到STM32F407"

python tools/backends/langchain_agent.py "查询STM32F407的I2C配置方法"
```

```python
# Python API
from pathlib import Path
from tools.backends.langchain_agent import HardwareAgent

agent = HardwareAgent(workspace_root=Path("."))

# 复杂任务
result = agent.run("""
请执行以下操作：
1. 检查是否有调试器连接
2. 如果有，烧录firmware.hex到stm32f407vgtx
3. 然后查询芯片手册中关于I2C1配置的信息
""")

print(result)
```

**可用工具**:
- `OnboardProject` - 项目onboard
- `FlashFirmware` - 烧录固件
- `QueryChipManual` - 查询手册
- `ListProbes` - 列出调试器
- `BuildProject` - 构建项目

#### 8.2 语义手册搜索

```python
from pathlib import Path
from tools.backends.chip_manual_rag import ChipManualRAG

# 初始化
rag = ChipManualRAG(Path("docs/chip/STM32F407"))

# 第一次会构建索引（可能需要几分钟）
rag.build_index()

# 查询
result = rag.query("I2C1的最大时钟频率是多少？")
print(f"Answer: {result['answer']}")
print(f"Confidence: {result['confidence']:.2%}")
print(f"Sources: {len(result['sources'])} documents")

# 芯片摘要
summary = rag.summarize_chip("STM32F407VG")
print(summary['sections']['peripherals']['answer'])
```

---

## 命令参考

### 完整命令列表

```bash
hardware-butler <command> [options]

Commands:
  # 项目管理
  onboard              项目onboarding（完整分析）
  inspect              项目检查（深度扫描）
  status               项目状态
  doctor               环境健康检查
  capabilities         显示功能矩阵

  # CubeMX
  detect               检测CubeMX项目
  advise-pin           引脚配置建议
  patch-ioc            修改.ioc文件

  # 芯片资料
  chip-dossier         创建芯片档案
  summarize-manual     手册摘要生成

  # 固件开发
  firmware-plan        固件意图规划
  firmware-patch       固件代码生成
  firmware-integrate   固件CubeMX集成

  # 构建
  plan-build           生成构建计划
  run-plan             执行构建计划
  propose-config       配置提案
  classify-log         构建日志分类

  # 硬件操作
  plan-action          硬件动作计划
  execute-action       执行硬件动作
  safety-audit         安全审计
  bench-runbook        生成bench手册

Options:
  --root PATH          项目根目录
  --out-dir PATH       输出目录
  --json               JSON格式输出
  --markdown           Markdown格式输出
  --write              实际写入（vs 预览）
  --help               帮助信息
```

---

## API参考

### Python API

#### PyOCD Backend

```python
from tools.backends.pyocd_backend import PyOCDBackend, FlashResult

# 初始化
backend = PyOCDBackend(target_override="stm32f407vgtx")

# 列出调试器
probes: list[ProbeInfo] = backend.list_probes()

# Flash
result: FlashResult = backend.flash(
    firmware_path="fw.hex",
    target="stm32f407vgtx",
    erase=True,
    verify=True
)

# 读内存
data: bytes = backend.read_memory(address=0x08000000, count=256)

# 复位
success: bool = backend.reset()
```

#### Chip Manual RAG

```python
from tools.backends.chip_manual_rag import ChipManualRAG

# 初始化
rag = ChipManualRAG(
    chip_docs_dir=Path("docs/chip/STM32F407"),
    cache_dir=Path(".index_cache")  # 可选
)

# 构建索引
rag.build_index(force_rebuild=False)

# 查询
result: dict = rag.query(question="I2C配置方法", top_k=3)
# result = {
#     "question": "...",
#     "answer": "...",
#     "sources": [...],
#     "confidence": 0.85
# }

# 芯片摘要
summary: dict = rag.summarize_chip("STM32F407VG")
```

#### LangChain Agent

```python
from tools.backends.langchain_agent import HardwareAgent

# 初始化
agent = HardwareAgent(
    workspace_root=Path("."),
    api_key="your-anthropic-key"  # 或从环境变量
)

# 执行任务
result: str = agent.run("列出连接的调试器并烧录固件")
```

---

## 使用示例

### 示例1: 完整开发流程

```bash
#!/bin/bash
# 新项目完整流程

PROJECT="/path/to/stm32-project"

# 1. Onboard项目
python tools/hardware_butler.py onboard --root "$PROJECT"

# 2. 检测CubeMX
python tools/hardware_butler.py detect --root "$PROJECT"

# 3. 配置I2C引脚
python tools/hardware_butler.py advise-pin \
  --root "$PROJECT" \
  --pin PB6 \
  --function i2c

# 4. 生成I2C传感器代码
python tools/hardware_butler.py firmware-plan \
  --root "$PROJECT" \
  --feature "i2c-sensor-read"

python tools/hardware_butler.py firmware-patch \
  --root "$PROJECT" \
  --feature "i2c-sensor-read" \
  --write

# 5. 构建
python tools/hardware_butler.py run-plan \
  --root "$PROJECT" \
  --phase build

# 6. Flash（使用PyOCD）
python -c "
from tools.backends.pyocd_backend import PyOCDBackend
backend = PyOCDBackend()
result = backend.flash('$PROJECT/build/firmware.hex', 'stm32f407vgtx')
print('Flash:', 'OK' if result.success else 'FAILED')
"

# 7. 测试
pytest tests/hardware/ --target=stm32f407vgtx --port=COM3 -m hardware
```

### 示例2: AI辅助开发

```python
from pathlib import Path
from tools.backends.langchain_agent import HardwareAgent
from tools.backends.chip_manual_rag import ChipManualRAG

# 1. 创建AI agent
agent = HardwareAgent(workspace_root=Path("."))

# 2. 对话式开发
agent.run("""
我有一个STM32F407的项目，需要：
1. 添加I2C1外设读取温度传感器
2. 配置PB6和PB7为I2C功能
3. 生成相应的代码
请帮我完成这些操作
""")

# 3. 查询芯片手册
rag = ChipManualRAG(Path("docs/chip/STM32F407"))
result = rag.query("I2C1的DMA配置方法")
print(result['answer'])

# 4. 烧录和测试
agent.run("烧录固件并通过串口验证I2C功能是否正常")
```

### 示例3: 批量项目分析

```python
from pathlib import Path
import hardware_butler_inspect

projects = [
    "/path/to/project1",
    "/path/to/project2",
    "/path/to/project3",
]

for project in projects:
    print(f"Analyzing {project}...")

    result = hardware_butler_inspect.inspect_project(
        Path(project),
        Path("docs/inspections") / Path(project).name
    )

    print(f"  MCU: {result.get('mcu', 'Unknown')}")
    print(f"  Backend: {result.get('backend', 'Unknown')}")
    print(f"  Has CubeMX: {result.get('has_cubemx', False)}")
    print()
```

### 示例4: 硬件测试自动化

```python
# tests/hardware/test_production.py
import pytest

@pytest.mark.hardware
class TestProductionBoard:
    """生产测试套件"""

    def test_power_on(self, dut):
        """测试上电"""
        dut.expect("Boot OK", timeout=2)

    def test_leds(self, dut):
        """测试LED"""
        for led in ['RED', 'GREEN', 'BLUE']:
            dut.write(f'led {led} on')
            dut.expect(f'{led} ON', timeout=1)

    def test_uart(self, dut):
        """测试UART回环"""
        test_data = "HELLO"
        dut.write(test_data)
        dut.expect(test_data, timeout=1)

    def test_i2c_sensor(self, dut):
        """测试I2C传感器"""
        dut.write('read_temp')
        dut.expect('Temperature:', timeout=2)
```

运行：
```bash
pytest tests/hardware/test_production.py \
  --target=stm32f407vgtx \
  --port=COM3 \
  -v -m hardware
```

---

## 常见问题

### Q: 如何开始使用？
A: 先运行 `hardware-butler doctor` 检查环境，然后 `onboard` 你的第一个项目。

### Q: 需要哪些硬件？
A: 基本功能不需要硬件。真实Flash需要J-Link/ST-Link等调试器。

### Q: AI功能需要什么？
A: 需要设置 `ANTHROPIC_API_KEY` 环境变量。

### Q: 如何贡献？
A: 查看 `CONTRIBUTING.md`（待创建）。

---

## 下一步

1. ✅ 安装依赖
2. ✅ 运行 `doctor` 检查环境
3. ✅ Onboard你的第一个项目
4. ✅ 尝试AI手册搜索
5. ✅ （可选）连接调试器并Flash

---

**完整文档**: 查看 `docs/` 目录下的所有Markdown文件

**需要帮助?**: 提交Issue到项目仓库
