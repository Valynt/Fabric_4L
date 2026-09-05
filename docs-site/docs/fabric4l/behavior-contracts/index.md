---
owner: platform-team
status: active
last_reviewed: 2026-06-07
---

# Behavior Contracts

Behavior contracts are the executable definition of what the ValuePact platform is allowed to do—and what it must refuse to do. They encode intended behavior as passing tests, unintended behavior as failing tests, and untested behavior as **not production-ready**.

This section is the authoritative reference for how behavior-first testing governs every layer of the six-layer architecture, from ingestion through benchmarks.

## Why behavior-first testing matters

Traditional testing asks: "Does the code work?"

Behavior-first testing asks: **"Does the repo continuously prove that the implementation matches the intended behavior?"**

When behavior is not encoded in tests, gaps are discovered through troubleshooting, incident response, or security audits. That is too late. The behavior contract strategy ensures gaps surface as **failing tests, failing CI gates, or explicit contract violations before deployment**.

The canonical governance statement lives in `docs/governance/behavior-first-testing.md`. This section translates that policy into practical layer-by-layer guidance.

## Who should read this section

| Role | Why it matters |
|---|---|
| **Backend engineers** | Every service change must include or preserve behavior contracts. This section defines the markers, naming conventions, and coverage standards. |
| **Frontend engineers** | UI behavior is part of the 32-capability contract. E2E and component behavior tests are governed by the same readiness ladder. |
| **Security engineers** | Hostile tests, tenant boundary tests, and OWASP coverage are first-class behavior contracts. This section defines the waiver policy and audit semantics. |
| **Platform / SRE** | The readiness ladder and production-readiness gate determine whether a build can deploy. This section is the operational contract for release safety. |
| **Technical writers** | Behavior contracts are a source of truth for what the system does and does not allow. Use this section to keep docs aligned with tested behavior. |

## Core principles

| Principle | Meaning |
|---|---|
| **Intended behavior passes** | Every allowed action has a passing test that proves it works. |
| **Intended denial passes** | Every disallowed action has a passing test that proves it is blocked. |
| **Untested behavior is not production-ready** | If there is no test, the behavior does not exist for release purposes. |
| **Fail closed by default** | If behavior is not explicitly intended, the system must reject it. |

!!! warning "Do not claim readiness from static resolution alone"
    A passing static contract (Stage 1) proves that tests *map* to capabilities, not that they *execute and pass*. See [Gate Registry](gate-registry.md) for the full four-stage readiness ladder.

## What behavior contracts cover

The platform maintains **32 capabilities** across **10 domains**, tracked in `config/ci/behavior_contract_baseline.json`:

| Domain | Capabilities | Example |
|---|---|---|
| Auth behavior | 6 | Allowed auth paths succeed; invalid paths fail closed |
| Tenant isolation | 5 | Cross-tenant access is denied; same-tenant access succeeds |
| API access rules | 1 | Endpoints enforce authentication, authorization, and shape |
| Configuration validity | 1 | Invalid config is rejected at startup or in gates |
| Environment safety | 2 | Dev bypass flags cannot activate in production |
| Data boundaries | 1 | Data is scoped to tenant, user, and role |
| Failure behavior | 2 | Degradation is graceful; errors are safe and structured |
| Frontend user flows | 8 | UI states match intended allowed and denied paths |
| Service-to-service permissions | 1 | Internal calls carry and validate tenant context |
| Production readiness gates | 1 | Every release proves required invariants before deploy |

Each capability declares:

1. An **allowed** test
2. A **denied** test
3. An explicit **expected failure mode** (HTTP status, exception, safe default)
4. The **gate** that proves it before release

## Sections

- [Critical Behaviors](critical-behaviors.md) — What makes a behavior critical, layer-by-layer examples, and the behavior-debt process.
- [Test Strategy](test-strategy.md) — The test pyramid, marker semantics, and when to use each test type.
- [Gate Registry](gate-registry.md) — The four-stage readiness ladder, commands, waiver policy, and audit semantics.

## Quick validation commands

```bash
# Verify the static behavior contract is resolved (no test execution)
make check-behavior-contract

# Run critical behavior tests
pnpm run test:critical-behaviors

# Run the readiness audit (emits GREEN/YELLOW/RED)
make check-behavior-readiness-audit

# Full production readiness gate (required before release)
make production-readiness-gate
```

!!! tip "Narrow first, then broaden"
    When validating changes, start with the smallest relevant marker (e.g., `pytest -m unit` for pure logic), then expand to integration, contract, and finally backend-integrated suites. See [Test Strategy](test-strategy.md) for the full marker reference.

## Related documentation

- `docs/governance/behavior-first-testing.md` — Canonical governance statement
- `docs/testing/` — Canonical testing governance and behavior-readiness guidance
- `pytest.ini` — Marker definitions and test profiles
- `config/ci/behavior_contract_baseline.json` — Ratchet baseline (do not regress)
- `config/ci/behavior_readiness_waivers.yaml` — Skip and xfail waiver register
