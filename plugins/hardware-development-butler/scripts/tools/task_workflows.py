"""Intent-based safe task workflow plans for the hardware copilot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

INTENTS = {
    "collect-evidence": {
        "title": "整理资料",
        "description": "Refresh project brain and optionally collect chip documents.",
    },
    "analyze-hardware-risk": {
        "title": "分析原理图风险",
        "description": "Review missing board evidence and deterministic hardware risks.",
    },
    "configure-peripheral": {
        "title": "配置一个外设",
        "description": "Check pin evidence, plan firmware, and preview CubeMX changes.",
    },
    "diagnose-build-failure": {
        "title": "诊断构建失败",
        "description": "Classify a build log and regenerate the safe build plan.",
    },
    "prepare-bringup": {
        "title": "准备上板 bring-up",
        "description": "Generate evidence review and a no-hardware bench runbook.",
    },
}


def build_task_plan(
    root: Path,
    intent: str,
    *,
    part: str = "",
    pin: str = "",
    function: str = "",
    instance: str = "",
    log: str = "",
    question: str = "",
) -> dict[str, Any]:
    root = root.resolve()
    intent_id = intent if intent in INTENTS else "collect-evidence"
    context = {
        "part": part.strip(),
        "pin": pin.strip().upper(),
        "function": function.strip(),
        "instance": instance.strip().upper(),
        "log": log.strip(),
        "question": question.strip(),
    }
    steps, missing = intent_steps(str(root), intent_id, context)
    return {
        "schema_version": 1,
        "status": "needs-input" if missing else "ready",
        "root": str(root),
        "intent": {
            "id": intent_id,
            "title": INTENTS[intent_id]["title"],
            "description": INTENTS[intent_id]["description"],
        },
        "missing_inputs": missing,
        "steps": steps,
        "safety": {
            "safe_by_default": True,
            "touches_hardware": False,
            "real_hardware_actions": "planned-gated",
        },
        "next_actions": next_actions(intent_id, missing),
    }


def intent_steps(root: str, intent: str, context: dict[str, str]) -> tuple[list[dict[str, Any]], list[str]]:
    if intent == "collect-evidence":
        return collect_evidence_steps(root, context), []
    if intent == "analyze-hardware-risk":
        return risk_steps(root, context), []
    if intent == "configure-peripheral":
        return configure_peripheral_steps(root, context)
    if intent == "diagnose-build-failure":
        return diagnose_build_steps(root, context)
    if intent == "prepare-bringup":
        return prepare_bringup_steps(root, context), []
    return collect_evidence_steps(root, context), []


def collect_evidence_steps(root: str, context: dict[str, str]) -> list[dict[str, Any]]:
    steps = [
        step("brain", "刷新项目大脑", ["python", "tools/hardware_butler.py", "brain", "--root", root, "--json"]),
        step("inspect", "生成项目/板卡/固件报告", ["python", "tools/hardware_butler.py", "inspect", "--root", root, "--json"]),
    ]
    if context["part"]:
        steps.append(
            step(
                "chip-dossier",
                "搜索并整理芯片资料",
                [
                    "python",
                    "tools/hardware_butler.py",
                    "chip-dossier",
                    "--part",
                    context["part"],
                    "--api-search",
                    "--api-preset",
                    "chip-docs",
                    "--download",
                    "--json",
                ],
            )
        )
    return steps


def risk_steps(root: str, context: dict[str, str]) -> list[dict[str, Any]]:
    question = context["question"] or "这块板缺什么资料和硬件风险？"
    return [
        step("brain", "刷新项目大脑", ["python", "tools/hardware_butler.py", "brain", "--root", root, "--json"]),
        step("ask-risk", "基于证据回答风险问题", ["python", "tools/hardware_butler.py", "ask", "--root", root, "--question", question, "--json"]),
    ]


def configure_peripheral_steps(root: str, context: dict[str, str]) -> tuple[list[dict[str, Any]], list[str]]:
    missing = []
    if not context["function"]:
        missing.append("function")
    if not context["pin"] and context["function"] not in {"i2c", "spi", "uart", "can"}:
        missing.append("pin")
    if context["function"] in {"i2c", "spi", "uart", "can"} and not (context["pin"] or context["instance"]):
        missing.append("pin or instance")
    steps = [
        step("brain", "刷新项目大脑", ["python", "tools/hardware_butler.py", "brain", "--root", root, "--json"]),
    ]
    if context["pin"] and context["function"]:
        steps.append(
            step(
                "advise-pin",
                "检查 CubeMX 引脚配置建议",
                [
                    "python",
                    "tools/hardware_butler.py",
                    "advise-pin",
                    "--root",
                    root,
                    "--pin",
                    context["pin"],
                    "--function",
                    context["function"],
                    "--json",
                ],
            )
        )
    if context["function"]:
        firmware_args = [
            "python",
            "tools/hardware_butler.py",
            "firmware-plan",
            "--root",
            root,
            "--feature",
            f"{context['function']}-feature",
            "--function",
            context["function"],
            "--json",
        ]
        if context["pin"]:
            firmware_args.extend(["--pin", context["pin"]])
        steps.append(step("firmware-plan", "生成固件实现计划", firmware_args))
    return steps, missing


def diagnose_build_steps(root: str, context: dict[str, str]) -> tuple[list[dict[str, Any]], list[str]]:
    missing = [] if context["log"] else ["log"]
    steps = [
        step("plan-build", "重新生成安全构建计划", ["python", "tools/hardware_butler.py", "plan-build", "--root", root, "--json"])
    ]
    if context["log"]:
        steps.insert(
            0,
            step("classify-log", "分类构建日志", ["python", "tools/hardware_butler.py", "classify-log", context["log"], "--json"]),
        )
    return steps, missing


def prepare_bringup_steps(root: str, context: dict[str, str]) -> list[dict[str, Any]]:
    del context
    return [
        step("brain", "刷新项目大脑", ["python", "tools/hardware_butler.py", "brain", "--root", root, "--json"]),
        step(
            "bench-runbook",
            "生成不触碰硬件的上板手册",
            ["python", "tools/hardware_butler.py", "bench-runbook", "--root", root, "--action", "build-flash", "--json"],
        ),
        step(
            "plan-action",
            "生成确认门控动作计划",
            ["python", "tools/hardware_butler.py", "plan-action", "--root", root, "--action", "build-flash", "--json"],
        ),
    ]


def step(step_id: str, title: str, argv: list[str]) -> dict[str, Any]:
    return {
        "id": step_id,
        "title": title,
        "argv": argv,
        "command": " ".join(argv),
        "safe_by_default": True,
        "touches_hardware": False,
    }


def next_actions(intent: str, missing: list[str]) -> list[str]:
    if missing:
        return [f"Provide required input: {item}" for item in missing]
    if intent == "configure-peripheral":
        return ["Review advice and firmware plan before using patch-ioc or writing generated code."]
    if intent == "prepare-bringup":
        return ["Review runbook and action plan; real hardware remains confirmation-gated."]
    return ["Review every generated command before running it."]


def render_markdown(plan: dict[str, Any]) -> str:
    intent = plan.get("intent", {}) if isinstance(plan.get("intent"), dict) else {}
    lines = [
        "# Task Workflow",
        "",
        f"- Root: `{plan.get('root', '')}`",
        f"- Intent: {intent.get('title', 'unknown')}",
        f"- Status: `{plan.get('status', 'unknown')}`",
        "",
        "## Steps",
        "",
    ]
    for item in plan.get("steps", []):
        lines.append(f"- `{item.get('id', 'unknown')}` {item.get('title', '')}: `{item.get('command', '')}`")
    missing = plan.get("missing_inputs", [])
    if missing:
        lines.extend(["", "## Missing Inputs", ""])
        for item in missing:
            lines.append(f"- {item}")
    lines.extend(["", "## Next Actions", ""])
    for item in plan.get("next_actions", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)
