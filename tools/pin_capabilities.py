from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import runtime_context

FUNCTION_ALIASES = {
    'gpio': 'gpio-output',
    'output': 'gpio-output',
    'gpio-output': 'gpio-output',
    'gpio_output': 'gpio-output',
    'i2c': 'i2c',
    'iic': 'i2c',
    'spi': 'spi',
    'uart': 'uart',
    'usart': 'uart',
    'adc': 'adc',
    'pwm': 'pwm',
    'timer': 'timer',
    'tim': 'timer',
    'can': 'can',
}


def normalize_function(name: str) -> str:
    value = str(name or '').strip().lower().replace(' ', '-')
    return FUNCTION_ALIASES.get(value, value or 'unspecified')


def load_evidence(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict):
        raise ValueError('pin capability evidence must be a JSON object')
    pins = data.get('pins')
    if not isinstance(pins, dict):
        raise ValueError('pin capability evidence must contain a pins object')
    for pin, pin_data in pins.items():
        if not isinstance(pin, str) or not isinstance(pin_data, dict):
            raise ValueError('pins must map pin names to objects')
        signals = pin_data.get('signals', [])
        if signals is not None and not isinstance(signals, list):
            raise ValueError(f'pin {pin} signals must be a list')
    return data


def default_evidence_paths(project_root: Path, part: str) -> list[Path]:
    project = project_root.resolve()
    clean_part = sanitize_part(part)
    paths = [project / 'pin-capabilities.json']
    if clean_part:
        paths.extend(
            [
                project / 'docs' / 'chip' / clean_part / 'pin-capabilities.json',
                runtime_context.workspace_root() / 'docs' / 'chip' / clean_part / 'pin-capabilities.json',
            ]
        )
    return dedupe(paths)


def find_evidence(project_root: Path, part: str, explicit_path: str = '') -> dict[str, Any]:
    if explicit_path.strip():
        raw_path = Path(explicit_path).expanduser()
        if raw_path.is_absolute() or raw_path.exists():
            path = raw_path
        else:
            path = project_root / raw_path
        return load_or_missing(path, [path], f'explicit evidence file not found: {path.resolve()}')
    searched = default_evidence_paths(project_root, part)
    for path in searched:
        if path.exists():
            return load_or_missing(path, searched, 'no evidence file found')
    return missing(searched, 'no evidence file found')


def evaluate_pin(evidence: dict[str, Any], pin: str, requested_function: str, configured_signal: str = '') -> dict[str, Any]:
    pin_name = pin.strip().upper()
    requested = normalize_function(requested_function)
    result: dict[str, Any] = {
        'schema_version': 1,
        'pin': pin_name,
        'requested_function': requested,
        'verification_status': 'unknown',
        'support_status': 'unknown',
        'available': None,
        'matching_signals': [],
        'available_functions': [],
        'source': evidence.get('source', {}) if isinstance(evidence.get('source'), dict) else {},
        'part': str(evidence.get('part', '')),
        'package': str(evidence.get('package', '')),
        'evidence_file': str(evidence.get('_evidence_file', '')),
        'searched_paths': list(evidence.get('_searched_paths', [])),
        'notes': [],
    }
    if evidence.get('_load_error'):
        result['notes'].append('Evidence file could not be loaded: ' + str(evidence.get('_load_error', '')))
        return maybe_inferred(result, configured_signal)
    pins = evidence.get('pins') if isinstance(evidence.get('pins'), dict) else {}
    if not pins:
        result['notes'].append(str(evidence.get('_missing_reason') or 'No package pin evidence is loaded.'))
        return maybe_inferred(result, configured_signal)
    pin_data = pins.get(pin_name) or pins.get(pin_name.lower()) or pins.get(pin_name.upper())
    if not isinstance(pin_data, dict):
        result['notes'].append('Evidence file is loaded, but this pin is not present in it.')
        return maybe_inferred(result, configured_signal)
    signals = normalize_signals(pin_data.get('signals', []))
    result['available_functions'] = sorted({item['function'] for item in signals if item.get('function')})
    result['matching_signals'] = [item for item in signals if supports(item, requested)]
    if isinstance(pin_data.get('notes'), list):
        result['notes'].extend(str(item) for item in pin_data['notes'] if str(item).strip())
    if result['matching_signals']:
        result['verification_status'] = 'verified'
        result['support_status'] = 'supported'
        result['available'] = True
    elif signals:
        result['verification_status'] = 'contradicted'
        result['support_status'] = 'not-supported-by-evidence'
        result['available'] = False
        result['notes'].append('The evidence file lists this pin, but not the requested function.')
    else:
        result['notes'].append('The evidence file lists this pin without signal/function rows.')
        maybe_inferred(result, configured_signal)
    return result


