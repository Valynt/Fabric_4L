# Layer 5 Release Gates (Ground Truth)

This document defines mandatory **phase exit gates** for Layer 5 (`services/layer5-ground-truth/`) with explicit pass/fail thresholds, required evidence artifacts, and owner sign-off roles.

## Scope and authority

- Canonical runtime source: `services/layer5-ground-truth/src/layer5_ground_truth/`.
- Compatibility tree (`value_fabric/layer5/`) remains shim-only and is governed by source-of-truth checks.
- This gate document is evaluated alongside:
  - `docs/governance/layer5-backlog-issue-template.md`
  - `docs/reference/layer5/tenant-isolation-test-matrix.md`
  - `docs/launch/launch-blocker-register.md`

---

## Gate status model

Each phase is **PASS** only when every requirement below is satisfied:

1. Required command/test set has run with success exit status.
2. Numeric thresholds are met.
3. Required artifacts are attached/linked.
4. All required owners sign off.

Any unmet item is an automatic **FAIL** for that phase.

---

## Phase 0 — Backlog, contract baseline, and source-of-truth integrity

### Required command/test set (run exactly)

```bash
python services/layer5-ground-truth/scripts/check_no_duplicate_modules.py
pytest tests/contract
pytest tests/security
```

### Pass/fail thresholds

- Contract diff against baseline OpenAPI + schema artifacts: **0 unauthorized diffs**.
- Open P0 Layer 5 backlog items in release scope: **0**.
- Open P1 Layer 5 backlog items without owner+due date: **0**.
- Flaky tests in the required command set: **max 0**.

### Required artifacts

- Contract baseline report: `reports/layer5/contracts/phase0-contract-diff.md`
- Layer 5 issue register snapshot: `docs/governance/layer5-issue-register.md`
- Launch blocker cross-reference entry: `docs/launch/launch-blocker-register.md`
- Dashboard link (quality/security): `monitoring/grafana/layer5-governance-overview` (URL recorded in checklist)

### Required owner sign-off

- **Contract owner**
- **Tenant-isolation owner**
- **Ops owner**

---

## Phase 1 — Tenant isolation hostile coverage gate

### Required command/test set (run exactly)

```bash
python services/layer5-ground-truth/scripts/check_no_duplicate_modules.py
pytest services/layer5-ground-truth/tests/test_cross_tenant_hostile.py
pytest services/layer5-ground-truth/tests/test_api_tenant_propagation.py
pytest tests/security/test_tenant_boundary_fails_closed.py
pytest tests/security/test_cross_tenant_api.py
pytest tests/security/test_cross_tenant_write.py
pytest tests/security/test_tenant_context_contract.py
```

### Pass/fail thresholds

- Hostile classes in `docs/reference/layer5/tenant-isolation-test-matrix.md`: **100% mapped to automated files**.
- Cross-tenant read/write violation allowances: **0**.
- Missing-tenant-context fail-open allowances: **0**.
- Request-body tenant override acceptance: **0**.
- Flaky tests in tenant-isolation gate suite: **max 0**.

### Required artifacts

- Tenant isolation matrix update (if endpoint family changed): `docs/reference/layer5/tenant-isolation-test-matrix.md`
- Tenant-isolation baseline report: `reports/layer5/security/phase1-tenant-isolation.md`
- Exception register (if any approved temporary waivers): `docs/governance/layer5-tenant-exceptions.md`
- Dashboard link (security/authorization): `monitoring/grafana/layer5-tenant-isolation` (URL recorded in checklist)

### Required owner sign-off

- **Tenant-isolation owner** (required approver)
- **Contract owner**
- **Ops owner**

---

## Phase 2 — Layer 5 service correctness and contract conformance gate

### Required command/test set (run exactly)

```bash
python services/layer5-ground-truth/scripts/check_no_duplicate_modules.py
pytest services/layer5-ground-truth/tests
pytest tests/contract
make verify
```

### Pass/fail thresholds

- Layer 5 service tests exit code: **0**.
- Contract tests exit code: **0**.
- Unauthorized response-shape drift from approved baseline: **0**.
- Open P0 launch blockers attributable to Layer 5: **0**.
- Allowed flaky tests in Layer 5 and contract suites: **max 1** (must have linked issue and mitigation plan).

### Required artifacts

- Test evidence bundle: `reports/layer5/quality/phase2-test-evidence.md`
- Contract comparison artifact: `reports/layer5/contracts/phase2-contract-diff.md`
- Known flake register (if any): `docs/governance/layer5-flaky-tests.md`
- Dashboard link (service health + errors): `monitoring/grafana/layer5-service-health` (URL recorded in checklist)

### Required owner sign-off

- **Contract owner** (required approver)
- **Tenant-isolation owner**
- **Ops owner**

---

## Phase 3 — Performance, operations, and release candidate gate

### Required command/test set (run exactly)

```bash
make verify
pytest tests/security
pytest tests/contract
```

### Pass/fail thresholds

- p95 latency target for key Layer 5 endpoints (`GET /api/v1/truths`, `POST /api/v1/truths/{truth_id}/validate`): **<= 400 ms** in staging release candidate run.
- 5xx error rate for Layer 5 during release candidate soak: **< 0.5%**.
- Open P0 release items: **0**.
- Open P1 release items without accepted waiver: **0**.
- Maximum allowed flaky test count across full release gate run: **max 1**.

### Required artifacts

- Performance baseline report: `reports/layer5/performance/phase3-latency-baseline.md`
- Release gate execution report: `reports/layer5/release/phase3-release-gate-report.md`
- Issue register / waiver log: `docs/governance/layer5-release-issue-register.md`
- Dashboard links:
  - `monitoring/grafana/layer5-latency`
  - `monitoring/grafana/layer5-error-budget`

### Required owner sign-off

- **Ops owner** (required approver)
- **Contract owner**
- **Tenant-isolation owner**

---

## Failure handling

If any threshold fails:

1. Mark phase as `FAIL`.
2. Log blocker in the phase issue register artifact.
3. Assign owner + due date.
4. Re-run full phase command/test set after fix.
5. Capture new evidence artifact with timestamp and commit SHA.

No phase may be marked `PASS` using partial reruns without explicit waiver approval by all three sign-off roles.
