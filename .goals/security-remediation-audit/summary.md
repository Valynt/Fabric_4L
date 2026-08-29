# Goal Summary — Remediation & Refactor Plan Audit

## What was achieved

The ten-item Remediation & Refactor Plan (PROD-001…DB-010) was audited
against the live codebase at `origin/main` (`00bffb308`) with an
assessment-only deliverable: `.goals/security-remediation-audit/audit-report.md`.
No application source code was modified.

**Per acceptance criteria:**
1. Codebase synced to remote main — verified `HEAD == origin/main == 00bffb308`.
2. Assessment-only — no source changes; only `.goals/` artifacts.
3. All 10 plan items covered with Verdict + Evidence + Scope/Effort + Boundaries.
4. Claims verified by commands actually run (see report's verification table).
5. Both Builder (report) and Inspector (independent check) completed.

## Verdicts per item

| ID | Verdict | Effort |
|----|---------|--------|
| PROD-001 | VALID — live P0 evidence is a failed run; "seven journeys" ≠ committed 12-spec standard set | L |
| PROD-002 | PARTIALLY VALID — rollback drill exists but failed image-level; RTO/RPO records present | M |
| IDENTITY-003 | PARTIALLY VALID — partial coverage; live IdP E2E RE_TESTABLE | M |
| L3-SEC-004 | PARTIALLY VALID — mostly addressed via `check_layer3_cypher_scope.py` + 76-entry allowlist | M |
| DB-SEC-005 | PARTIALLY VALID — `app.current_tenant` doesn't exist (standardization moot); admin bypass still present | M |
| CI-006 | UNVERIFIABLE-IN-REPO — gate reproducibility requires the supported dep environment | L |
| L3-SEC-007 | **VALID — implementation claim FALSE.** Commit `0648b46` does not exist; unscoped `OPTIONAL MATCH (vp:ValuePack)` joins remain at `benchmarks.py:133,209` and `formulas.py:1310` | S |
| CI-008 | Mostly addressed — AST-based call-site check already exists | S |
| TEST-009 | VALID — hostile tests are regex-based and miss the `vp` optional-join/relationship side | S |
| DB-010 | Mostly addressed — `migration_status_report.py` already inspects pg_class/pg_policies | S |

## Key findings

1. **Single most important result:** the plan's claim that L3-SEC-007 was
   "implemented and committed as 0648b46" is false — the commit does not exist
   and the cross-tenant `usage_count` leak via `ValuePack` optional joins is
   still live at `origin/main`.
2. **P0 definition discrepancy:** plan says "seven P0 journeys"; committed
   standard P0 = 12 specs, `:p0:deep` = 7. Scope must be pinned before
   executing PROD-001.
3. **PROD-001/002/IDENTITY-003 share one physical stack** (live L1–L6 + IdP);
   environment-bound with common setup cost.
4. **Several "new" items are already implemented** under different taxonomy
   (CI-008, DB-010, most of L3-SEC-004/DB-SEC-005) — the highest-value work is
   verifying/ratcheting existing gates, not rebuilding them.

## Iteration history

- **Iteration 1:** Builder produced the audit report; Inspector independently
  re-verified all central claims (commit absence, unscoped optional joins, P0
  spec counts, signoff-evidence failures, GUC absence) → **PASS** on first
  iteration. No corrective rounds required.

## Recommendations

- Execute L3-SEC-007 for real: tenant-scope the `vp` side of the optional
  joins in `benchmarks.py` and `formulas.py`, and swap the regex-based hostile
  test for an executable validator assertion that catches unscoped optional
  joins (fold into TEST-009).
- Pin the P0 journey set (12-spec standard vs 7-spec deep) before any
  PROD-001 execution.
- Treat CI-008/DB-010 as verify-the-existing-gate work rather than new
  tooling; reproduce `make verify` on the release SHA before investing in new
  abstractions.
- Filing IDs (PROD-001…DB-010) trace to no committed artifact — consider
  committing the AuditOrchestrator findings that produced this plan so future
  audits can be diffed.
## Follow-up (2026-08-29): L3-SEC-007 landed

Implemented the tenant-scoping fix the audit recommended:

- `benchmarks.py` list/get: `OPTIONAL MATCH (vp:ValuePack)` now carries `{tenant_id: $tenant_id}` (list uses an f-string, so braces escaped as `{{...}}`).
- `formulas.py` ref-count and delete-step: `vp:ValuePack`, `fv:FormulaVersion`, and `v:Variable` optional joins now `{tenant_id: $tenant_id}`; bare `OPTIONAL MATCH (f)` hardened to `(f:Formula)` for the broad-MATCH guard.
- TEST-009 fold-in: 14 executable validator + behavioral hostile tests in tests/security/test_optional_join_tenant_scope.py, plus static ValuePack-scope checks in the benchmarks regex file.

Validation: layer3 security suite 63 passed / 5 skipped (pre-existing skips); layer3 Cypher scope CI gate PASS (0 unsafe). Residual out-of-scope: `create_formula`/`update_formula` fetch steps and `update_formula` delete-rels are pre-existing unscoped queries at origin/main (fail-closed, no leak) — not part of L3-SEC-007.
