# Changelog

All notable changes are documented here.

## 0.1.0 - GitHub Launch Candidate

- Reworked the README around a safe first-day path: `guide`, `doctor`, `auto`, and `next-step`.
- Added install, architecture, command, GUI, and launch-readiness documentation.
- Added GitHub CI, issue templates, pull request template, contribution guide, support policy, and dependency update configuration.
- Added plugin runtime packaging validation and drift guards for the bundled Codex plugin.
- Added clean-clone runtime fallback through `plugins/hardware-development-butler/scripts/embeddedskills/`.
- Split dependencies into minimal runtime, development verification, and full optional integration requirement files.
- Kept real flash, erase, reset, debug, bus writes, and long observation behind confirmation-gated or planned-gated paths.
