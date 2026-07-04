# Changelog

All notable changes are documented here.

## 0.1.0 - GitHub Launch Candidate

First public launch candidate for Hardware Butler: a safe-first embedded
hardware development workspace that helps users understand projects before
touching real hardware.

### Added

- Safe first-day path through `guide`, `doctor`, `auto`, and `next-step`.
- No-hardware demo flow using `tests/fixtures/cubemx-basic`.
- Source-backed hardware understanding workflow covering project evidence,
  chip documents, CubeMX pin/config review, firmware planning, and bench
  runbooks.
- CLI and GUI entry points for project scanning, evidence Q&A, firmware
  planning, safety audits, and workbench status.
- GitHub CI, issue templates, pull request template, contribution guide,
  support policy, security policy, Dependabot, launch checklist, and release
  process.
- Read-only `github_launch_audit.py` for checking remote HEAD, GitHub About
  metadata, repository topics, and the latest `ci.yml` run.
- Codex plugin runtime packaging with source-sync drift guards.

### Changed

- README and package metadata now use the public `Hardware Butler` identity and
  the same safe-first project description as the GitHub launch settings.
- Dependencies are split into minimal runtime, development verification, UI,
  hardware, AI, reporting, and all-in optional sets.
- Generated inspection/chip outputs are ignored so first-time demo commands do
  not pollute the Git worktree.

### Safety

- Real flash, erase, reset, debug, bus writes, network scans, and long
  observation remain blocked, simulated, confirmation-gated, or planned-gated.
- Hardware tests remain opt-in behind `--run-hardware`.
- Clean GitHub clones can use the bundled
  `plugins/hardware-development-butler/scripts/embeddedskills/` runtime mirror
  without requiring the ignored root `embeddedskills/` checkout.

### Launch Gates

- Push local launch commits to `main`.
- Set GitHub About description, homepage, and topics from
  `docs/GITHUB_REPOSITORY_SETTINGS.md`.
- Wait for `ci.yml` to pass on `main`.
- Rerun `python tools\github_launch_audit.py --json` and require
  `"status": "ok"` before tagging `v0.1.0`.
