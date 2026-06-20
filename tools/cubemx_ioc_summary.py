"""Summarize STM32CubeMX .ioc files.

The parser keeps the raw key/value data intact and extracts the fields most
useful for bring-up: MCU, package, project manager settings, pin assignments,
peripherals, clocks, and middleware.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import runtime_context  # noqa: E402
import safe_io  # noqa: E402

PIN_PREFIXES = ("PA", "PB", "PC", "PD", "PE", "PF", "PG", "PH", "PI", "PJ", "PK")


def parse_ioc(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def summarize(path: Path) -> dict[str, Any]:
    values = parse_ioc(path)
    pins: dict[str, dict[str, str]] = defaultdict(dict)
    peripherals: set[str] = set()
    middleware: set[str] = set()
    clock_keys: dict[str, str] = {}

    for key, value in values.items():
        prefix = key.split(".", 1)[0]
        if prefix.startswith(PIN_PREFIXES):
            pin, field = key.split(".", 1) if "." in key else (key, "value")
            pins[pin][field] = value
        if "." in key and not prefix.startswith(PIN_PREFIXES):
            if prefix.isupper() or any(ch.isdigit() for ch in prefix):
                peripherals.add(prefix)
        if key.startswith("Mcu.") or key.startswith("ProjectManager."):
            continue
        if "Clock" in key or key.startswith("RCC.") or key.startswith("PLL."):
            clock_keys[key] = value
        if key.startswith("MIDDLEWARES.") or key.startswith("FREERTOS.") or key.startswith("USB_"):
            middleware.add(prefix)

    normalized_pins = normalize_pins(pins)
    normalized_peripherals = normalize_peripherals(values, normalized_pins)
    indexes = build_indexes(normalized_pins)

    return {
        "schema_version": 1,
        "ioc_file": str(path.resolve()),
        "mcu": {
            "family": values.get("Mcu.Family", ""),
            "name": values.get("Mcu.Name", ""),
            "package": values.get("Mcu.Package", ""),
            "line": values.get("Mcu.Line", ""),
        },
        "project": {
            "name": values.get("ProjectManager.ProjectName", ""),
            "toolchain": values.get("ProjectManager.TargetToolchain", ""),
            "firmware_package": values.get("ProjectManager.FirmwarePackage", ""),
            "hal_assert": values.get("ProjectManager.HalAssertFull", ""),
        },
        "pin_count": len(pins),
        "pins": dict(sorted(pins.items())),
        "normalized_pins": normalized_pins,
        "peripherals": sorted(peripherals),
        "peripheral_details": normalized_peripherals,
        "middleware": sorted(middleware),
        "clock_settings": dict(sorted(clock_keys.items())),
        "indexes": indexes,
        "raw_key_count": len(values),
    }


def normalize_pins(pins: dict[str, dict[str, str]]) -> dict[str, dict[str, Any]]:
    normalized = {}
    for pin, fields in sorted(pins.items()):
        signal = fields.get("Signal", fields.get("value", ""))
        port, number = split_pin(pin)
        function_class = classify_signal(signal)
        normalized[pin] = {
            "port": port,
            "number": number,
            "signal": signal,
            "function_class": function_class,
            "label": fields.get("GPIO_Label", ""),
            "owner": owner_from_signal(signal, function_class),
            "mode": mode_from_signal(signal),
            "gpio": {
                "pull": fields.get("GPIO_PuPd", ""),
                "speed": fields.get("GPIO_Speed", ""),
                "output_type": fields.get("GPIO_OType", ""),
                "initial_level": fields.get("GPIO_InitState", ""),
            },
            "risk_tags": risk_tags(pin, signal, function_class),
            "raw": dict(fields),
        }
    return normalized


def split_pin(pin: str) -> tuple[str, int | None]:
    match = re.match(r"^P([A-K])(\d+)$", pin)
    if not match:
        return "", None
    return match.group(1), int(match.group(2))


def classify_signal(signal: str) -> str:
    text = signal.lower()
    if "swd" in text or "jtms" in text or "jtck" in text or text.startswith("sys_"):
        return "debug"
    if text.startswith("gpio"):
        return "gpio"
    if text.startswith("i2c"):
        return "i2c"
    if text.startswith("spi"):
        return "spi"
    if text.startswith("usart") or text.startswith("uart"):
        return "uart"
    if text.startswith("tim") and "_ch" in text:
        return "pwm"
    if text.startswith("tim"):
        return "timer"
    if text.startswith("adc"):
        return "adc"
    if text.startswith("can"):
        return "can"
    if text.startswith("usb"):
        return "usb"
    if text.startswith("rcc"):
        return "clock"
    if not text:
        return "unassigned"
    return "alternate"


def owner_from_signal(signal: str, function_class: str) -> str:
    if function_class == "gpio":
        return "GPIO"
    if "_" in signal:
        return signal.split("_", 1)[0]
    return signal or ""


def mode_from_signal(signal: str) -> str:
    text = signal.lower()
    if "output" in text:
        return "output"
    if "input" in text:
        return "input"
    if "exti" in text:
        return "interrupt"
    if "_ch" in text:
        return "alternate-function"
    if "swd" in text or "jt" in text:
        return "debug"
    return ""


def risk_tags(pin: str, signal: str, function_class: str) -> list[str]:
    tags = []
    if pin in {"PA13", "PA14"} or function_class == "debug":
        tags.append("debug-access")
    if function_class == "clock":
        tags.append("clock-source")
    if function_class == "gpio" and "Output" in signal:
        tags.append("output-current")
    return tags


def normalize_peripherals(values: dict[str, str], normalized_pins: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    details: dict[str, dict[str, Any]] = {}
    for key, value in values.items():
        if "." not in key:
            continue
        prefix, field = key.split(".", 1)
        if prefix.startswith(PIN_PREFIXES) or prefix.startswith("ProjectManager") or prefix.startswith("Mcu"):
            continue
        if not (prefix.isupper() or any(ch.isdigit() for ch in prefix)):
            continue
        item = details.setdefault(
            prefix,
            {
                "type": peripheral_type(prefix),
                "instance": prefix,
                "enabled": True,
                "mode": "",
                "pins": [],
                "parameters": {},
                "dma": [],
                "nvic": [],
            },
        )
        item["parameters"][field] = value
        if field.lower().endswith("virtualmode") or field == "VirtualMode":
            item["mode"] = value
    for pin, info in normalized_pins.items():
        owner = info.get("owner", "")
        if owner in details:
            details[owner]["pins"].append(pin)
    return dict(sorted(details.items()))


def peripheral_type(instance: str) -> str:
    text = instance.upper()
    if text.startswith("I2C"):
        return "i2c"
    if text.startswith("SPI"):
        return "spi"
    if text.startswith("USART") or text.startswith("UART"):
        return "uart"
    if text.startswith("TIM"):
        return "timer"
    if text.startswith("ADC"):
        return "adc"
    if text.startswith("CAN"):
        return "can"
    if text.startswith("FREERTOS"):
        return "rtos"
    return text.lower()


def build_indexes(normalized_pins: dict[str, dict[str, Any]]) -> dict[str, Any]:
    by_function: dict[str, list[str]] = defaultdict(list)
    by_label = {}
    reserved = {}
    for pin, info in normalized_pins.items():
        by_function[info["function_class"]].append(pin)
        if info.get("label"):
            by_label[info["label"]] = pin
        if info["risk_tags"]:
            reserved[pin] = info["risk_tags"]
    return {
        "by_function": {key: sorted(value) for key, value in sorted(by_function.items())},
        "by_label": dict(sorted(by_label.items())),
        "reserved_pins": dict(sorted(reserved.items())),
    }


def render_markdown(data: dict[str, Any]) -> str:
    mcu = data["mcu"]
    project = data["project"]
    lines = [
        "# CubeMX IOC Summary",
        "",
        f"- IOC: `{data['ioc_file']}`",
        f"- MCU: {mcu['name'] or 'unknown'}",
        f"- Family: {mcu['family'] or 'unknown'}",
        f"- Package: {mcu['package'] or 'unknown'}",
        f"- Project: {project['name'] or 'unknown'}",
        f"- Toolchain: {project['toolchain'] or 'unknown'}",
        f"- Firmware package: {project['firmware_package'] or 'unknown'}",
        f"- Configured pins: {data['pin_count']}",
        "",
        "## Peripherals",
        "",
    ]
    for peripheral in data["peripherals"]:
        lines.append(f"- {peripheral}")
    if not data["peripherals"]:
        lines.append("- none detected")
    lines.extend(["", "## Pins", ""])
    for pin, fields in data["pins"].items():
        signal = fields.get("Signal", fields.get("value", ""))
        mode = fields.get("Mode", "")
        label = fields.get("GPIO_Label", "")
        details = ", ".join(part for part in (signal, mode, label) if part)
        lines.append(f"- `{pin}`: {details or 'configured'}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize STM32CubeMX .ioc")
    parser.add_argument("ioc", help="Path to .ioc file")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    data = summarize(Path(args.ioc))
    content = json.dumps(data, ensure_ascii=False, indent=2) if args.as_json and not args.markdown else render_markdown(data)
    if args.out:
        safe_io.safe_write_text(Path(args.out), content, allowed_roots=runtime_context.allowed_write_roots())
    else:
        print(content)


if __name__ == "__main__":
    main()
