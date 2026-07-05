# GitHub Launch Checklist

## Repository Shape

- [x] `embeddedskills/` is either a clean submodule, a tracked plugin runtime mirror, or documented as an external prerequisite through `HW_BUTLER_EMBEDDEDSKILLS_ROOT`.
- [x] Package metadata does not accidentally include the ignored root `embeddedskills/` checkout.
- [x] Generated `build/`, `dist/`, `.hardware-butler/`, caches, and virtual environments are ignored.
- [x] README starts with a clear value proposition and a safe first command.
- [x] A no-hardware demo path exists for first-time users without a board project.
- [x] Install/runtime choices are documented in `docs/INSTALL.md`.
- [x] Hardware understanding workflow is documented as source-backed evidence, CubeMX, firmware, and gated bench use.
- [x] Release process and repository settings are documented.
- [x] `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `SUPPORT.md`, and `CODE_OF_CONDUCT.md` exist.

## Verification

- [x] `python tools\release_verify.py --profile quick`
- [x] `python tools\release_verify.py` is documented as the one-command full local release gate.
- [x] `ruff check tools/ tests/`
- [x] `mypy tools/ --config-file mypy.ini`
- [x] `pytest tests/ -v --basetemp=.tmp-pytest-current`
- [x] `python tests\validate_hardware_butler.py`
- [x] `python tools\package_hardware_butler_plugin.py`
- [x] `python plugins\hardware-development-butler\scripts\validate_package.py`
- [x] `python tools\github_launch_audit.py --json` exists as the read-only remote launch verifier.
- [x] Clean candidate tree without root `embeddedskills/` passes package, pytest, butler validation, and plugin validation using the packaged runtime mirror.
- [x] CI runs lint, mypy, tests with a fresh basetemp, butler validation, and plugin validation.

## Safety

- [x] Real flash, erase, reset, debug, bus writes, and long observation remain blocked or confirmation-gated.
- [x] Hardware tests remain opt-in behind `--run-hardware`.
- [x] Security policy explains confirmation-token limitations.

## GitHub

- [x] CI workflow exists and includes plugin package validation.
- [x] Dependabot configuration exists for pip and GitHub Actions.
- [x] Issue forms are available.
- [x] Pull request template includes verification and safety checks.
- [x] Generated release notes are grouped by `.github/release.yml`.
- [ ] `python tools\github_launch_audit.py --json` reports `"status": "ok"` against GitHub.
- [ ] CI passes on `main`.
- [ ] Repository description, topics, and homepage are set in GitHub settings.
