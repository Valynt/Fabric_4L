# Weekly Hard Acceptance Gates

This policy replaces score-based milestones with mandatory week-by-week acceptance gates.

## Mandatory gate checks (every week)

1. **Contract pass rate**: must be 100% for `contract_static` suite.
2. **Tenant-boundary tests**: all `tenant_boundary` tests must pass.
3. **Security gate**: all `security` marker tests must pass.
4. **p95 latency budget**: p95 API latency must stay within 900 ms.
5. **Error budget**: sprint-week error budget burn must remain at or below 2.0%.

If any mandatory gate fails, scope cannot advance to the next week.

## Week-by-week advancement gates

- **Week 1 → Week 2:** no critical regressions and all mandatory checks green.
- **Week 2 → Week 3:** no critical regressions and all mandatory checks green.
- **Week 3 → Week 4:** no critical regressions and all mandatory checks green.
- **Week 4 → Sprint close:** no critical regressions and all mandatory checks green.

## CI enforcement

CI workflow: `.github/workflows/weekly-acceptance-gates.yml`

The workflow enforces:
- Mandatory contract, tenant-boundary, and security test checks.
- Explicit progression block when previous week has any critical regressions.
- Publication of a single status artifact per sprint week.

## Rollback criteria and owners

| Gate | Owner | Rollback criteria |
|---|---|---|
| Contract pass rate | `@value-fabric/architects` | Any Sev-1 contract regression or pass rate below threshold. |
| Tenant-boundary tests | `@value-fabric/security-leads` | Any hostile cross-tenant read/write regression. |
| Security gate | `@value-fabric/security-leads` | Any critical security test failure or auth bypass finding. |
| p95 latency budget | `@value-fabric/sre-leads` | p95 exceeds budget for two consecutive measurement windows. |
| Error budget | `@value-fabric/sre-leads` | Error budget burn >100% or any single-day burn >50%. |

## Weekly status artifact

A single artifact is published per sprint week:

- Artifact name: `weekly-gate-status-<week>`
- Artifact file: `artifacts/weekly-gates/weekly-gate-status.json`

Required fields:
- `sprint_week`
- `generated_at_utc`
- `advance_blocked`
- `advance_blocker_reason`
- `gates[]` including `id`, `required`, `owner`, `target`, `rollback_criteria`, `status`

## Release checklist additions

Before promoting week scope in release planning:

- [ ] `weekly-acceptance-gates` workflow passed for current week.
- [ ] `weekly-gate-status.json` uploaded and archived.
- [ ] `advance_blocked` is `false`.
- [ ] No open critical regressions from previous week.
- [ ] All mandatory checks are pass (no pending metrics unresolved at release decision time).
