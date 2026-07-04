# Release Process

Use this checklist when publishing a GitHub release or cutting a launch branch.

## 1. Prepare The Tree

One-command local verification:

```powershell
python tools\release_verify.py
```

For quick iteration on the onboarding/demo/plugin path:

```powershell
python tools\release_verify.py --profile quick
```

The full profile expands to:

```powershell
python tools\package_hardware_butler_plugin.py
python tools\hardware_butler.py guide --root tests\fixtures\cubemx-basic
python tools\hardware_butler.py doctor --root tests\fixtures\cubemx-basic --json
python tools\hardware_butler.py ask --root tests\fixtures\cubemx-basic --question Mcu.Package --json
python plugins\hardware-development-butler\scripts\validate_package.py
ruff check tools/ tests/
mypy tools/ --config-file mypy.ini
pytest tests/ -v --basetemp=.tmp-pytest-current
python tests\validate_hardware_butler.py
python -m pip install -e . --dry-run
python -m pip install -r requirements-dev.txt --dry-run
python -m pip install -r requirements-all.txt --dry-run
git diff --check
```

To print the current command list directly from the tool:

```powershell
python tools\release_verify.py --profile full --list
```

For a source-workspace smoke test, create a clean candidate tree without the
root `embeddedskills/` checkout and confirm the packaged plugin runtime is used.
The launch checklist records the latest clean-tree result.

## 2. Review The Boundary

- `embeddedskills/` remains ignored as an independent checkout.
- `plugins/hardware-development-butler/scripts/embeddedskills/` is the bundled runtime mirror.
- Real hardware actions remain blocked, simulated, or confirmation-gated.
- Generated outputs such as `.hardware-butler/`, `docs/inspections/`, caches, and local study notes stay ignored.

## 3. Commit

Recommended first launch commit:

```powershell
git add .
git status --short
git commit -m "chore: prepare hardware butler for GitHub launch"
```

Review staged files before committing. Do not stage the root `embeddedskills/`
checkout unless the repository strategy has explicitly changed to a submodule or
tracked source directory.

## 4. Push And Verify

```powershell
git push origin main
```

After pushing, verify that GitHub Actions runs the matrix in
`.github/workflows/ci.yml` and passes on `main`.

Then run the read-only remote launch audit. It exits nonzero until `main`
matches local HEAD, the GitHub About metadata matches
`docs/GITHUB_REPOSITORY_SETTINGS.md`, and the latest `ci.yml` run on `main`
completed successfully.

```powershell
python tools\github_launch_audit.py --json
```

For an operator-friendly checklist, run the same command without `--json`; any
failing check prints a `next:` line with the exact follow-up action.
If the audit cannot reach GitHub or the configured remote, `--json` still emits
a structured `audit.runtime` failure so scripts can surface the infrastructure
problem without parsing stderr.

## 5. Tag

Tag only after CI is green:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

Create the GitHub release from `CHANGELOG.md` and call out that real hardware
execution is still confirmation-gated or planned-gated.
