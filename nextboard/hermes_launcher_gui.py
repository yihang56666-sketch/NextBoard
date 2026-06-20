import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

BASE_DIR = Path(r"D:\hermes")
HERMES_HOME = BASE_DIR / "data"
HERMES_EXE = BASE_DIR / "venv" / "Scripts" / "hermes.exe"
ENV_FILE = HERMES_HOME / ".env"

DAILY_DIR = Path(r"C:\Users\35182\ai-research-daily")
DAILY_APP = DAILY_DIR / "app.py"
DAILY_COLLECT = DAILY_DIR / "collect.py"
DAILY_CACHE = DAILY_DIR / "data_cache.json"


DEFAULT_PROMPT = """任务：生成一份中文简报，主题是“今天最新、最近爆火或增长很快的 GitHub 开源项目”。

关注方向：
- AI Agent、LLM、RAG、强化学习、神经网络、多模态、机器人、开发者工具。
- 优先找新发布、近期更新、今日/本周热度明显上升的项目。
- 不要直接搬运 README 原文。

优先检查来源：
- GitHub Trending daily
- GitHub 搜索：近期创建并按 star 排序的仓库
- Hacker News、Hugging Face、Papers with Code
- 作者官方博客、release notes 或项目主页

输出结构：
1. 必看
2. 可看
3. 观察中

每个项目必须包含：
- 项目名和 GitHub 链接
- 发布时间或最近更新时间；拿不到就写“不确定”
- star 数或增长信号；拿不到就写“不确定”
- 3 到 5 句中文简要解释：它是干什么的、为什么火、适合谁看

规则：
- 输出中文。
- 每条都要有来源链接。
- 不确定的信息必须明确标注“不确定”。
- 结合本地日报目录里的数据进行整理：
  C:\\Users\\35182\\ai-research-daily
"""


def load_env():
    values = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def save_env(updates):
    HERMES_HOME.mkdir(parents=True, exist_ok=True)
    lines = []
    seen = set()
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key = line.split("=", 1)[0].strip()
                if key in updates:
                    lines.append(f"{key}={updates[key]}")
                    seen.add(key)
                    continue
            lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def hermes_env():
    env = os.environ.copy()
    env["HERMES_HOME"] = str(HERMES_HOME)
    return env


