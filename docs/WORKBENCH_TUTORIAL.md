# 硬件管家工作台教程

硬件管家工作台把项目检测、环境检查、安全入驻、报告生成、下一步推荐和台架准备连到一个界面里。日常使用时优先打开工作台，只有高级功能才回到 CLI。

## 1. 从源码启动

先安装依赖：

```powershell
pip install -r requirements.txt
```

启动工作台：

```powershell
python gui\hardware_agent_ui.py
```

启动后会自动刷新当前工作区。你也可以点 `浏览`，选择自己的 CubeMX、Keil、CMake 或 EIDE 项目根目录。

## 2. 打包成 exe

确保已经安装 PyInstaller，或者机器上能找到 `pyinstaller.exe`：

```powershell
pip install pyinstaller
```

运行打包脚本：

```powershell
python tools\build_workbench_exe.py
```

打包后会生成两个目录：

```text
dist\HardwareButlerWorkbench\HardwareButlerWorkbench.exe
dist\hardware_butler_cli\hardware_butler_cli.exe
```

打开 GUI：

```powershell
Start-Process dist\HardwareButlerWorkbench\HardwareButlerWorkbench.exe
```

注意：这两个 `dist` 子目录要放在一起。GUI exe 会自动寻找旁边的 CLI exe 作为后端。

## 3. 每天怎么用

1. 打开工作台。
2. 在顶部选择项目根目录。
3. 点 `刷新`，查看状态卡、流程表、动作表和报告表。
4. 如果不确定下一步，点 `运行推荐`。
5. 如果你知道要做什么，在动作表里选一行，再点 `运行所选`。
6. 右侧报告表会显示入驻清单、项目档案、板卡画像、固件画像、构建计划、配置提案等报告是否已经生成。

工作台会把命令摘要显示在底部输出区。JSON 细节仍由后端保存到项目和报告目录中。

## 4. 按钮对应关系

| 界面动作 | 作用 | 后端命令 |
| --- | --- | --- |
| 刷新 | 重新读取项目状态 | `workbench` |
| 运行推荐 | 执行当前建议的安全动作 | 来自 `primary_action` |
| 运行所选 | 执行动作表中选中的安全动作 | 来自 `actions` |
| 自动分析 | 必要时生成项目报告并更新状态 | `auto` |
| 检查环境 | 检查本地工具和产品就绪状态 | `doctor` |
| 检测项目 | 检测 CubeMX 元数据和构建后端 | `detect` |
| 准备台架手册 | 生成不触碰硬件的台架 runbook | `bench-runbook` |
| 查看安全审计 | 查看硬件动作审计摘要 | `safety-audit` |

## 5. 安全边界

工作台默认只跑安全本地动作。它不会直接烧录、擦除、复位、在线调试、长时间观测、发送总线帧或扫描网络。

真实硬件动作仍然是 `planned-gated`：需要动作计划、确认 token、设备身份、电压电流证据、产物 hash 和回滚记录。这个边界是为了避免误烧、误擦和误连硬件。

## 6. 高级 CLI 能力

下面这些能力已经在项目里，但还没有独立 GUI 向导：

```powershell
python tools\hardware_butler.py chip-dossier --part STM32F407VGTx --json
python tools\hardware_butler.py advise-pin --root <project-root> --pin PB7 --function i2c --json
python tools\hardware_butler.py patch-ioc --root <project-root> --function i2c --instance I2C1 --scl PB6 --sda PB7 --json
python tools\hardware_butler.py firmware-plan --root <project-root> --feature i2c-sensor-read --json
python tools\hardware_butler.py firmware-patch --root <project-root> --feature i2c-sensor-read --json
python tools\hardware_butler.py classify-log <build-log.txt> --json
```

完整覆盖情况见 `docs\WORKBENCH_FEATURE_COVERAGE.md`。

## 7. 常见问题

| 问题 | 处理 |
| --- | --- |
| 启动源码 GUI 提示缺 PyQt6 | 运行 `pip install -r requirements.txt` |
| 打包脚本提示找不到 PyInstaller | 运行 `pip install pyinstaller` |
| 工作台显示未检测到后端 | 先确认项目根目录选对，里面应有 `.ioc`、`.uvprojx`、`CMakeLists.txt` 或 EIDE 工程文件 |
| 报告表显示缺失 | 点 `运行推荐` 或 `自动分析` 生成安全入驻报告 |
| exe 打开后动作运行失败 | 确认 `dist\HardwareButlerWorkbench` 和 `dist\hardware_butler_cli` 两个目录仍放在同一个 `dist` 目录下 |
| 需要真实烧录或调试 | 先用 `bench-runbook` 和 `plan-action` 生成计划，再按确认 token 流程执行，不要绕过门控 |
