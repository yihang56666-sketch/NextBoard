# Package Pin Evidence Implementation Plan

Goal: add explicit package pin evidence to CubeMX pin advice.

Scope:
- Add `tools/pin_capabilities.py` to load local JSON evidence.
- Add `advise-pin --pin-evidence` and JSON/Markdown output.
- Test verified, contradicted, and unknown evidence states.
- Update product doctor, plugin validation, package sync, and docs.

Safety boundary:
- Do not infer vendor pin mux from memory.
- Missing evidence remains `unknown` or `.ioc`-only `inferred`.
- Real flash/debug/observe remains `planned-gated`.

Validation:
- `python tests\validate_hardware_butler.py`
- `python tools\package_hardware_butler_plugin.py`
- `python plugins\hardware-development-butler\scripts\tests\validate_hardware_butler.py`
- `python plugins\hardware-development-butler\scripts\validate_package.py`
