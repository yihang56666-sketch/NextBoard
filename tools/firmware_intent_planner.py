"""Plan CubeMX/HAL/FreeRTOS firmware implementation without editing code."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import cubemx_config_advisor  # noqa: E402
import cubemx_ioc_summary  # noqa: E402
import runtime_context  # noqa: E402
import safe_io  # noqa: E402


def normalize_feature(name: str) -> str:
    text = name.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "feature"


def plan_implementation(root: Path, *, feature: str, pin: str = "", function: str = "", rtos: bool = True) -> dict[str, Any]:
    root = root.resolve()
    ioc_path = cubemx_config_advisor.find_ioc(root)
    summary = cubemx_ioc_summary.summarize(ioc_path)
    normalized_feature = normalize_feature(feature)
    requested_function = cubemx_config_advisor.normalize_function(function or feature)
    pin_advice = None
    if pin:
        pin_advice = cubemx_config_advisor.advise(root, pin=pin, function=requested_function)
    handle = infer_hal_handle(requested_function, summary)
    module = normalized_feature.replace("-", "_")
    rtos_available = "FREERTOS" in summary.get("middleware", []) or "FREERTOS" in summary.get("peripheral_details", {})
    use_rtos = rtos and rtos_available
    status = "plan-only" if (not rtos or rtos_available) else "plan-only-needs-rtos-configuration"
    return {
        "schema_version": 1,
        "status": status,
        "root": str(root),
        "ioc_file": str(ioc_path),
        "feature": feature,
        "requested_function": requested_function,
        "rtos_requested": rtos,
        "rtos_available": rtos_available,
        "mcu": summary["mcu"],
        "cube_generated_boundaries": {
            "allowed": ["CubeMX USER CODE sections", "Core/Inc/app_*.h", "Core/Src/app_*.c"],
            "forbidden_by_default": ["Drivers/", "generated HAL driver files", "startup files", "linker scripts"],
        },
        "recommended_files": [
            f"Core/Inc/app_{module}.h",
            f"Core/Src/app_{module}.c",
        ],
        "hal": {
            "handle": handle,
            "init_function": init_function(requested_function, handle),
            "callbacks": callbacks(requested_function),
        },
        "rtos_api": "cmsis_os_v1",
        "freertos": freertos_plan(requested_function, use_rtos, requested=rtos),
        "concurrency_model": concurrency_model(requested_function, use_rtos),
        "timeout_ms": timeout_ms(requested_function),
        "error_policy": error_policy(requested_function),
        "recovery_policy": recovery_policy(requested_function),
        "integration_hooks": integration_hooks(requested_function),
        "safe_defaults": safe_defaults(requested_function),
        "pin_advice": pin_advice,
        "verification": [
            "Build before flashing.",
            "Keep first firmware test low-risk and observable through UART/RTT/SWO or LED.",
            "Flash only after hardware action plan reaches ready-for-user-confirmation and user confirms it.",
        ],
    }


def infer_hal_handle(function: str, summary: dict[str, Any]) -> str:
    peripherals = summary.get("peripherals", [])
    prefix_map = {
        "i2c": ("I2C", "hi2c"),
        "spi": ("SPI", "hspi"),
        "uart": ("USART", "huart"),
        "can": ("CAN", "hcan"),
        "pwm": ("TIM", "htim"),
        "timer": ("TIM", "htim"),
        "adc": ("ADC", "hadc"),
    }
    prefix, handle_prefix = prefix_map.get(function, ("GPIO", ""))
    for peripheral in peripherals:
        if peripheral.startswith(prefix):
            match = re.search(r"(\d+)$", peripheral)
            digits = match.group(1) if match else ""
            return f"{handle_prefix}{digits}" if digits and handle_prefix else ""
    return ""


def init_function(function: str, handle: str) -> str:
    if not handle:
        return "MX_GPIO_Init()" if function == "gpio-output" else "needs CubeMX peripheral init"
    stem = handle[1:].upper()
    if handle.startswith("huart"):
        return f"MX_USART{stem[-1]}_UART_Init()"
    return f"MX_{stem}_Init()"


def callbacks(function: str) -> list[str]:
    table = {
        "i2c": ["HAL_I2C_MasterTxCpltCallback", "HAL_I2C_MasterRxCpltCallback", "HAL_I2C_ErrorCallback"],
        "spi": ["HAL_SPI_TxRxCpltCallback", "HAL_SPI_ErrorCallback"],
        "uart": ["HAL_UART_RxCpltCallback", "HAL_UART_ErrorCallback"],
        "adc": ["HAL_ADC_ConvCpltCallback", "HAL_ADC_ErrorCallback"],
        "pwm": ["HAL_TIM_PWM_PulseFinishedCallback"],
        "timer": ["HAL_TIM_PeriodElapsedCallback"],
        "can": ["HAL_CAN_RxFifo0MsgPendingCallback", "HAL_CAN_ErrorCallback"],
    }
    return table.get(function, [])


def timeout_ms(function: str) -> int:
    table = {
        "i2c": 100,
        "spi": 100,
        "uart": 20,
        "adc": 20,
        "pwm": 0,
        "timer": 0,
        "can": 10,
        "gpio-output": 0,
    }
    return table.get(function, 100)


def concurrency_model(function: str, rtos_enabled: bool) -> dict[str, Any]:
    if not rtos_enabled:
        return {
            "mode": "bare-metal",
            "primitives": ["bounded polling", "interrupt callbacks when configured"],
            "notes": ["Do not busy-wait indefinitely; keep blocking HAL calls bounded by timeout."],
        }
    table = {
        "i2c": ["mutex", "bus-owner task", "request queue"],
        "spi": ["mutex", "bus-owner task", "request queue"],
        "uart": ["rx queue", "parser task", "short timeout receive loop"],
        "adc": ["sampling task", "sample handoff variable or queue"],
        "pwm": ["control task", "duty update API"],
        "can": ["rx task", "tx API", "error callback"],
        "gpio-output": ["control task", "thread-safe setter"],
    }
    return {"mode": "freertos", "primitives": table.get(function, ["application task", "bounded waits"])}


def error_policy(function: str) -> dict[str, Any]:
    return {
        "return_contract": "app status enum with OK/NOT_READY/TIMEOUT/HAL_ERROR",
        "hal_mapping": "HAL_OK maps to OK; any other HAL_StatusTypeDef maps to HAL_ERROR unless timeout is detected separately.",
        "logging": "caller should log status transitions through UART/RTT/SWO after bring-up channel is confirmed",
        "function": function,
    }


def recovery_policy(function: str) -> list[str]:
    table = {
        "i2c": ["On repeated HAL_ERROR, stop traffic and consider bus recovery by toggling SCL only after schematic review."],
        "spi": ["Deassert chip-select after every failed transfer and reinitialize the peripheral only from a safe task context."],
        "uart": ["Handle overrun/framing errors in HAL_UART_ErrorCallback and restart receive path."],
        "adc": ["Stop ADC after failed poll/conversion before retrying."],
        "pwm": ["Set compare value to zero before disabling or on error."],
        "can": ["Detect bus-off/passive errors, stop transmitting, and require operator review before rejoining a live bus."],
        "gpio-output": ["Return to inactive output level on stop or fault."],
    }
    return table.get(function, ["Stop the feature, preserve debug access, and retry only after root cause is understood."])


def integration_hooks(function: str) -> list[str]:
    common = ["Call app init after CubeMX peripheral init.", "Create or call app task from a USER CODE section."]
    table = {
        "i2c": ["Enable I2C event/error IRQ or DMA in CubeMX if non-blocking transfers are later required."],
        "spi": ["Configure GPIO chip-select pins and DMA if sustained transfers are required."],
        "uart": ["Enable USART IRQ or DMA for production RX paths; keep one debug log channel available."],
        "adc": ["Configure sampling time, channel rank, and DMA if continuous sampling is required."],
        "pwm": ["Verify timer channel, polarity, prescaler, and period before enabling the external load."],
        "can": ["Configure filters before normal mode; use silent/loopback for first bench test when uncertain."],
    }
    return [*common, *table.get(function, [])]


def freertos_plan(function: str, enabled: bool, *, requested: bool = True) -> dict[str, Any]:
    if not enabled:
        reason = "FreeRTOS middleware is not enabled in the .ioc." if requested else "RTOS planning was disabled by the user."
        return {"enabled": False, "model": "blocking or interrupt-driven bare-metal flow", "reason": reason}
    table = {
        "i2c": ("bus-owner task", ["queue for requests", "mutex if sharing with other modules", "task notification for DMA completion"]),
        "spi": ("bus-owner task", ["queue for transfers", "GPIO chip-select guard", "task notification for DMA completion"]),
        "uart": ("rx task", ["stream buffer or queue", "DMA/interrupt receive", "parser task for commands"]),
        "adc": ("sampling task", ["DMA circular buffer", "queue or notification to processing task"]),
        "pwm": ("control task", ["queue for duty updates", "safe startup duty", "timer hardware output"]),
        "timer": ("event task", ["task notification from timer ISR", "bounded processing"]),
        "can": ("CAN rx/tx tasks", ["rx queue", "tx queue", "filters before normal mode"]),
        "gpio-output": ("control task", ["queue or direct API for state changes", "safe inactive default"]),
    }
    model, primitives = table.get(function, ("application task", ["queue for commands", "bounded waits"]))
    return {
        "enabled": True,
        "model": model,
        "primitives": primitives,
        "isr_rule": "Use FromISR APIs only, keep ISR short, defer work to tasks.",
    }


def safe_defaults(function: str) -> list[str]:
    defaults = ["Initialize feature disabled until app explicitly starts it."]
    if function in {"gpio-output", "pwm"}:
        defaults.append("Use inactive output level or zero/safe duty before enabling load.")
    if function in {"i2c", "spi", "uart", "can"}:
        defaults.append("Start with conservative speed and timeouts; log errors.")
    if function == "can":
        defaults.append("Use silent or loopback mode before joining a live bus when uncertain.")
    return defaults


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Firmware Implementation Plan",
        "",
        f"- Root: `{plan['root']}`",
        f"- IOC: `{plan['ioc_file']}`",
        f"- Feature: {plan['feature']}",
        f"- Function: `{plan['requested_function']}`",
        f"- Status: `{plan['status']}`",
        "",
        "## Recommended Files",
        "",
    ]
    for item in plan["recommended_files"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## HAL", ""])
    lines.append(f"- Handle: `{plan['hal']['handle'] or 'unknown'}`")
    lines.append(f"- Init function: `{plan['hal']['init_function']}`")
    for item in plan["hal"]["callbacks"]:
        lines.append(f"- Callback: `{item}`")
    lines.extend(["", "## FreeRTOS", ""])
    lines.append(f"- Enabled: {plan['freertos']['enabled']}")
    lines.append(f"- Model: {plan['freertos']['model']}")
    for item in plan["freertos"].get("primitives", []):
        lines.append(f"- Primitive: {item}")
    lines.extend(["", "## Safe Defaults", ""])
    for item in plan["safe_defaults"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Verification", ""])
    for item in plan["verification"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan CubeMX/HAL/FreeRTOS firmware implementation")
    parser.add_argument("--root", default=".")
    parser.add_argument("--feature", required=True)
    parser.add_argument("--pin", default="")
    parser.add_argument("--function", default="")
    parser.add_argument("--no-rtos", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    plan = plan_implementation(
        Path(args.root),
        feature=args.feature,
        pin=args.pin,
        function=args.function,
        rtos=not args.no_rtos,
    )
    content = json.dumps(plan, ensure_ascii=False, indent=2) if args.as_json else render_markdown(plan)
    if args.out:
        safe_io.safe_write_text(Path(args.out), content, allowed_roots=runtime_context.allowed_write_roots())
    else:
        print(content)


if __name__ == "__main__":
    main()
