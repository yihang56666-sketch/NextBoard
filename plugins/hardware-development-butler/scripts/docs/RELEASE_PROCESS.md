# Release Process

Use this checklist when publishing a GitHub release or cutting a launch branch.

## 1. Prepare The Tree

One-command local verification:

```powershell
python tools\release_verify.py
```

The verifier prints one compact `PASS` line per step by default. Add
`--verbose` when you need the full child command output while debugging a
failing gate.

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

Before the real push, you can verify that the currently cached GitHub account
has write access to the configured remote without changing GitHub:

```powershell
python tools\github_launch_audit.py --check-push-only
```

If this reports `Permission to <owner>/<repo>.git denied to <account>`, the
computer can still upload to GitHub, but the active Git credential is not allowed
to push to this repository. Grant that account write access, switch Git
Credential Manager to an account that owns the repository, or change `origin` to
the repository you intend to publish.

```powershell
git push origin main
```

After pushing, verify that GitHub Actions runs the matrix in
`.github/workflows/ci.yml` and passes on `main`.

Then run the read-only remote launch audit. It exits nonzero until `main`
matches local HEAD, the GitHub About metadata matches
`docs/GITHUB_REPOSITORY_SETTINGS.md`, and the latest `ci.yml` run on `main`
completed successfully for the local launch candidate commit.

```powershell
python tools\github_launch_audit.py --json
```

To include the same push-permission preflight in the full launch audit:

```powershell
python tools\github_launch_audit.py --check-push --json
```

For an operator-friendly checklist, run the same command without `--json`; any
failing check prints a `next:` line with the exact follow-up action.
If the audit cannot reach GitHub or the configured remote, `--json` still emits
a structured `audit.runtime` failure so scripts can surface the infrastructure
problem without parsing stderr.

When you only need the expected GitHub About settings and copy-pasteable
commands, or GitHub is temporarily unreachable, print them without contacting
GitHub:

```powershell
python tools\github_launch_audit.py --print-settings
python tools\github_launch_audit.py --print-settings --json
```

If you publish under a different GitHub owner or repository name, pass that
target explicitly so the generated homepage and audit expectations match the
actual public URL:

```powershell
python tools\github_launch_audit.py --owner yihang56666-sketch --repo hardware-agent --print-settings
python tools\github_launch_audit.py --owner yihang56666-sketch --repo hardware-agent --json
```

## 5. Tag

Tag only after CI is green:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

Create the GitHub release from `CHANGELOG.md` and call out that real hardware
execution is still confirmation-gated or planned-gated. GitHub generated release
notes are grouped by `.github/release.yml`; use them as a PR-level cross-check,
then keep the final release body aligned with `CHANGELOG.md`.
