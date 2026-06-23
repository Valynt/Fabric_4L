# Gate Engineering Framework

This directory is the source of truth for release-readiness gates and versioned contracts.

## Machine-readable files

| File | Purpose |
|---|---|
| `gate-schema.json` | JSON Schema for a single gate definition. |
| `contract-schema.json` | JSON Schema for a single contract definition. |
| `gate-registry.json` | Inventory of all gates: criteria, measurement, owners, enforcement points. |
| `contract-inventory.json` | Inventory of all contracts: syntax, semantics, invariants, owners, validation, enforcement. |
| `example-release-readiness-report.json` | Example blocked report with exceptions, warnings, and blocking results. |

## Policy files

| File | Purpose |
|---|---|
| `exception-policy.md` | Rules for overriding a gate, including expiration, separation of duties, and evidence retention. |
| `promotion-policy.md` | Environment promotion paths, profiles, blockers, and artifact tagging rules. |
| `canary-policy.md` | Canary traffic progression, auto-rollback triggers, and inconclusive-canary handling. |
| `rollback-recovery-policy.md` | Rollback readiness gates, authority, idempotency, and recovery objectives. |
| `contract-versioning-policy.md` | Contract versioning, breaking-change RFC, compatibility windows, and sunset. |
| `ai-agent-evaluation-gates.md` | Required AI/agent eval evidence, critical-error thresholds, and human-review triggers. |
| `security-tenant-isolation-gates.md` | Release-blocking security and tenant-isolation invariants and static/live gates. |
| `data-migration-gates.md` | Migration checklist, expand-and-contract rules, and destructive cleanup policy. |
| `observability-slo-gates.md` | Required SLOs, trace dimensions, alert validation, and breach actions. |
| `e2e-gate-matrix.md` | Critical end-to-end paths that must be exercised before and after release. |

## Enforcement wiring

| Component | Location |
|---|---|
| Validator / report generator | `scripts/ci/gate_engineering_validator.py` |
| Failure-injection tests | `tests/ci/test_gate_engineering.py` |
| npm scripts | `package.json` — `gate-engineering:validate`, `gate-engineering:test` |
| Generated report example | `artifacts/release/gate-results/2026-06-19-all-passing/release-readiness-report.{json,md}` |

## Usage

Validate the registries:

```bash
python scripts/ci/gate_engineering_validator.py validate
```

Generate a release-readiness report from gate results:

```bash
python scripts/ci/gate_engineering_validator.py report \
  --release-id <id> \
  --artifact-digest <sha256> \
  --commit-sha <sha> \
  --environment <env> \
  --risk-class <class> \
  --artifact-dir <dir> \
  --output-dir <dir>
```

Run the failure-injection tests:

```bash
python -m pytest tests/ci/test_gate_engineering.py -v
```

## Principles

- Every gate is explicit, measurable, evidence-backed, reproducible, fail-closed, owner-assigned, auditable, versioned, and time-bounded.
- No manual approvals without evidence.
- No synthetic success bypassing real components.
- Tenant isolation and auth boundaries are never overridable.
