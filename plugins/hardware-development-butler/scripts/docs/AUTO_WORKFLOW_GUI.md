# Hardware Butler Auto Workflow And GUI

This is the simplest entry point for the workspace. It turns the existing hardware, firmware, and safety tools into one connected loop:

1. Inspect the selected project.
2. Write `.hardware-butler/project-state.json`.
3. Show the current workflow phase.
4. Recommend exactly one next safe command.
5. Run only safe automation unless the existing confirmation gates are used.

## One Command

Use `auto` when you want the butler to do the safe first pass for you:

```powershell
python tools\hardware_butler.py auto --root <project-root> --out-dir docs\inspections\<project-name> --json
```

`auto` can generate onboarding reports and project state. It does not flash, erase, debug, reset, transmit bus frames, scan networks, or bypass hardware action tokens.

Use `next-step` when you only want the recommendation:

```powershell
python tools\hardware_butler.py next-step --root <project-root> --json
```

The response includes:

- `status`: the current project workflow status.
- `phases`: project detection, safe onboarding, configuration, safe discovery, and bench readiness.
- `next_step`: the one recommended command, with `safe_by_default` and `touches_hardware` flags.
- `state_path`: the persisted `.hardware-butler/project-state.json` file.

## Desktop UI

Install dependencies, then launch the workflow console:

```powershell
pip install -r requirements.txt
python gui\hardware_agent_ui.py
```

The UI provides:

- Project root selector.
- Status cards for backend, CubeMX, safety, and workflow state.
- Workflow phase table.
- Next-step recommendation panel.
- Buttons for `Auto`, `Next Step`, `Doctor`, `Detect`, and `Bench Runbook`.

The UI runs CLI commands through argument lists with `shell=False`. It intentionally does not expose direct real-flash or real-debug buttons.

## Safe Daily Loop

```powershell
python tools\hardware_butler.py auto --root <project-root> --out-dir docs\inspections\<project-name> --json
python tools\hardware_butler.py next-step --root <project-root> --json
python gui\hardware_agent_ui.py
```

When the project reaches bench work, generate a no-hardware runbook first:

```powershell
python tools\hardware_butler.py bench-runbook --root <project-root> --action build-flash --json
```

Real hardware actions remain planned-gated and require the existing explicit confirmation-token flow.