def new_console(args, cwd=None, env=None):
    subprocess.Popen(
        args,
        cwd=str(cwd or Path.home()),
        env=env or os.environ.copy(),
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


def run_hermes(args):
    if not HERMES_EXE.exists():
        messagebox.showerror("Hermes missing", f"Not found:\n{HERMES_EXE}")
        return
    new_console(args, env=hermes_env())


class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("龙虾 + AI 前沿日报")
        self.geometry("940x720")
        self.minsize(820, 600)
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="龙虾 + AI 前沿日报", font=("Microsoft YaHei UI", 17, "bold")).pack(anchor="w")
        ttk.Label(
            root,
            text=f"龙虾本体: {HERMES_EXE}    日报目录: {DAILY_DIR}",
            foreground="#4b5563",
        ).pack(anchor="w", pady=(2, 12))

        cfg = ttk.LabelFrame(root, text="OpenAI 兼容 API 配置", padding=12)
        cfg.pack(fill="x")
        cfg.columnconfigure(1, weight=1)

        ttk.Label(cfg, text="API Key").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)
        self.api_key = ttk.Entry(cfg, show="*")
        self.api_key.grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(cfg, text="Base URL").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=4)
        self.base_url = ttk.Entry(cfg)
        self.base_url.grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(cfg, text="模型名").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=4)
        self.model = ttk.Entry(cfg)
        self.model.grid(row=2, column=1, sticky="ew", pady=4)

        hermes_buttons = ttk.LabelFrame(root, text="龙虾控制", padding=10)
        hermes_buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(hermes_buttons, text="保存配置", command=self.save_config).pack(side="left", padx=(0, 8))
        ttk.Button(hermes_buttons, text="启动龙虾", command=self.start_hermes).pack(side="left", padx=(0, 8))
        ttk.Button(hermes_buttons, text="运行 doctor", command=self.run_doctor).pack(side="left", padx=(0, 8))
        ttk.Button(hermes_buttons, text="打开 .env", command=self.open_env).pack(side="left", padx=(0, 8))

        daily_buttons = ttk.LabelFrame(root, text="AI 前沿日报流程", padding=10)
        daily_buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(daily_buttons, text="启动日报界面", command=self.start_daily_app).pack(side="left", padx=(0, 8))
        ttk.Button(daily_buttons, text="刷新数据", command=self.refresh_daily_data).pack(side="left", padx=(0, 8))
        ttk.Button(daily_buttons, text="打开日报目录", command=self.open_daily_folder).pack(side="left", padx=(0, 8))
        ttk.Button(daily_buttons, text="打开缓存", command=self.open_daily_cache).pack(side="left")

        prompt_box = ttk.LabelFrame(root, text="最新热门 GitHub 项目提示词", padding=12)
        prompt_box.pack(fill="both", expand=True, pady=(12, 0))
        self.prompt = scrolledtext.ScrolledText(prompt_box, wrap="word", height=18, font=("Consolas", 10))
        self.prompt.pack(fill="both", expand=True)
        self.prompt.insert("1.0", DEFAULT_PROMPT)

        prompt_buttons = ttk.Frame(root)
        prompt_buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(prompt_buttons, text="复制提示词", command=self.copy_prompt).pack(side="left", padx=(0, 8))
        ttk.Button(prompt_buttons, text="启动龙虾并手动粘贴", command=self.start_hermes).pack(side="left", padx=(0, 8))
        ttk.Button(prompt_buttons, text="重置提示词", command=self.reset_prompt).pack(side="left")

        ttk.Label(
            root,
            text="推荐流程：先点“刷新数据”，再点“启动日报界面”。龙虾主要用于解释、分级和润色总结。",
            foreground="#374151",
        ).pack(anchor="w", pady=(10, 0))

    def _load_values(self):
        values = load_env()
        self.api_key.insert(0, values.get("OPENAI_API_KEY", ""))
        self.base_url.insert(0, values.get("OPENAI_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1"))
        self.model.insert(0, values.get("OPENAI_MODEL", "mimo-v2.5-pro"))

    def save_config(self):
        save_env(
            {
                "OPENAI_API_KEY": self.api_key.get().strip(),
                "OPENAI_BASE_URL": self.base_url.get().strip(),
                "OPENAI_API_BASE": self.base_url.get().strip(),
                "OPENAI_MODEL": self.model.get().strip(),
                "TERMINAL_ENV": "local",
            }
        )
        messagebox.showinfo("已保存", f"配置已写入：\n{ENV_FILE}")

    def start_hermes(self):
        self.save_config()
        run_hermes([str(HERMES_EXE)])

    def run_doctor(self):
        run_hermes([str(HERMES_EXE), "doctor"])

    def open_env(self):
        HERMES_HOME.mkdir(parents=True, exist_ok=True)
        ENV_FILE.touch(exist_ok=True)
        subprocess.Popen(["notepad.exe", str(ENV_FILE)])

    def start_daily_app(self):
        if not DAILY_APP.exists():
            messagebox.showerror("找不到日报界面", f"未找到：\n{DAILY_APP}")
            return
        new_console(["python", str(DAILY_APP)], cwd=DAILY_DIR)

    def refresh_daily_data(self):
        if not DAILY_COLLECT.exists():
            messagebox.showerror("找不到采集脚本", f"未找到：\n{DAILY_COLLECT}")
            return
        new_console(["python", str(DAILY_COLLECT)], cwd=DAILY_DIR)

    def open_daily_folder(self):
        DAILY_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer.exe", str(DAILY_DIR)])

    def open_daily_cache(self):
        if DAILY_CACHE.exists():
            subprocess.Popen(["notepad.exe", str(DAILY_CACHE)])
        else:
            messagebox.showwarning("缓存不存在", f"请先点击“刷新数据”：\n{DAILY_CACHE}")

    def copy_prompt(self):
        text = self.prompt.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("已复制", "提示词已复制。请粘贴到龙虾窗口。")

    def reset_prompt(self):
        self.prompt.delete("1.0", "end")
        self.prompt.insert("1.0", DEFAULT_PROMPT)


if __name__ == "__main__":
    if sys.platform != "win32":
        raise SystemExit("This launcher is intended for Windows.")
    Launcher().mainloop()
