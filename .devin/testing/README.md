# Testing Artifacts — Single Source of Truth

This directory is the **canonical location** for all test audit artifacts, gap matrices, inventory reports, and assurance documentation.

## Current Artifacts

| File | Description | Last Updated |
|------|-------------|--------------|
| `assurance-remediation-report.md` | Active remediation findings | See file |
| `assurance-remediation-report-2026-04-26.md` | Dated remediation snapshot | 2026-04-26 |
| `backend-audit-l1.md` | Layer 1 backend audit | See file |
| `production-invariants.md` | Production invariant catalog | See file |
| `quarantine-removal-log.md` | Quarantined test removal tracking | See file |
| `test-assurance-inventory.md` | Assurance inventory | See file |
| `test-discovery-report.md` | Test discovery findings | See file |
| `test-gap-matrix.md` | P0/P1/P2 classified gaps | See file |
| `test-inventory.md` | Complete test inventory (backend + frontend) | See file |
| `test-quality-audit-2026-04-15.md` | Quality audit snapshot | 2026-04-15 |

## Rules

1. **All new test artifacts go here.** Do not create `testing-artifacts/` or `testing-assurance/` variants.
2. **Date snapshots** with `YYYY-MM-DD` suffix for historical versions.
3. **Archive old snapshots** to `archive/testing-dedup/` after 30 days.
4. **Use episodic memory** for execution logs, not redundant report directories.

## Generation

These artifacts are produced by:
- `test-assurance` agent (autonomous)
- `test-quality-remediation` workflow
- Manual audits

## Deduplication History

Previously, divergent versions existed in `testing-artifacts/` and `testing-assurance/`.
These were consolidated on 2026-04-28. See `archive/testing-dedup/README.md` for details.
