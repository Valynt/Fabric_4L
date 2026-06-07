---
owner: platform-team
status: active
last_reviewed: 2026-06-07
---

# Gate Registry

Production readiness is not a single boolean. It is a four-stage ladder where each stage is a strictly stronger claim than the one below it, and **no stage may be skipped**. This page defines each stage, the command that proves it, the machine-readable audit output, and the waiver policy for controlled exceptions.

## The four-stage readiness ladder

| Stage | Claim | Proven by | Command |
|---|---|---|---|
| **1. Static contract resolved** | Every capability maps to an allowed + denied test that exists | `scripts/ci/check_behavior_contract.py` (static analysis, no pytest execution) | `make check-behavior-contract` |
| **2. Behavior tests executed** | Those tests actually run and pass | pytest JUnit run of critical-behavior suites | `pnpm run test:critical-behaviors` |
| **3. Readiness audit passed** | Executed results are aggregated, skips/xfails are controlled, and a status is emitted | `scripts/ci/behavior_readiness_audit.py` | `make check-behavior-readiness-audit` |
| **4. Production ready** | The full canonical production gate passes with behavior readiness wired in | Policy-driven release gate | `make production-readiness-gate` |

!!! danger "A passing static contract does not authorize a 'ready' claim"
    Stage 1 alone is insufficient. A contract can resolve to a test that exists but is skipped, xfailed, or never executed. Static resolution proves *intent is mapped*, not that *behavior holds*. A "ready" claim requires Stages 2 and 3, and production release requires Stage 4.

## Stage 1: Static contract resolved

**Command:**
```bash
make check-behavior-contract
```

**What it does:**
- Parses `contracts/behavior-contract.yaml` and the ratchet baseline in `config/ci/behavior_contract_baseline.json`
- Verifies that every declared capability has:
  - An `allowed` test file that exists and is importable
  - A `denied` test file that exists and is importable
  - An explicit `expected_failure_mode`
- Enforces the minimum capability count (32) and required domains (10)

**Outcome:**
- Pass: All capabilities are statically resolvable.
- Fail: Missing test file, missing failure mode, or regression below baseline.

**Baseline (do not regress):**
```json
{
  "min_capabilities": 32,
  "required_domains": [
    "api_access", "auth", "configuration_validity",
    "data_boundaries", "environment_safety", "failure_behavior",
    "frontend_user_flows", "production_readiness",
    "service_to_service", "tenant_isolation"
  ]
}
```

!!! tip "Updating the baseline"
    If you add new capabilities, regenerate the baseline:
    ```bash
    python scripts/ci/check_behavior_contract.py --update-baseline
    ```
    This must be committed in the same PR as the new tests.

## Stage 2: Behavior tests executed

**Command:**
```bash
pnpm run test:critical-behaviors
```

**What it does:**
- Executes the pytest suites mapped to critical behavior capabilities
- Produces JUnit XML for downstream audit consumption
- Fails if any allowed or denied test fails

**Why Stage 1 is insufficient without Stage 2:**
- Tests can exist on disk but be skipped via `pytest.skip`, missing fixtures, or import errors
- A green static contract does not guarantee the test body ever runs
- Stage 2 proves the tests *execute* and *pass*

## Stage 3: Readiness audit passed

**Command:**
```bash
make check-behavior-readiness-audit
# or
make gate-behavior-readiness
```

**What it does:**
- Runs the behavior suites (or consumes their JUnit output)
- Aggregates pass/fail/skip/xfail counts
- Applies the waiver register from `config/ci/behavior_readiness_waivers.yaml`
- Emits a machine-readable report to `artifacts/readiness/behavior-readiness-audit.json`

### Audit output schema

The report contains:

| Field | Description |
|---|---|
| `gate_name` | Name of the audited gate |
| `command` | Command that produced the results |
| `passed_count` | Number of passing tests |
| `failed_count` | Number of failing tests |
| `skipped_count` | Number of skipped tests |
| `xfailed_count` | Number of expected-failure tests |
| `waiver_references` | List of active waiver IDs matched |
| `benign_skips` | Skips matched as not-applicable |
| `final_status` | `GREEN`, `YELLOW`, or `RED` |

### Status semantics

| Status | Meaning | Release authorized? |
|---|---|---|
| **GREEN** | All executable gates pass; only benign not-applicable skips remain | Yes |
| **YELLOW** | All executable gates pass, but one or more active documented waivers remain | Yes, with acknowledged debt |
| **RED** | Any failure, any unwaived/expired skip/xfail, or unresolved static contract | **No** |

