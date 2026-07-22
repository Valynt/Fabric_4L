# Engineering Quality Thresholds

> Versioned thresholds for cyclomatic complexity, test coverage, duplication,
> and code health. These are implementation acceptance criteria, not
> architectural decisions. ADRs define the rules; this standard defines the
> numbers.
>
> Companion to: ADR-035, ADR-036, ADR-037, ADR-038

---

## Cyclomatic Complexity

| Scope | Max CCN | Notes |
|---|---|---|
| Per function | 15 | Hard limit — functions exceeding this must be refactored |
| Per module (extracted) | 12 | For modules produced by responsibility separation (e.g., ADR-037) |
| Per module (legacy) | 20 | Tolerance for pre-refactoring modules; must not increase |

**Measurement:** CCN is measured per function using `radon cc` (Python) or
equivalent. "Per module" is the sum of function-level CCN within a single file.

---

## Test Coverage

| Module criticality | Min branch coverage | Notes |
|---|---|---|
| Critical (security, tenant isolation, query execution) | 80% | Must be met before ADR transitions to Accepted |
| High (workflow engine, extraction pipeline) | 70% | For extracted modules per ADR-037 |
| Standard (business logic, API routes) | 60% | General baseline |
| Low (utilities, helpers) | 40% | Minimal expectation |

**Measurement:** Branch coverage via `pytest --cov --cov-branch` (Python) or
`vitest --coverage` (TypeScript). Coverage is measured on the diff for PRs and
on the module for ADR acceptance.

---

## Duplication

| Metric | Threshold | Notes |
|---|---|---|
| Duplication percentage (critical paths) | < 15% | Critical paths: query execution, tenant context, auth middleware |
| Duplication percentage (non-critical) | < 25% | General codebase baseline |
| DRY violation count (tenant validation) | 1 | After ADR-035 extraction; single shared implementation |

**Measurement:** Repowise `get_health` duplication metric or `jscpd` equivalent.

---

## Code Health

| Metric | Target | Notes |
|---|---|---|
| Hotspot health score | > 7.0 | Measured by repowise; alert band is < 5.0 |
| Average health score | > 8.0 | Measured by repowise |
| Alert-band files (health 1.0) | 0 | No file should remain at health 1.0 |
| Untested hotspots | 0 | All hotspot files must have test coverage |

**Measurement:** Repowise `get_health` with trend tracking. Post-sprint
snapshots captured via `repowise health --trend`.

---

## Cognitive Complexity Growth

| Metric | Threshold | Notes |
|---|---|---|
| Growth ratio | 1.2:1 | New code must not increase complexity ratio by more than 20% |

**Measurement:** Compare cognitive complexity of added vs. modified code using
`radon cc -s` or equivalent.

---

## Sprint Verification

After each sprint, capture:

```bash
# Post-sprint health snapshot
repowise health --trend > sprint-N-health.json

# Risk delta
repowise risk main..HEAD --json > sprint-N-risk.json

# Dead code delta
repowise dead-code --json > sprint-N-deadcode.json

# Security posture
repowise security --json > sprint-N-security.json
```

Compare against baseline to verify thresholds are met.

---

## Exception Process

Exceptions to these thresholds require:

1. Documented justification in the PR description
2. Approval from Platform Engineering lead
3. Expiry date for the exception
4. Tracking in the compatibility debt registry (`docs/governance/compatibility-debt-registry.md`)

---

*Last updated: 2026-07-20*
