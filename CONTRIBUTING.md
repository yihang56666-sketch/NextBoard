# Contributing

Thanks for helping improve Hardware Butler. This project touches embedded
hardware workflows, so changes should stay boring, reviewable, and safe by
default.

## Development Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
python -m pip install -e .
```

## Before Opening a Pull Request

Run the release verifier before sending broad changes:

```powershell
python tools\release_verify.py
```

For quick iteration on the onboarding/demo/plugin path:

```powershell
python tools\release_verify.py --profile quick
```

The most common individual checks are:

```powershell
ruff check tools/ tests/
mypy tools/ --config-file mypy.ini
pytest tests/ -v --basetemp=.tmp-pytest-current
python tests\validate_hardware_butler.py
```

Hardware tests are opt-in:

```powershell
pytest tests/ -v --run-hardware
```

## Safety Rules

Do not bypass `tools/hardware_action_executor.py`,
`embeddedskills/safety_gate.py`, or confirmation-token checks. Real flash,
erase, reset, debug, serial/CAN/network writes, and long-running observation
must stay planned and gated.

## Conduct

Follow `CODE_OF_CONDUCT.md`. For this project, respectful collaboration includes
being precise about hardware evidence and treating unsafe action paths as serious
issues.

If you change packaged runtime files, sync and validate the Codex plugin:

```powershell
python tools\package_hardware_butler_plugin.py
python plugins\hardware-development-butler\scripts\validate_package.py
```