def load_or_missing(path: Path, searched: list[Path], missing_reason: str) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.exists():
        return missing(searched, missing_reason)
    try:
        data = load_evidence(resolved)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            'pins': {},
            'source': {},
            '_evidence_file': str(resolved),
            '_searched_paths': as_strings(searched),
            '_load_error': str(exc),
        }
    data['_evidence_file'] = str(resolved)
    data['_searched_paths'] = as_strings(searched)
    return data


def missing(searched: list[Path], reason: str) -> dict[str, Any]:
    return {
        'pins': {},
        'source': {},
        '_evidence_file': '',
        '_searched_paths': as_strings(searched),
        '_missing_reason': reason,
    }


def normalize_signals(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    signals = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get('name') or item.get('signal') or '').strip()
        signals.append(
            {
                'name': name,
                'function': normalize_function(str(item.get('function') or function_from_signal(name))),
                'af': str(item.get('af') or item.get('alternate_function') or '').strip(),
                'evidence': str(item.get('evidence') or item.get('source') or '').strip(),
            }
        )
    return signals


def supports(signal: dict[str, str], requested: str) -> bool:
    if normalize_function(signal.get('function', '')) == requested:
        return True
    return signal_matches(signal.get('name', ''), requested)


def function_from_signal(signal: str) -> str:
    text = signal.strip().lower()
    if not text:
        return ''
    if text.startswith('gpio'):
        return 'gpio-output' if 'output' in text else 'gpio'
    if text.startswith('i2c'):
        return 'i2c'
    if text.startswith('spi'):
        return 'spi'
    if text.startswith('usart') or text.startswith('uart'):
        return 'uart'
    if text.startswith('adc'):
        return 'adc'
    if text.startswith('can'):
        return 'can'
    if text.startswith('tim') and '_ch' in text:
        return 'pwm'
    if text.startswith('tim'):
        return 'timer'
    return ''


def signal_matches(signal: str, function: str) -> bool:
    text = signal.strip().lower()
    if function == 'gpio-output':
        return 'gpio_output' in text or 'gpio output' in text
    if function == 'uart':
        return text.startswith('usart') or text.startswith('uart')
    if function == 'pwm':
        return text.startswith('tim') and '_ch' in text
    if function == 'timer':
        return text.startswith('tim')
    return bool(function and function in text)


def maybe_inferred(result: dict[str, Any], configured_signal: str) -> dict[str, Any]:
    requested = str(result.get('requested_function', ''))
    if configured_signal and signal_matches(configured_signal, requested):
        result['verification_status'] = 'inferred'
        result['support_status'] = 'configured-in-project'
        result['available'] = None
        result['matching_signals'] = [
            {
                'name': configured_signal,
                'function': requested,
                'af': '',
                'evidence': 'Existing CubeMX .ioc assignment only; verify against package pin data.',
            }
        ]
        result['notes'].append('Existing .ioc assignment matches the request, but package evidence is not loaded.')
    return result


def sanitize_part(part: str) -> str:
    return ''.join(ch for ch in str(part or '').strip() if ch.isalnum() or ch in {'-', '_'})


def as_strings(paths: list[Path]) -> list[str]:
    return [str(path.resolve()) for path in paths]


def dedupe(paths: list[Path]) -> list[Path]:
    result = []
    seen = set()
    for path in paths:
        key = str(path.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result
