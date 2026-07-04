# GitHub Repository Settings

Suggested settings for the public repository page.

## About

Description:

```text
Safe-first embedded hardware development workspace for project scanning, CubeMX/build discovery, evidence indexing, firmware planning, bench runbooks, and gated hardware actions.
```

Homepage:

```text
https://github.com/LeoKemp223/NextBoard#readme
```

Topics:

```text
embedded, hardware, stm32, cubemx, firmware, freertos, jlink, openocd, probe-rs, serial, can, safety, codex-plugin
```

## Features

Recommended:

- Enable Issues.
- Enable Discussions only if you want public Q&A.
- Enable Dependabot alerts and security updates.
- Keep Actions enabled for pull requests and pushes to `main`.

## Branch Protection

For `main`, require:

- Pull request before merge.
- Status checks from the `CI` workflow.
- Conversation resolution before merge.

If the repository starts private and becomes public later, re-run the clean
candidate tree smoke test after the visibility change.
