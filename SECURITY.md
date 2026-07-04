# Security Policy

## Scope and threat model

This project is a **hardware-development assistant workspace**. It inspects
projects, gathers chip documentation, advises on CubeMX pin/peripheral config,
generates firmware code, and prepares **safety-gated** plans for
build/flash/debug/observe actions on embedded targets.

The safety architecture is built around two ideas:

1. **A blocked-by-default executor.** `tools/hardware_action_executor.py` keeps
   real hardware backends blocked (`blocked-real-backend-not-enabled`) and only
   permits `fake`/simulator/build paths until backend-specific bench validation
   is completed. This is the sanctioned path.
2. **Confirmation tokens** that bind a prepared action to its exact parameters
   (target, probe, voltage, current limit, erase scope, recovery, artifact hash,
   backend, ...).

## Confirmation token model — what it does and does NOT guarantee

The confirmation token is computed as:

```
"hwc1-" + sha256(json(normalized plan fields))[:32]
```

See `embeddedskills/safety_gate.py:confirmation_token` and
`tools/hardware_action_plan.py:confirmation_token` (identical by design).

**What the token guarantees:**

- **Parameter integrity / anti-tampering.** If any bound field (target, voltage,
  erase scope, artifact hash, ...) changes after the plan is generated, the
  recomputed token will not match and the action is blocked
  (`blocked-plan-token-mismatch`).
- **Audit binding.** Token consumption is recorded so replays of the *same*
  token against the *same* workspace ledger are detected.

**What the token does NOT guarantee (known limitation):**

- **It is not cryptographic proof of human approval.** The token is a keyless
  SHA-256 hash over fields the caller already knows. Any party (including an
  autonomous agent) that can see or reconstruct the plan fields can recompute a
  matching token. There is no HMAC secret and no out-of-band confirmation step.

In other words: the token proves *"this token matches this plan"*, not
*"a human reviewed and approved this plan."* Real-world safety for irreversible
operations (flash, erase, debug, bus writes) depends on:

1. A human actually reading the rendered plan before supplying the token, **and**
2. Real hardware backends remaining disabled unless explicitly enabled in a
   bench-validated environment.

### Defense-in-depth for real flashing

The pyOCD backend helper (`tools/backends/pyocd_backend.py:execute_flash_action`)
**fails closed**: it refuses to perform a real flash unless **both**

- the environment variable `HARDWARE_BUTLER_ENABLE_REAL_FLASH=1` is set, **and**
- a non-empty confirmation token is supplied.

The GUI never calls a backend's `flash()` directly; it shells out to the gated
`bench-runbook` CLI so the confirmation flow cannot be bypassed from the UI.

### Hardening roadmap

A future revision may replace the keyless token with an HMAC over a per-session
secret that is only materialized through an interactive human-confirmation step,
so the token cannot be self-minted by an automated caller. Until then, treat
"gated" as **"integrity-bound and logged,"** not **"human-authorized."**

## Reporting a vulnerability

Please open a private security advisory on the repository, or contact the
maintainer (`LeoKemp223`) directly. Do not file public issues for undisclosed
vulnerabilities. We aim to acknowledge reports within a few days.

When reporting, include:

- affected file(s) and version/commit,
- a minimal reproduction or proof of concept,
- the impact you observed (e.g. arbitrary command execution, ungated hardware
  action, file disclosure).