!!! warning "YELLOW is a signal, not a failure"
    YELLOW means the platform is releasable but carries active, time-boxed waivers. The owning team must remove the waiver before it expires, or the next audit will downgrade to RED.

## Stage 4: Production ready

**Command:**
```bash
make production-readiness-gate
```

**What it does:**
- Runs the canonical production-readiness gate
- Includes the `behavior-readiness` gate wired into multiple profiles:
  - `mainline-full`
  - `release-candidate`
  - `production-core`
  - `tier0-production-safety`
- Validates additional domains: reliability, observability, recovery, release metadata, tenancy, billing, abuse resistance, audit logging, and production safety

**Outcome:**
- Pass: The build is authorized for promotion to production.
- Fail: Block promotion until all gates pass.

## Waiver policy for skips and xfails

The readiness audit fails closed on any unexpected skip or xfail. A skip is only tolerated if it matches one of two categories defined in `config/ci/behavior_readiness_waivers.yaml`.

### Category 1: Benign + not-applicable

These skips do **not** downgrade GREEN. They represent parametrized matrix cells that legitimately do not apply.

**Current benign pattern:**

| ID | Pattern | Category | Reason |
|---|---|---|---|
| `benign-no-write-methods` | `has no write methods` | `not_applicable` | Read-only endpoint families (e.g., L3 `graph_viz` GET `/graph`) have no POST/PUT/DELETE/PATCH routes, so write-auth assertions do not apply. This is structural, not a coverage gap. |

!!! note "Adding benign patterns"
    Benign patterns require approval from `@value-fabric/security-leads` and must be documented with a structural justification. They are matched as substrings against pytest skip messages.

### Category 2: Active, owned, time-boxed waivers

Presence of any active waiver downgrades the audit from GREEN to YELLOW. Expired waivers downgrade to RED.

**Schema per waiver entry:**

| Field | Requirement |
|---|---|
| `id` | Unique waiver ID |
| `message_pattern` | Substring matched against skip/xfail message |
| `skip_id` | Optional stable test node ID substring |
| `owner` | GitHub team or handle accountable for removal |
| `reason` | Why the skip is temporarily tolerated |
| `ticket` | Tracking issue ID (e.g., `BEHAVIOR-DEBT-L2-001`) |
| `expires_on` | `YYYY-MM-DD`; after this date the waiver fails closed |

**Current active waivers:**

| ID | Owner | Ticket | Expires | Reason |
|---|---|---|---|---|
| `waiver-l2-import-infra` | `@value-fabric/backend-leads` | `BEHAVIOR-DEBT-L2-001` | 2026-09-07 | L2 import chain issues prevent runtime hostile behavioral tests; covered by static contract and `test_tenant_isolation.py` |
| `waiver-l3-import-infra` | `@value-fabric/backend-leads` | `BEHAVIOR-DEBT-L3-001` | 2026-09-07 | L3 import chain issues prevent runtime hostile behavioral tests; covered by `test_tenant_isolation.py` |

!!! danger "Expired waivers are RED"
    When a waiver passes its `expires_on` date, the audit automatically treats matched skips as unwaived and produces RED. There is no auto-renewal. The owning team must resolve the underlying issue or file a new waiver with a new expiration date and fresh justification.

## Hard rules

> Do **not** claim the repository is "ready" or "production-ready" from a passing static contract alone.

A "ready" claim requires:

1. **Static contract resolved** (`make check-behavior-contract`)
2. **Behavior tests executed and passing** (`pnpm run test:critical-behaviors`)
3. **Readiness audit reporting GREEN or YELLOW** with all skips/xfails resolved or explicitly waived (`make check-behavior-readiness-audit`)
4. **Production readiness gate passing** (`make production-readiness-gate`)

## CI integration

The following jobs in `.github/workflows/pr-checks.yml` enforce the ladder:

| Job | Stage | Requirement |
|---|---|---|
| `structural-preflight` | 1 | Import topology, Python contract lint, frontend root policy |
| `contract-checks` | 1 | OpenAPI drift detection and contract coverage |
| `production-readiness-gate` | 4 | `make production-readiness-gate` required for PRs targeting `main` |

## Related documentation

- [Critical Behaviors](critical-behaviors.md) — Layer-by-layer critical behavior examples
- [Test Strategy](test-strategy.md) — Marker definitions and execution commands
- `docs/governance/behavior-first-testing.md` — Canonical governance statement
- `config/ci/behavior_contract_baseline.json` — Ratchet baseline
- `config/ci/behavior_readiness_waivers.yaml` — Waiver register
