# Archived documentation index

This index catalogues historical reports retained for traceability. Each entry
links the original file in place (banner-stamped `STATUS: ARCHIVED`) and points
to the current canonical replacement.

> Files listed here are **not** moved physically — they remain at their original
> paths to avoid breaking external bookmarks and historical commit references.
> A follow-up commit may relocate them under `docs/archive/quality-reports/`
> using `git mv` once link checkers and external references have been audited.

## Audit & analysis reports

| File | Date | Replaced by |
| ---- | ---- | ----------- |
| [DOCUMENTATION_AUDIT_REPORT.md](../DOCUMENTATION_AUDIT_REPORT.md) | 2026-05-03 | This documentation refresh pass and the Diátaxis index at [docs/README.md](../README.md) |
| [BACKEND_FRONTEND_ALIGNMENT_ANALYSIS.md](../BACKEND_FRONTEND_ALIGNMENT_ANALYSIS.md) | 2026 | [contracts/GOVERNANCE.md](../../contracts/GOVERNANCE.md), [contracts/openapi/](../../contracts/openapi/) |
| [misalignment-report.md](../misalignment-report.md) | 2026-05-02 | [contracts/GOVERNANCE.md](../../contracts/GOVERNANCE.md) |
| [test-quality-audit.md](../test-quality-audit.md) | 2026-05-01 | [reference/testing-strategy.md](../reference/testing-strategy.md) |
| [test-audit-2026-04-28.md](../test-audit-2026-04-28.md) | 2026-04-28 | [reference/testing-strategy.md](../reference/testing-strategy.md) |

## Security reports

| File | Date | Replaced by |
| ---- | ---- | ----------- |
| [SECURITY_FIXES_EXECUTION_LOG.md](../SECURITY_FIXES_EXECUTION_LOG.md) | 2026-04-27 | [SECURITY.md](../../SECURITY.md), [security/](../security/), [security-gates.md](../security-gates.md) |
| [SECURITY_FIXES_SUMMARY.md](../SECURITY_FIXES_SUMMARY.md) | 2026-04-27 | [SECURITY.md](../../SECURITY.md), [security/](../security/) |
| [MCP_GATEWAY_SECURITY_ASSESSMENT_2026-04-24.md](../MCP_GATEWAY_SECURITY_ASSESSMENT_2026-04-24.md) | 2026-04-24 | [reference/](../reference/), [security/](../security/) |

## Migration / refactor logs

| File | Date | Replaced by |
| ---- | ---- | ----------- |
| [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) | — | [NAVIGATION_ARCHITECTURE.md](../NAVIGATION_ARCHITECTURE.md), [DESIGN.md](../../DESIGN.md) |
| [CHANGES.md](../CHANGES.md) | 2026-04-21 | [CHANGELOG.md](../../CHANGELOG.md) |
| [migration-note-layer56-canonical-imports.md](../migration-note-layer56-canonical-imports.md) | 2026-05-06 | Direction reversed by [ADR-027](../architecture/ADR-021-layer-3-canonical-runtime-path.md); see [reference/layer-runtime-path-governance.md](../reference/layer-runtime-path-governance.md) |

## Existing archived materials

- [quality-reports/](quality-reports/) — earlier batch of quality reports.
- [archive-registry.md](archive-registry.md) — registry of previously archived items.
- [MIGRATION_REPORT.md](MIGRATION_REPORT.md) — prior migration report.

## Files intentionally **not** archived

These were considered and kept active because they are evergreen references or
rolling baselines, not point-in-time reports:

- [current-failures.md](../current-failures.md) — rolling test baseline; updated continuously.
- [SECURITY_TRIAGE_RUBRIC.md](../SECURITY_TRIAGE_RUBRIC.md) — evergreen classification reference.
- [LAUNCH_RUNBOOK.md](../LAUNCH_RUNBOOK.md) — active production-launch runbook.
