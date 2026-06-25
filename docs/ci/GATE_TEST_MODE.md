# FABRIC_GATE_TEST_MODE — Sign-Off Policy

## Overview

`FABRIC_GATE_TEST_MODE` is a flag that controls whether the mandatory security
regression gate skips expensive browser and frontend operations. When set to
`1`, the following checks are **skipped**:

| Check | Script | Risk if Skipped |
|---|---|---|
| Critical E2E skip-valve guard | `assert-no-skipped-critical-e2e.mjs` | Skipped critical E2E tests go undetected |
| OpenAPI contract drift check | `make contract-drift` | API contract regressions go undetected |
| Deprecation marker standardization | `standardize_deprecation_markers.py` | Deprecated code not tracked |
| Frontend contract tests | `vitest + assert-no-placeholder-contract-tests.mjs` | Frontend contract regressions go undetected |

## Default Behavior (RB-6 Fix)

**Default: `FABRIC_GATE_TEST_MODE=0`** (all checks run).

Prior to the RB-6 fix, the default was `1`, meaning the E2E skip-valve guard
had **never run in CI** for the v1.2.0 release cycle. This was identified as
a release blocker in the production readiness audit.

## When Is Test Mode Permitted?

`FABRIC_GATE_TEST_MODE=1` is permitted **only** in the following cases:

1. **Local developer machines** that do not have `node` or `pnpm` installed.
2. **Temporary CI bypass** with explicit sign-off (see below).

It is **never** permitted to set `FABRIC_GATE_TEST_MODE=1` permanently in
CI environment variables (e.g., GitHub Actions secrets, `.env.ci`).

## Sign-Off Process for Temporary CI Bypass

If a CI environment genuinely cannot run the frontend checks (e.g., a
dedicated backend-only runner), the following sign-off is required:

1. Create a GitHub issue titled `[CI] FABRIC_GATE_TEST_MODE=1 bypass — <reason>`.
2. The issue must be approved by the **Security Lead** and **Platform Lead**.
3. The bypass must include an **expiry date** (maximum 5 business days).
4. The issue number must be referenced in the CI configuration change.

## Pre-Flight Check

When `FABRIC_GATE_TEST_MODE=0`, the gate script performs a pre-flight check
to verify that `node` and `pnpm` are available. If either is missing, the
gate exits with a clear error message rather than silently skipping the checks.

```
ERROR: FABRIC_GATE_TEST_MODE=0 but 'node' is not available.
       Install Node.js or set FABRIC_GATE_TEST_MODE=1 with owner sign-off.
       See docs/ci/GATE_TEST_MODE.md for the sign-off process.
```

## Local Development

To run the gate locally on a machine without frontend tooling:

```bash
FABRIC_GATE_TEST_MODE=1 bash scripts/ci/mandatory_security_regression_gate.sh
```

This is acceptable for local development but must not be used in CI without
the sign-off process described above.
