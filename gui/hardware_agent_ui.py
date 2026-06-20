"""Web3-style GUI for Hardware Agent.

Features:
- Modern glassmorphism design
- Gradient backgrounds
- Neon accents
- Card-based layout
- Responsive and interactive
"""

import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class WorkerThread(QThread):
    """Background worker for running commands."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, argv, project_root=None):
        super().__init__()
        # argv MUST be a list of arguments. shell=True with interpolated user
        # input is forbidden here: it allowed arbitrary command execution from
        # GUI text fields and bypassed the project's safety-gate architecture.
        if not isinstance(argv, (list, tuple)):
            raise TypeError("WorkerThread requires an argv list, not a shell string")
        self.argv = list(argv)
        self.project_root = project_root

    def run(self):
        try:
            import subprocess
            result = subprocess.run(
                self.argv,
                shell=False,
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )
            if result.returncode == 0:
                self.finished.emit(result.stdout)
            else:
                self.error.emit(result.stderr)
        except Exception as e:
            self.error.emit(str(e))


class GlassCard(QFrame):
    """Glassmorphism card widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                backdrop-filter: blur(10px);
            }
        """)


class HardwareAgentUI(QMainWindow):
    """Main UI window with Web3 styling."""

    def __init__(self):
        super().__init__()
        self.project_root = None
        self.init_ui()

    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("硬件助手 🚀 Hardware Agent")
        self.setGeometry(100, 100, 1200, 800)

        # Set dark theme with gradient
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0a0e27, stop:0.5 #1a1f3a, stop:1 #0a0e27
                );
            }
            QLabel {
                color: #ffffff;
                font-family: 'Segoe UI', Arial;
            }
            QPushButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2
                );
                color: white;
                border: none;
                border-radius: 12px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #764ba2, stop:1 #667eea
                );
            }
            QPushButton:pressed {
                background: #5a4d7a;
            }
            QLineEdit, QTextEdit, QComboBox {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px;
                color: white;
                font-size: 13px;
            }
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                background: rgba(255, 255, 255, 0.02);
            }
            QTabBar::tab {
                background: rgba(255, 255, 255, 0.05);
                color: white;
                padding: 12px 24px;
                border-radius: 8px 8px 0 0;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2
                );
            }
        """)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = self.create_header()
        layout.addWidget(header)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self.create_quick_start_tab(), "⚡ 快速开始")
        tabs.addTab(self.create_project_tab(), "📁  项目管理")
        tabs.addTab(self.create_ai_tab(), "🤖 AI工具")
        tabs.addTab(self.create_hardware_tab(), "🔧 硬件操作")
        layout.addWidget(tabs)

        # Status bar
        self.status = QLabel("就绪")
        self.status.setStyleSheet("color: #00ff88; padding: 8px;")
        layout.addWidget(self.status)

    def create_header(self):
        """Create header with logo and project selector."""
        header = GlassCard()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 15, 20, 15)

        # Logo
        logo = QLabel("🛠️ 硬件助手")
        logo.setStyleSheet("font-size: 24px; font-weight: bold; color: #667eea;")
        layout.addWidget(logo)

        layout.addStretch()

        # Project selector
        self.project_input = QLineEdit()
        self.project_input.setPlaceholderText("项目路径...")
        self.project_input.setMinimumWidth(300)
        layout.addWidget(self.project_input)

        browse_btn = QPushButton("📂 浏览")
        browse_btn.clicked.connect(self.browse_project)
        layout.addWidget(browse_btn)

        return header

    def create_quick_start_tab(self):
        """Quick start tab with common actions."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # Welcome card
        welcome = GlassCard()
        welcome_layout = QVBoxLayout(welcome)
        title = QLabel("👋 欢迎使用硬件助手")
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin: 15px;")
        welcome_layout.addWidget(title)

        subtitle = QLabel("AI驱动的硬件开发智能助手")
        subtitle.setStyleSheet("font-size: 14px; color: rgba(255,255,255,0.7); margin: 0 15px 15px 15px;")
        welcome_layout.addWidget(subtitle)
        layout.addWidget(welcome)

        # Quick actions grid
        actions_grid = QHBoxLayout()

        # Onboard button
        onboard_card = self.create_action_card(
            "📋 项目入驻",
            "自动分析和生成项目文档",
            self.onboard_project
        )
        actions_grid.addWidget(onboard_card)

        # Doctor button
        doctor_card = self.create_action_card(
            "🏥 环境检查",
            "检查开发环境和工具链",
            self.run_doctor
        )
        actions_grid.addWidget(doctor_card)

        # AI Search
        ai_card = self.create_action_card(
            "🔍 AI搜索",
            "智能搜索芯片手册",
            lambda: self.switch_to_tab(2)
        )
        actions_grid.addWidget(ai_card)

        layout.addLayout(actions_grid)

        # Output
        output_label = QLabel("📤 输出")
        output_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(output_label)

        self.quick_output = QTextEdit()
        self.quick_output.setReadOnly(True)
        self.quick_output.setPlaceholderText("命令输出将显示在这里...")
        layout.addWidget(self.quick_output)

        layout.addStretch()
        return tab

    def create_action_card(self, title, subtitle, action):
        """Create action button card."""
        card = GlassCard()
        card.setMinimumHeight(120)
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.6);")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)

        btn = QPushButton("运行")
        btn.clicked.connect(action)
        layout.addWidget(btn)

        return card

    def create_project_tab(self):
        """Project management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Project info card
        info_card = GlassCard()
        info_layout = QVBoxLayout(info_card)

        info_label = QLabel("📊 项目信息")
        info_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        info_layout.addWidget(info_label)

        self.project_info = QTextEdit()
        self.project_info.setReadOnly(True)
        self.project_info.setPlaceholderText("选择项目后显示信息...")
        info_layout.addWidget(self.project_info)

        layout.addWidget(info_card)

        # Actions
        actions = QHBoxLayout()

        inspect_btn = QPushButton("🔍 深度检查")
        inspect_btn.clicked.connect(self.inspect_project)
        actions.addWidget(inspect_btn)

        status_btn = QPushButton("📊 项目状态")
        status_btn.clicked.connect(self.project_status)
        actions.addWidget(status_btn)

        build_btn = QPushButton("⚙️ 构建计划")
        build_btn.clicked.connect(self.build_plan)
        actions.addWidget(build_btn)

        layout.addLayout(actions)

        return tab

    def create_ai_tab(self):
        """AI tools tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # AI search card
        search_card = GlassCard()
        search_layout = QVBoxLayout(search_card)

        title = QLabel("🤖 AI芯片手册搜索")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        search_layout.addWidget(title)

        self.ai_query = QLineEdit()
        self.ai_query.setPlaceholderText("问芯片相关问题（例如：'I2C1怎么配置？'）")
        search_layout.addWidget(self.ai_query)

        search_btn = QPushButton("🔍 AI搜索")
        search_btn.clicked.connect(self.ai_search)
        search_layout.addWidget(search_btn)

        self.ai_output = QTextEdit()
        self.ai_output.setReadOnly(True)
        self.ai_output.setPlaceholderText("AI回答将显示在这里...")
        search_layout.addWidget(self.ai_output)

        layout.addWidget(search_card)

        # Natural language control
        nl_card = GlassCard()
        nl_layout = QVBoxLayout(nl_card)

        nl_title = QLabel("💬 自然语言控制")
        nl_title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        nl_layout.addWidget(nl_title)

        self.nl_input = QLineEdit()
        self.nl_input.setPlaceholderText("告诉助手做什么（例如：'烧录固件到STM32F407'）")
        nl_layout.addWidget(self.nl_input)

        nl_btn = QPushButton("▶️ 执行")
        nl_btn.clicked.connect(self.nl_execute)
        nl_layout.addWidget(nl_btn)

        layout.addWidget(nl_card)

        return tab

    def create_hardware_tab(self):
        """Hardware operations tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Flash card
        flash_card = GlassCard()
        flash_layout = QVBoxLayout(flash_card)

        title = QLabel("⚡ 烧录固件")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        flash_layout.addWidget(title)

        # Firmware file
        fw_layout = QHBoxLayout()
        self.fw_path = QLineEdit()
        self.fw_path.setPlaceholderText("固件路径 (hex/bin)...")
        fw_layout.addWidget(self.fw_path)

        fw_browse = QPushButton("📂")
        fw_browse.clicked.connect(self.browse_firmware)
        fw_layout.addWidget(fw_browse)
        flash_layout.addLayout(fw_layout)

        # Target
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("目标芯片:"))
        self.target_combo = QComboBox()
        self.target_combo.addItems([
            "stm32f407vgtx",
            "stm32f103c8tx",
            "stm32h750vbtx",
            "自定义..."
        ])
        target_layout.addWidget(self.target_combo)
        flash_layout.addLayout(target_layout)

        # Flash button
        flash_btn = QPushButton("🚀 立即烧录")
        flash_btn.setStyleSheet(flash_btn.styleSheet() + """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f093fb, stop:1 #f5576c);
                padding: 15px;
                font-size: 16px;
            }
        """)
        flash_btn.clicked.connect(self.flash_firmware)
        flash_layout.addWidget(flash_btn)

        self.flash_output = QTextEdit()
        self.flash_output.setReadOnly(True)
        self.flash_output.setMaximumHeight(150)
        flash_layout.addWidget(self.flash_output)

        layout.addWidget(flash_card)

        # Probes card
        probes_card = GlassCard()
        probes_layout = QVBoxLayout(probes_card)

        probes_title = QLabel("🔌 已连接的调试器")
        probes_title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        probes_layout.addWidget(probes_title)

        self.probes_list = QTextEdit()
        self.probes_list.setReadOnly(True)
        self.probes_list.setMaximumHeight(100)
        probes_layout.addWidget(self.probes_list)

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.list_probes)
        probes_layout.addWidget(refresh_btn)

        layout.addWidget(probes_card)

        layout.addStretch()
        return tab

    def browse_project(self):
        """Browse for project directory."""
        path = QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if path:
            self.project_input.setText(path)
            self.project_root = path
            self.status.setText(f"📁 Project: {Path(path).name}")

    def browse_firmware(self):
        """Browse for firmware file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Firmware", "", "Firmware Files (*.hex *.bin *.elf)"
        )
        if path:
            self.fw_path.setText(path)

    def run_command(self, argv, output_widget):
        """Run command in background thread.

        argv must be a list of arguments (no shell). The displayed line is a
        best-effort human-readable join and is NOT what gets executed.
        """
        self.status.setText("⏳ Running...")
        display = " ".join(str(a) for a in argv)
        output_widget.append(f"$ {display}\n")

        worker = WorkerThread(argv, self.project_root)
        worker.finished.connect(lambda result: self.on_command_finished(result, output_widget))
        worker.error.connect(lambda error: self.on_command_error(error, output_widget))
        worker.start()

    def on_command_finished(self, result, output_widget):
        """Handle command completion."""
        output_widget.append(result)
        self.status.setText("✅ 完成")

    def on_command_error(self, error, output_widget):
        """Handle command error."""
        output_widget.append(f"❌ 错误: {error}")
        self.status.setText("❌ 错误")

    def onboard_project(self):
        """Onboard project."""
        if not self.project_root:
            self.quick_output.append("❌ Please select a project first\n")
            return

        cmd = [sys.executable, "tools/hardware_butler.py", "onboard",
               "--root", self.project_root]
        self.run_command(cmd, self.quick_output)

    def run_doctor(self):
        """Run health check."""
        cmd = [sys.executable, "tools/hardware_butler.py", "doctor", "--json"]
        self.run_command(cmd, self.quick_output)

    def inspect_project(self):
        """Inspect project."""
        if not self.project_root:
            self.project_info.append("❌ Please select a project first\n")
            return

        cmd = [sys.executable, "tools/hardware_butler.py", "inspect",
               "--root", self.project_root]
        self.run_command(cmd, self.project_info)

    def project_status(self):
        """Get project status."""
        if not self.project_root:
            self.project_info.append("❌ Please select a project first\n")
            return

        cmd = [sys.executable, "tools/hardware_butler.py", "status",
               "--root", self.project_root]
        self.run_command(cmd, self.project_info)

    def build_plan(self):
        """Generate build plan."""
        if not self.project_root:
            self.project_info.append("❌ Please select a project first\n")
            return

        cmd = [sys.executable, "tools/hardware_butler.py", "plan-build",
               "--root", self.project_root]
        self.run_command(cmd, self.project_info)

    def ai_search(self):
        """AI manual search."""
        query = self.ai_query.text()
        if not query:
            return

        cmd = [sys.executable, "tools/backends/chip_manual_rag.py",
               "docs/chip", query]
        self.run_command(cmd, self.ai_output)

    def nl_execute(self):
        """Natural language execution."""
        task = self.nl_input.text()
        if not task:
            return

        cmd = [sys.executable, "tools/backends/langchain_agent.py", task]
        self.run_command(cmd, self.ai_output)

    def flash_firmware(self):
        """Flash firmware.

        Real flashing is safety-gated and never performed directly from the
        GUI. We generate a confirmation-gated bench runbook through the
        hardware_butler CLI instead of calling a backend's flash() directly;
        a direct call would bypass the token gate and the project's
        planned-gated guarantee for real flash/debug/observe.
        """
        fw = self.fw_path.text()
        target = self.target_combo.currentText()

        if not fw:
            self.flash_output.append("❌ Please select firmware file\n")
            return
        if not self.project_root:
            self.flash_output.append("❌ Please select a project first\n")
            return

        self.flash_output.append(
            f"🔒 Real flash is safety-gated. Generating a no-hardware bench "
            f"runbook for {Path(fw).name} → {target}.\n"
            f"   Review it, then run the gated plan-action/execute-action "
            f"flow from the CLI to proceed.\n"
        )
        cmd = [sys.executable, "tools/hardware_butler.py", "bench-runbook",
               "--root", self.project_root,
               "--action", "build-flash",
               "--target", target,
               "--artifact", fw,
               "--json"]
        self.run_command(cmd, self.flash_output)

    def list_probes(self):
        """List connected probes (read-only discovery)."""
        cmd = [sys.executable, "-c",
               "from tools.backends.pyocd_backend import PyOCDBackend; "
               "probes = PyOCDBackend().list_probes(); "
               "print(f'Found {len(probes)} probe(s)'); "
               "[print(f'{p.product_name} - {p.unique_id}') for p in probes]"]
        self.run_command(cmd, self.probes_list)

    def switch_to_tab(self, index):
        """Switch to specific tab."""
        # Find tab widget
        tabs = self.centralWidget().findChild(QTabWidget)
        if tabs:
            tabs.setCurrentIndex(index)


def main():
    """Launch the GUI."""
    app = QApplication(sys.argv)

    # Set application font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = HardwareAgentUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
