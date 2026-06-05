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

Every major repo domain must have a clear behavioral contract:

| Domain | Contract Location | What It Proves |
|---|---|---|
| Auth behavior | `tests/security/`, `tests/contract/` | Allowed auth paths succeed; invalid paths fail closed |
| Tenant isolation | `tests/security/`, `tests/integration/` | Cross-tenant access is denied; same-tenant access succeeds |
| API access rules | `tests/contract/`, `contracts/openapi/` | Endpoints enforce authentication, authorization, and shape |
| Configuration validity | `tests/ci/`, `tests/arch/` | Invalid config is rejected at startup or in gates |
| Environment safety | `tests/contract/test_startup_bypass_guard_contract.py` | Dev bypass flags cannot activate in production |
| Data boundaries | `tests/security/`, `tests/integration/` | Data is scoped to tenant, user, and role |
| Failure behavior | `tests/chaos/`, `tests/contract/` | Degradation is graceful; errors are safe and structured |
| Frontend user flows | `apps/web/src/**/*.behavior.test.*` | UI states match intended allowed and denied paths |
| Service-to-service permissions | `tests/contract/`, `tests/integration/` | Internal calls carry and validate tenant context |
| Production readiness gates | `tests/ci/`, `make production-readiness-gate` | Every release proves required invariants before deploy |

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

| Pattern | Use For |
|---|---|
| `test_*_behavior.py` | Backend behavior contracts |
| `*.behavior.test.ts` | Frontend behavior contracts |
| `test_*_contract.py` | API and schema contracts |
| `test_*_hostile.py` | Negative security and isolation tests |
| `test_*_gate.py` | CI and release gates |

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

## Relation to Other Documents

- For tactical test execution commands, markers, and coverage targets, see [`docs/reference/testing-strategy.md`](../../docs/reference/testing-strategy.md).
- For layer-specific testing rules and validation commands, see [`AGENTS.md`](../../AGENTS.md).
- For security test requirements, see [`tests/security/README.md`](../../tests/security/README.md).
- For contract test conventions, see [`tests/contract/README.md`](../../tests/contract/README.md).

---

**Document Owner:** Value Fabric Engineering  
**Review Cycle:** Quarterly  
**Next Review:** September 19, 2026
