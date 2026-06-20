"""Generate CubeMX pin/peripheral configuration advice from .ioc evidence."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import cubemx_ioc_summary  # noqa: E402
import pin_capabilities  # noqa: E402
import runtime_context  # noqa: E402
import safe_io  # noqa: E402

FUNCTION_ALIASES = {
    "gpio": "gpio-output",
    "output": "gpio-output",
    "gpio-output": "gpio-output",
    "i2c": "i2c",
    "iic": "i2c",
    "spi": "spi",
    "uart": "uart",
    "usart": "uart",
    "adc": "adc",
    "pwm": "pwm",
    "timer": "timer",
    "can": "can",
}
PIN_PREFIXES = ("PA", "PB", "PC", "PD", "PE", "PF", "PG", "PH", "PI", "PJ", "PK")


def find_ioc(root: Path) -> Path:
    root = root.resolve()
    if root.suffix.lower() == ".ioc":
        return root
    matches = sorted(root.rglob("*.ioc"))
    if not matches:
        raise FileNotFoundError(f"No CubeMX .ioc file found under {root}")
    if len(matches) > 1:
        choices = ", ".join(str(path.relative_to(root)) for path in matches[:10])
        raise ValueError(f"Multiple CubeMX .ioc files found under {root}; pass the exact .ioc file. Candidates: {choices}")
    return matches[0]


def normalize_function(name: str) -> str:
    return FUNCTION_ALIASES.get(name.strip().lower(), name.strip().lower() or "unspecified")


def advise(root: Path, *, pin: str, function: str, pin_evidence: str = '') -> dict[str, Any]:
    ioc_path = find_ioc(root)
    summary = cubemx_ioc_summary.summarize(ioc_path)
    pin_name = pin.strip().upper()
    requested = normalize_function(function)
    normalized_pin = summary.get("normalized_pins", {}).get(pin_name, {})
    pin_fields = summary.get("pins", {}).get(pin_name, {})
    configured_signal = normalized_pin.get("signal") or pin_fields.get("Signal", pin_fields.get("value", ""))
    evidence_root = ioc_path.parent if Path(root).suffix.lower() == '.ioc' else Path(root)
    capability_evidence = pin_capabilities.evaluate_pin(
        pin_capabilities.find_evidence(evidence_root, str(summary.get('mcu', {}).get('name') or ''), pin_evidence),
        pin_name,
        requested,
        configured_signal,
    )
    conflicts = detect_conflicts(pin_name, configured_signal, requested)
    conflicts.extend(pin_capability_conflicts(capability_evidence))
    status = "conflict" if conflicts else ("ok" if pin_fields else "needs-configuration")
    return {
        "schema_version": 1,
        "status": status,
        "ioc_file": summary["ioc_file"],
        "mcu": summary["mcu"],
        "project": summary["project"],
        "requested_function": requested,
        "pin": {
            "name": pin_name,
            "configured": bool(pin_fields),
            "configured_signal": configured_signal,
            "function_class": normalized_pin.get("function_class", ""),
            "risk_tags": normalized_pin.get("risk_tags", []),
            "fields": pin_fields,
        },
        "pin_capability_evidence": capability_evidence,
        "required_settings": required_settings(requested),
        "why": reasons(requested),
        "alternatives": alternatives(requested),
        "conflicts": conflicts,
        "risks": risks(pin_name, requested, configured_signal, conflicts) + pin_capability_risks(capability_evidence),
        "generated_code": generated_code_impact(requested),
        "next_actions": next_actions(status, conflicts) + pin_capability_next_actions(capability_evidence),
    }


def propose_ioc_patch(
    root: Path,
    *,
    pin: str = "",
    function: str,
    instance: str = "",
    pair_pin: str = "",
    pin_role: str = "",
    scl_pin: str = "",
    sda_pin: str = "",
    timing: str = "",
    label: str = "",
) -> dict[str, Any]:
    ioc_path = find_ioc(root)
    requested = normalize_function(function)
    pin_name = normalize_pin_name(pin) if pin else ""
    pair_name = normalize_pin_name(pair_pin) if pair_pin else ""
    scl_name = normalize_pin_name(scl_pin) if scl_pin else ""
    sda_name = normalize_pin_name(sda_pin) if sda_pin else ""
    summary = cubemx_ioc_summary.summarize(ioc_path)
    conflicts = []
    if requested == "i2c":
        if not instance.strip():
            return blocked_patch_result(
                ioc_path,
                summary,
                pin_name or sda_name or scl_name,
                requested,
                "missing_instance",
                "I2C patch requires --instance, for example I2C1.",
            )
        if not (scl_name and sda_name):
            if pin_name and pair_name:
                role = pin_role.strip().lower() or "sda"
                sda_name = pin_name if role == "sda" else pair_name
                scl_name = pair_name if role == "sda" else pin_name
            else:
                return blocked_patch_result(
                    ioc_path,
                    summary,
                    pin_name,
                    requested,
                    "missing_i2c_pins",
                    "I2C requires both --scl and --sda pins plus --instance.",
                )
        pin_name = sda_name
        pair_name = scl_name
    elif not pin_name:
        return blocked_patch_result(
            ioc_path,
            summary,
            pin_name,
            requested,
            "missing_pin",
            "This patch requires --pin.",
        )

    for candidate in [item for item in (pin_name, pair_name) if item]:
        signal = (summary.get("normalized_pins", {}).get(candidate, {}) or {}).get("signal", "")
        conflicts.extend(detect_conflicts(candidate, signal, requested))
    if conflicts:
        return {
            "schema_version": 1,
            "status": "blocked-conflict",
            "ioc_file": str(ioc_path.resolve()),
            "mcu": summary["mcu"],
            "requested_function": requested,
            "pin": pin_name,
            "pair_pin": pair_name,
            "changes": [],
            "proposed_changes": [],
            "blocked_changes": [],
            "diff_preview": "",
            "backup_path": backup_path(ioc_path),
            "conflicts": conflicts,
            "write_required_flags": ["--write", "--confirm-write"],
            "write_required_confirmation": True,
            "written": False,
            "next_actions": ["Resolve conflicts before changing the .ioc file."],
        }

    if requested == "gpio-output":
        changes = gpio_output_changes(pin_name, label=label)
    elif requested == "i2c":
        changes = i2c_changes(scl_name, sda_name, instance=instance, timing=timing or "0x00C0EAFF")
    else:
        return blocked_patch_result(
            ioc_path,
            summary,
            pin_name,
            requested,
            "unsupported_function",
            f"Safe .ioc patch generation is not implemented for {requested}.",
        )

    original = ioc_path.read_text(encoding="utf-8", errors="replace")
    updated = apply_ioc_changes(original, changes)
    return {
        "schema_version": 1,
        "status": "ready-to-write",
        "ioc_file": str(ioc_path.resolve()),
        "mcu": summary["mcu"],
        "project": summary["project"],
        "requested_function": requested,
        "pin": pin_name,
        "pair_pin": pair_name,
        "changes": changes,
        "proposed_changes": changes,
        "blocked_changes": [],
        "diff_preview": diff_preview(original, updated, fromfile=str(ioc_path), tofile=f"{ioc_path} (patched)"),
        "backup_path": backup_path(ioc_path),
        "conflicts": [],
        "write_required_flags": ["--write", "--confirm-write"],
        "write_required_confirmation": True,
        "written": False,
        "notes": patch_notes(requested),
        "next_actions": [
            "Review every key/value change before writing.",
            "After writing, open STM32CubeMX, regenerate code, then run a build before any flash/debug action.",
        ],
    }


def blocked_patch_result(ioc_path: Path, summary: dict[str, Any], pin: str, function: str, code: str, message: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": f"blocked-{code}",
        "ioc_file": str(ioc_path.resolve()),
        "mcu": summary["mcu"],
        "requested_function": function,
        "pin": pin,
        "changes": [],
        "proposed_changes": [],
        "blocked_changes": [],
        "diff_preview": "",
        "backup_path": backup_path(ioc_path),
        "conflicts": [],
        "error": {"code": code, "message": message},
        "write_required_flags": ["--write", "--confirm-write"],
        "write_required_confirmation": True,
        "written": False,
        "next_actions": [message],
    }


def normalize_pin_name(pin: str) -> str:
    value = pin.strip().upper()
    if not value:
        return ""
    if value in {"BOOT0", "NRST"}:
        return value
    if not value.startswith(PIN_PREFIXES):
        raise ValueError(f"Unsupported pin name: {pin}")
    return value


def gpio_output_changes(pin: str, *, label: str = "") -> list[dict[str, str]]:
    safe_label = label.strip() or f"APP_{pin}_OUT"
    return [
        change(pin, "Signal", "GPIO_Output", "Configure pin as GPIO output."),
        change(pin, "GPIO_Label", safe_label, "Make generated code easier to inspect."),
        change(pin, "GPIO_OType", "GPIO_OType_PP", "Use push-pull output for direct logic/LED drive."),
        change(pin, "GPIO_PuPd", "GPIO_NOPULL", "Do not add internal pull unless the schematic requires it."),
        change(pin, "GPIO_Speed", "GPIO_SPEED_FREQ_LOW", "Keep edge rate low during bring-up."),
        change(pin, "GPIO_InitState", "GPIO_PIN_RESET", "Start from a safe inactive level."),
    ]


def i2c_changes(scl_pin: str, sda_pin: str, *, instance: str, timing: str) -> list[dict[str, str]]:
    instance = instance.strip().upper() or "I2C1"
    changes = [
        change(sda_pin, "Signal", f"{instance}_SDA", "Assign I2C data line."),
        change(scl_pin, "Signal", f"{instance}_SCL", "Assign I2C clock line."),
    ]
    for bus_pin in (sda_pin, scl_pin):
        changes.extend(
            [
                change(bus_pin, "GPIO_OType", "GPIO_OType_OD", "I2C lines must be open-drain."),
                change(bus_pin, "GPIO_PuPd", "GPIO_NOPULL", "Use external pull-ups sized for the bus."),
                change(bus_pin, "GPIO_Speed", "GPIO_SPEED_FREQ_LOW", "Start with conservative edge rate."),
            ]
        )
    changes.extend(
        [
            change(instance, "IPParameters", "Timing", "Enable explicit timing parameter in CubeMX."),
            change(instance, "Timing", timing, "Initial timing value; verify against actual I2C clock."),
        ]
    )
    return changes


def change(owner: str, field: str, value: str, reason: str) -> dict[str, str]:
    return {"key": f"{owner}.{field}", "value": value, "reason": reason}


def patch_notes(function: str) -> list[str]:
    if function == "gpio-output":
        return [
            "This .ioc patch only configures CubeMX metadata; verify load current and schematic before driving the pin.",
            "Generated firmware still needs application code to call HAL_GPIO_WritePin from a safe user-code/app layer.",
        ]
    if function == "i2c":
        return [
            "This .ioc patch assumes external pull-ups and a conservative initial timing value.",
            "Verify pull-up voltage, bus capacitance, and CubeMX timing after clock configuration.",
        ]
    return []


def write_ioc_patch(patch: dict[str, Any], *, confirm_write: bool = False) -> dict[str, Any]:
    if patch.get("status") != "ready-to-write":
        raise ValueError(f"patch status must be ready-to-write, got {patch.get('status')}")
    if not confirm_write:
        raise ValueError("Writing .ioc changes requires --write --confirm-write after reviewing the patch.")
    ioc_path = Path(str(patch["ioc_file"]))
    safe_io.validate_write_path(ioc_path, allowed_roots=runtime_context.allowed_write_roots())
    validate_ioc_patch_current_state(ioc_path, patch)
    original = ioc_path.read_text(encoding="utf-8", errors="replace")
    updated = apply_ioc_changes(original, patch.get("changes", []))
    backup = safe_io.safe_write_text(Path(patch.get("backup_path") or backup_path(ioc_path)), original, allowed_roots=runtime_context.allowed_write_roots())
    written = safe_io.safe_write_text(ioc_path, updated, allowed_roots=runtime_context.allowed_write_roots())
    return {**patch, "status": "written", "written": True, "written_file": written, "backup_file": backup}


def validate_ioc_patch_current_state(ioc_path: Path, patch: dict[str, Any]) -> None:
    summary = cubemx_ioc_summary.summarize(ioc_path)
    requested = normalize_function(str(patch.get("requested_function") or ""))
    conflicts: list[dict[str, str]] = []
    for item in patch.get("changes", []):
        key = str(item.get("key") or "")
        value = str(item.get("value") or "")
        if not key.endswith(".Signal") or "." not in key:
            continue
        owner = key.split(".", 1)[0].strip().upper()
        current = str((summary.get("normalized_pins", {}).get(owner, {}) or {}).get("signal") or "")
        if current and current == value:
            continue
        conflicts.extend(detect_conflicts(owner, current, requested))
    if conflicts:
        raise ValueError(f"Current .ioc state has changed since preview; refusing to write over conflicts: {conflicts}")


def apply_ioc_changes(text: str, changes: list[dict[str, str]]) -> str:
    lines = text.splitlines()
    line_index = {}
    for index, raw in enumerate(lines):
        if "=" not in raw or raw.lstrip().startswith("#"):
            continue
        key = raw.split("=", 1)[0].strip()
        line_index[key] = index
    appended = []
    for item in changes:
        key = str(item.get("key", ""))
        value = str(item.get("value", ""))
        if not key:
            continue
        line = f"{key}={value}"
        if key in line_index:
            lines[line_index[key]] = line
        else:
            appended.append(line)
    if appended:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("# Added by hardware-butler patch-ioc")
        lines.extend(appended)
    return "\n".join(lines) + "\n"


def backup_path(ioc_path: Path) -> str:
    return str(ioc_path.with_name(f"{ioc_path.name}.before-cubemx-patch"))


def diff_preview(original: str, updated: str, *, fromfile: str, tofile: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            original.splitlines(),
            updated.splitlines(),
            fromfile=fromfile,
            tofile=tofile,
            lineterm="",
        )
    )


def required_settings(function: str) -> list[dict[str, str]]:
    table = {
        "gpio-output": [
            ("Pin mode", "GPIO Output"),
            ("GPIO mode", "Output Push Pull"),
            ("Initial level", "Inactive/safe level before enabling external load"),
            ("GPIO speed", "Low unless edge rate or timing requires higher speed"),
            ("Pull", "No pull unless the schematic requires a defined idle state"),
        ],
        "i2c": [
            ("Peripheral mode", "I2C controller/master or target/slave as required"),
            ("GPIO output type", "Open Drain"),
            ("Pull-up", "External pull-ups to a voltage safe for every bus device"),
            ("Timing", "Generate from actual I2C peripheral clock"),
            ("NVIC/DMA", "Use interrupt or DMA for non-blocking RTOS transfers"),
        ],
        "spi": [
            ("Peripheral mode", "SPI master/slave to match the external device"),
            ("Clock polarity/phase", "Match slave datasheet CPOL/CPHA"),
            ("NSS/chip select", "Prefer GPIO-controlled CS for one or more slaves"),
            ("DMA", "Enable for sustained transfers or displays/sensors with large frames"),
        ],
        "uart": [
            ("Mode", "Asynchronous UART/USART"),
            ("Baud/parity/stop", "Match the connected device"),
            ("Receive path", "Interrupt or DMA for command streams under RTOS"),
            ("Diagnostics", "Keep one log channel available during bring-up"),
        ],
        "adc": [
            ("Mode", "ADC input"),
            ("Sampling time", "Choose based on source impedance"),
            ("Reference", "Verify Vref and analog supply"),
            ("DMA", "Use DMA for continuous multi-channel sampling"),
        ],
        "pwm": [
            ("Timer mode", "PWM generation"),
            ("Period", "Derive from timer clock and prescaler"),
            ("Duty cycle", "Start at a safe inactive duty"),
            ("Output polarity", "Match the driver/load safe state"),
        ],
        "timer": [
            ("Timer mode", "Base/PWM/capture/compare as required"),
            ("Clock source", "Internal timer clock unless external timing is required"),
            ("Interrupt/DMA", "Enable only when the application consumes events safely"),
        ],
        "can": [
            ("Peripheral mode", "CAN normal/silent/loopback according to bring-up phase"),
            ("Bit timing", "Match bus bitrate and sample point"),
            ("Transceiver", "Verify standby/enable pin and voltage domain"),
            ("Filters", "Configure receive filters before bus testing"),
        ],
    }
    return [{"setting": key, "recommendation": value} for key, value in table.get(function, [])]


def reasons(function: str) -> list[str]:
    table = {
        "gpio-output": [
            "Push-pull is appropriate for directly driving a logic input or LED through a resistor.",
            "A safe initial level prevents accidental enabling of loads at reset.",
        ],
        "i2c": [
            "I2C is a wired-AND bus, so pins must be open-drain with pull-ups.",
            "Pull-up voltage must match the lowest-tolerance device on the bus.",
        ],
        "spi": ["SPI electrical behavior and sampling depend on CPOL/CPHA matching the slave."],
        "uart": ["UART framing must match the connected peer; receive should not busy-wait in RTOS code."],
        "adc": ["ADC accuracy depends on source impedance, sampling time, reference, and analog limits."],
        "pwm": ["Hardware PWM gives deterministic timing that a task loop cannot provide."],
        "timer": ["Timers should own precise timing while tasks handle slower control work."],
        "can": ["CAN bus tests can affect other nodes; begin with silent/loopback when uncertain."],
    }
    return table.get(function, ["Function-specific evidence is not encoded yet; verify with the chip manual and schematic."])


def alternatives(function: str) -> list[str]:
    table = {
        "gpio-output": ["Open-drain output when sharing a line or level shifting.", "Timer PWM output for periodic waveforms."],
        "i2c": ["Use another I2C instance if pins conflict.", "Use software I2C only for low-speed recovery/prototype cases."],
        "spi": ["Use another SPI instance or lower SCK when layout/device margin is unknown."],
        "uart": ["Use RTT/SWO for logs if UART pins are needed by the application."],
        "adc": ["Use external ADC when resolution/noise/source impedance exceeds MCU ADC capability."],
        "pwm": ["Use DAC or filtered PWM for analog-like output."],
        "timer": ["Use RTOS software timers only for coarse timing."],
        "can": ["Use loopback/silent mode before joining a live bus."],
    }
    return table.get(function, [])


def detect_conflicts(pin: str, configured_signal: str, function: str) -> list[dict[str, str]]:
    conflicts = []
    if high_risk_pin_or_signal(pin, configured_signal):
        conflicts.append(
            {
                "level": "high",
                "conflict": "reserved_pin",
                "message": f"{pin} is reserved for debug/clock/boot/reset use ({configured_signal or 'reserved pin'}); do not patch it automatically.",
            }
        )
    if configured_signal and not signal_matches(configured_signal, function):
        conflicts.append(
            {
                "level": "warning",
                "conflict": "configured_signal_mismatch",
                "message": f"{pin} is currently configured as {configured_signal}, not {function}.",
            }
        )
    if pin in {"PA13", "PA14"}:
        conflicts.append(
            {
                "level": "high",
                "conflict": "debug_pin",
                "message": f"{pin} is commonly used for SWD; do not repurpose until recovery access is proven.",
            }
        )
    return conflicts


def high_risk_pin_or_signal(pin: str, signal: str) -> bool:
    text = signal.upper()
    return (
        pin in {"PA13", "PA14", "BOOT0", "NRST"}
        or text.startswith("SYS_")
        or text.startswith("RCC_")
        or "SWD" in text
        or "JTMS" in text
        or "JTCK" in text
        or "OSC" in text
        or "BOOT" in text
        or "NRST" in text
    )


def signal_matches(signal: str, function: str) -> bool:
    normalized = signal.lower()
    if function == "gpio-output":
        return "gpio_output" in normalized or "gpio output" in normalized
    if function == "uart":
        return normalized.startswith("usart") or normalized.startswith("uart")
    if function == "pwm":
        return normalized.startswith("tim") and "_ch" in normalized
    if function == "timer":
        return normalized.startswith("tim")
    return function in normalized


def pin_capability_conflicts(capability: dict[str, Any]) -> list[dict[str, str]]:
    if capability.get("verification_status") != "contradicted":
        return []
    pin = capability.get("pin", "")
    requested = capability.get("requested_function", "")
    functions = ", ".join(capability.get("available_functions", [])) or "none listed"
    return [
        {
            "level": "high",
            "conflict": "pin_capability_mismatch",
            "message": f"Package evidence for {pin} does not list {requested}; listed functions: {functions}.",
        }
    ]


def pin_capability_risks(capability: dict[str, Any]) -> list[dict[str, str]]:
    status = capability.get("verification_status")
    if status == "verified":
        return []
    if status == "contradicted":
        return [
            {
                "risk": "Pin mux not supported by package evidence",
                "mitigation": "Choose a matching alternate-function pin or provide corrected package pin evidence before changing CubeMX.",
            }
        ]
    if status == "inferred":
        return [
            {
                "risk": "Pin mux inferred only from existing .ioc",
                "mitigation": "Verify the exact chip package pin table before relying on this assignment.",
            }
        ]
    return [
        {
            "risk": "Package pin capability unknown",
            "mitigation": "Add pin-capabilities.json from datasheet/package evidence or manually verify the alternate-function table.",
        }
    ]


def pin_capability_next_actions(capability: dict[str, Any]) -> list[str]:
    status = capability.get("verification_status")
    if status == "verified":
        return []
    if status == "contradicted":
        return ["Do not apply this pin assignment until package pin evidence and CubeMX selection agree."]
    return ["Provide package pin capability evidence with --pin-evidence or docs/chip/<part>/pin-capabilities.json."]


def risks(pin: str, function: str, configured_signal: str, conflicts: list[dict[str, str]]) -> list[dict[str, str]]:
    items = [
        {
            "risk": "Schematic mismatch",
            "mitigation": "Confirm the board schematic before assuming the pin is free or connected to the expected load.",
        }
    ]
    if function == "gpio-output":
        items.append(
            {
                "risk": "GPIO current or output contention",
                "mitigation": "Verify resistor/load and ensure the pin is not connected to another active output.",
            }
        )
    if function == "i2c":
        items.append(
            {
                "risk": "Unsafe pull-up voltage",
                "mitigation": "Confirm pull-up voltage and all bus device voltage tolerance.",
            }
        )
    if configured_signal and conflicts:
        items.append({"risk": "Existing CubeMX configuration conflict", "mitigation": "Resolve pin mux conflict before regenerating code."})
    return items


def generated_code_impact(function: str) -> list[str]:
    if function == "gpio-output":
        return ["Expect `MX_GPIO_Init()` changes.", "Use `HAL_GPIO_WritePin()` from application/user-code areas."]
    if function == "i2c":
        return ["Expect `MX_I2C*_Init()` and `I2C_HandleTypeDef hi2c*`.", "Use a bus-owner task or mutex under FreeRTOS."]
    if function == "spi":
        return ["Expect `MX_SPI*_Init()` and `SPI_HandleTypeDef hspi*`.", "Use GPIO chip-select and DMA callbacks when needed."]
    if function == "uart":
        return ["Expect `MX_USART*_UART_Init()` and `UART_HandleTypeDef huart*`.", "Use interrupt/DMA receive for RTOS command streams."]
    if function == "pwm":
        return ["Expect `MX_TIM*_Init()`.", "Start PWM only after setting a safe duty cycle."]
    return ["Keep edits inside CubeMX `USER CODE` sections or app-specific files."]


def next_actions(status: str, conflicts: list[dict[str, str]]) -> list[str]:
    actions = []
    if status == "needs-configuration":
        actions.append("Configure the pin/peripheral in CubeMX and regenerate code.")
    if conflicts:
        actions.append("Resolve listed conflicts before firmware implementation or flashing.")
    actions.append("Run build before any flash/debug action.")
    return actions


def render_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# CubeMX Configuration Advice",
        "",
        f"- IOC: `{data['ioc_file']}`",
        f"- MCU: {data['mcu'].get('name') or 'unknown'}",
        f"- Pin: `{data['pin']['name']}`",
        f"- Requested function: `{data['requested_function']}`",
        f"- Status: `{data['status']}`",
        f"- Existing signal: {data['pin'].get('configured_signal') or 'none'}",
        "",
        "## Required Settings",
        "",
    ]
    for item in data["required_settings"]:
        lines.append(f"- {item['setting']}: {item['recommendation']}")
    lines.extend(["", "## Why", ""])
    for item in data["why"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Risks", ""])
    for item in data["risks"]:
        lines.append(f"- {item['risk']}: {item['mitigation']}")
    lines.extend(["", "## Pin Capability Evidence", ""])
    capability = data.get("pin_capability_evidence", {})
    lines.append(f"- Verification: `{capability.get('verification_status', 'unknown')}`")
    lines.append(f"- Support: `{capability.get('support_status', 'unknown')}`")
    lines.append(f"- Evidence file: `{capability.get('evidence_file', '') or 'none'}`")
    source = capability.get("source") or {}
    if source:
        lines.append(f"- Source: {source.get('document', 'unknown')} {source.get('revision', '')}".rstrip())
    matches = capability.get("matching_signals", [])
    if matches:
        for item in matches:
            lines.append(f"- Match: `{item.get('name', '')}` {item.get('af', '')}: {item.get('evidence', '')}".rstrip())
    else:
        functions = ", ".join(capability.get("available_functions", [])) or "none listed"
        lines.append(f"- Available functions from evidence: {functions}")
    for note in capability.get("notes", []):
        lines.append(f"- Note: {note}")
    lines.extend(["", "## Conflicts", ""])
    if data["conflicts"]:
        for item in data["conflicts"]:
            lines.append(f"- [{item['level']}] {item['conflict']}: {item['message']}")
    else:
        lines.append("- none")
    lines.extend(["", "## Alternatives", ""])
    if data["alternatives"]:
        for item in data["alternatives"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none encoded")
    lines.extend(["", "## Generated Code Impact", ""])
    for item in data["generated_code"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Next Actions", ""])
    for item in data["next_actions"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def render_ioc_patch_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# CubeMX IOC Patch",
        "",
        f"- IOC: `{data.get('ioc_file', '')}`",
        f"- Status: `{data.get('status', '')}`",
        f"- Requested function: `{data.get('requested_function', '')}`",
        f"- Pin: `{data.get('pin', '')}`",
        f"- Pair pin: `{data.get('pair_pin', '')}`",
        f"- Written: {data.get('written', False)}",
        f"- Backup path: `{data.get('backup_path', '')}`",
        "",
        "## Proposed Changes",
        "",
    ]
    changes = data.get("proposed_changes") or data.get("changes") or []
    if changes:
        for item in changes:
            lines.append(f"- `{item.get('key', '')}` = `{item.get('value', '')}`: {item.get('reason', '')}")
    else:
        lines.append("- none")
    if data.get("conflicts"):
        lines.extend(["", "## Conflicts", ""])
        for item in data["conflicts"]:
            lines.append(f"- [{item.get('level', '')}] {item.get('conflict', '')}: {item.get('message', '')}")
    if data.get("diff_preview"):
        lines.extend(["", "## Diff Preview", "", "```diff", data["diff_preview"], "```"])
    if data.get("notes"):
        lines.extend(["", "## Notes", ""])
        for item in data["notes"]:
            lines.append(f"- {item}")
    lines.extend(["", "## Next Actions", ""])
    for item in data.get("next_actions", []):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Advise CubeMX pin/peripheral configuration")
    parser.add_argument("--root", default=".")
    parser.add_argument("--pin", required=True)
    parser.add_argument("--function", required=True)
    parser.add_argument("--pin-evidence", default="")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    data = advise(Path(args.root), pin=args.pin, function=args.function, pin_evidence=args.pin_evidence)
    content = json.dumps(data, ensure_ascii=False, indent=2) if args.as_json else render_markdown(data)
    if args.out:
        safe_io.safe_write_text(Path(args.out), content, allowed_roots=runtime_context.allowed_write_roots())
    else:
        print(content)


if __name__ == "__main__":
    main()
