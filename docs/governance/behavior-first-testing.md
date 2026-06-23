# Behavior-First Testing Strategy

## Operating Principle

> **No critical behavior exists unless it is tested.**

---

## Enforcement Rule

- **Intended behavior passes.**
- **Unintended behavior fails.**
- **Untested behavior is not production-ready.**

---

## Strategy

This repository uses tests as the **executable contract** for intended behavior.

The goal is not just to add more tests. The goal is to make the test suite the executable definition of how the system is supposed to behave.

Every major repo domain must have a clear behavioral contract. The canonical registry lives in `contracts/behavior-contract.yaml` and is enforced by `make check-behavior-contract`:

| Domain | Contract Location | What It Proves | Capabilities |
|---|---|---|---|
| Auth behavior | `tests/security/`, `tests/contract/`, `apps/web/src/auth/`, `apps/web/src/contexts/`, `apps/web/src/hooks/` | Allowed auth paths succeed; invalid paths fail closed | 6 |
| Tenant isolation | `tests/security/`, `services/*/tests/test_cross_tenant_hostile_behavioral.py` | Cross-tenant access is denied; same-tenant access succeeds | 5 |
| API access rules | `tests/contract/`, `contracts/openapi/` | Endpoints enforce authentication, authorization, and shape | 1 |
| Configuration validity | `tests/ci/`, `tests/arch/` | Invalid config is rejected at startup or in gates | 1 |
| Environment safety | `tests/contract/test_startup_bypass_guard_contract.py`, `tests/security/test_dev_bypass.py` | Dev bypass flags cannot activate in production | 2 |
| Data boundaries | `tests/security/`, `tests/integration/` | Data is scoped to tenant, user, and role | 1 |
| Failure behavior | `services/layer2-extraction/tests/test_sse_streaming_behavior.py`, `tests/contract/` | Degradation is graceful; errors are safe and structured | 2 |
| Frontend user flows | `apps/web/src/**/*.behavior.test.*`, `apps/web/e2e/behaviors/` | UI states match intended allowed and denied paths | 8 |
| Service-to-service permissions | `tests/contract/`, `tests/integration/` | Internal calls carry and validate tenant context | 1 |
| Production readiness gates | `tests/ci/`, `tests/k8s/`, `make production-readiness-gate` | Every release proves required invariants before deploy | 1 |

**Total: 32 capabilities** across 10 domains. Each capability declares an `allowed` test, a `denied` test, and an explicit `expected_failure_mode`. The ratchet baseline is stored in `config/ci/behavior_contract_baseline.json`.

---

## Standard

The standard is not **"does the code work locally?"**

The standard is:

> **"Does the repo continuously prove that the implementation matches the intended behavior?"**

When the intended behavior is not encoded in tests, the repo creates future troubleshooting debt.

Troubleshooting should not be the primary mechanism for discovering security, configuration, or runtime gaps. Those gaps should surface as **failing tests, failing CI gates, or explicit contract violations before deployment**.

---

## Behavioral Contract Format

For every production-critical workflow, the repo must define:

1. **The intended allowed behavior.**
   - What should happen when a valid actor performs a valid action.
   - This must be encoded as a passing test.

2. **The intended denied behavior.**
   - What should happen when an invalid actor, invalid action, or out-of-scope request occurs.
   - This must be encoded as a passing test that asserts denial.

3. **The expected failure mode for unsafe or out-of-scope behavior.**
   - Error codes, HTTP status codes, exceptions, or safe defaults.
   - The failure mode must be explicit and tested.

4. **The test or gate that proves the behavior before release.**
   - pytest marker, CI job, Makefile target, or pre-commit gate.
   - If the gate is not present, the behavior is not proven.

---

## Fail-Closed Default

If behavior is not explicitly intended, it should **fail closed by default**.

Examples:

- A new endpoint without an auth test is assumed unsafe.
- A repository method without a tenant-scoped test is assumed leaking.
- A configuration flag without a validity test is assumed dangerous.
- An agent workflow without output schema validation is assumed ungoverned.

---

## Naming and Discovery

Behavior-first tests should be discoverable by name:

| Pattern | Use For | Examples |
|---|---|---|
| `test_*_behavior.py` | Backend behavior contracts | `services/layer2-extraction/tests/test_sse_streaming_behavior.py` |
| `test_*_hostile_behavioral.py` | Runtime hostile behavior contracts | `services/layer2-extraction/tests/test_cross_tenant_hostile_behavioral.py` |
| `*.behavior.test.ts` | Frontend component/hook behavior contracts | `apps/web/src/hooks/useAuth.behavior.test.ts` |
| `*.behavior.spec.ts` | E2E journey behavior contracts | `apps/web/e2e/behaviors/j1-ingestion.behavior.spec.ts` |
| `test_*_contract.py` | API and schema contracts | `tests/contract/test_error_envelope_consistency.py` |
| `test_*_hostile.py` | Negative security and isolation tests | `tests/security/test_hostile_tenant_endpoint_family_contracts.py` |
| `test_*_gate.py` | CI and release gates | `tests/k8s/test_production_blockers.py` |

Tests that assert allowed paths should use names like:

```python
def test_authenticated_user_can_read_own_tenant_data():
```

Tests that assert denied paths should use names like:

```python
def test_unauthenticated_request_is_rejected_with_401():
def test_cross_tenant_read_fails_closed_with_403():
```

---

## Checklist for New Capabilities

Before merging a production-critical capability:

- [ ] The intended allowed behavior has a passing test.
- [ ] The intended denied behavior has a passing test.
- [ ] The failure mode is explicit and tested.
- [ ] A CI gate or marker exists to enforce the behavior on every PR.
- [ ] If the behavior spans layers, a cross-layer contract test exists.
- [ ] If the behavior is security-sensitive, a hostile test exists.

---

## Readiness Ladder: From Static Resolution to Production Ready

"Ready" is **not** a single boolean. It is a four-stage ladder. Each stage is a
strictly stronger claim than the one below it, and **no stage may be skipped**.
Critically, **a passing static contract (Stage 1) does not by itself authorize a
"ready" claim** — that requires Stages 2 and 3 as well.

| Stage | Claim | Proven by | Command |
|---|---|---|---|
| 1. Static contract resolved | Every capability *maps to* an allowed + denied test that exists | `scripts/ci/check_behavior_contract.py` (static, no pytest) | `make check-behavior-contract` |
| 2. Behavior tests executed | Those tests *actually run and pass* (not just resolve on paper) | pytest JUnit run of the critical-behavior suites | `pnpm run test:critical-behaviors` |
| 3. Readiness audit passed | Executed results are aggregated, **skips/xfails are controlled**, and a GREEN/YELLOW/RED status is emitted | `scripts/ci/behavior_readiness_audit.py` | `make check-behavior-readiness-audit` / `make gate-behavior-readiness` |
| 4. Production ready | The full canonical production gate passes **with** the behavior readiness audit wired in | policy-driven release gate + production readiness | `make production-readiness-gate` (profiles include `behavior-readiness`) |

### Why each stage is necessary

- **Stage 1 alone is insufficient.** A contract can resolve to a test that
  exists but is skipped, xfailed, or never executed. Static resolution proves
  *intent is mapped*, not that *behavior holds*.
- **Stage 2 alone is insufficient.** Tests can pass while silently skipping
  matrix cells (e.g. a route file moved and the test fell back to `pytest.skip`).
  A green pytest run can still hide an unexecuted contract.
- **Stage 3 closes the skip loophole.** The readiness audit fails closed on any
  unexpected skip or xfail. A skip is tolerated **only** if it is either:
  - **benign + not-applicable** (matched by `benign_skip_patterns` in
    `config/ci/behavior_readiness_waivers.yaml`, e.g. a read-only endpoint
    family has no write methods), or
  - covered by an **active, owned, time-boxed waiver** in the same file.
  Anything else (route-not-found, import error, missing dependency, expired
  waiver) produces **RED**.
- **Stage 4 is the only stage that authorizes release.** It runs the canonical
  production-readiness gate with `behavior-readiness` wired into the
  `mainline-full`, `release-candidate`, `production-core`, and
  `tier0-production-safety` profiles.

### Status semantics (Stage 3 audit output)

The audit writes a machine-readable report to
`artifacts/readiness/behavior-readiness-audit.json` containing the gate name,
command, pass/fail, `passed_count`, `failed_count`, `skipped_count`,
`xfailed_count`, `waiver_references`, `benign_skips`, and `final_status`:

| Status | Meaning |
|---|---|
| **GREEN** | All executable gates pass; only benign not-applicable skips remain. |
| **YELLOW** | All executable gates pass, but one or more active documented waivers remain. |
| **RED** | Any failure, OR any unwaived/expired skip/xfail, OR the static contract is unresolved. |

### Hard rule

> Do **not** claim the repository is "ready" or "production-ready" from a passing
> static contract alone. A "ready" claim requires the canonical readiness path to
> **execute** behavior contracts (Stage 2) and the readiness audit to report
> **GREEN or YELLOW with all skips/xfails resolved or explicitly waived**
> (Stage 3). Production release requires Stage 4.

---

## Relation to Other Documents

- For tactical test execution commands, markers, and coverage targets, see [`docs/reference/testing-strategy.md`](../../docs/reference/testing-strategy.md).
- For layer-specific testing rules and validation commands, see [`AGENTS.md`](../../AGENTS.md).
- For security test requirements, see [`tests/security/README.md`](../../tests/security/README.md).
- For contract test conventions, see [`tests/contract/README.md`](../../tests/contract/README.md).

---

**Document Owner:** Value Fabric Engineering  
**Review Cycle:** Quarterly  
**Next Review:** September 19, 2026
