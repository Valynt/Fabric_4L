# Fabric_4L Flakiness Dashboard

> **Version:** 1.2.0 | **Last Updated:** 2024-06-15 | **Next Review:** 2024-07-15
>
> This dashboard tracks flakiness trends across the Fabric_4L test suite over time.
> Data is populated automatically by the [flakiness-tracker workflow](../../.github/workflows/flakiness-tracker.yml).

---

## Severity Legend

| Color | Severity | Consistency | Action Required |
|-------|----------|-------------|-----------------|
| 🟢 Green | Stable | 100% | None — test is fully deterministic |
| 🟡 Yellow | Warning | 95% – 99% | Monitor; investigate if trend worsens |
| 🔴 Red | Critical | < 95% | Immediate action required; quarantine or fix |

---

## Current Week Summary

| Metric | This Week | Last Week | Trend |
|--------|-----------|-----------|-------|
| Total Tests Analyzed | 0 | 0 | — |
| Flaky Tests | 0 | 0 | — |
| Critical (< 95%) | 0 | 0 | — |
| Warning (95-99%) | 0 | 0 | — |
| Overall Pass Rate | — | — | — |
| Avg Test Duration | — | — | — |

---

## Flaky Tests Detail (Current Run)

> Updated automatically by CI. *Last run: N/A*

| Test Node ID | Suite | Marker | Pass Rate | Consistency | Severity | First Seen | Status |
|--------------|-------|--------|-----------|-------------|----------|------------|--------|
| — | — | — | — | — | — | — | — |

---

## Historical Trend (12-Week Rolling)

| Week | Date | Total Tests | Flaky Tests | Critical | Warning | Pass Rate | Notes |
|------|------|-------------|-------------|----------|---------|-----------|-------|
| W0 | 2024-06-15 | — | — | — | — | — | Baseline |
| W-1 | 2024-06-08 | — | — | — | — | — | — |
| W-2 | 2024-06-01 | — | — | — | — | — | — |
| W-3 | 2024-05-25 | — | — | — | — | — | — |
| W-4 | 2024-05-18 | — | — | — | — | — | — |
| W-5 | 2024-05-11 | — | — | — | — | — | — |
| W-6 | 2024-05-04 | — | — | — | — | — | — |
| W-7 | 2024-04-27 | — | — | — | — | — | — |
| W-8 | 2024-04-20 | — | — | — | — | — | — |
| W-9 | 2024-04-13 | — | — | — | — | — | — |
| W-10 | 2024-04-06 | — | — | — | — | — | — |
| W-11 | 2024-03-30 | — | — | — | — | — | — |

---

## Flakiness by Test Suite

| Suite | Total Tests | Flaky | Stable | Flakiness % |
|-------|-------------|-------|--------|-------------|
| Backend — unit | — | — | — | — |
| Backend — integration | — | — | — | — |
| Backend — contract_static | — | — | — | — |
| Backend — tenant_boundary | — | — | — | — |
| Backend — security | — | — | — | — |
| Frontend — unit | — | — | — | — |
| Frontend — contracts | — | — | — | — |
| E2E | — | — | — | — |
| A11y | — | — | — | — |

---

## Known Flaky Tests Registry

> Persistent flaky tests that require long-term tracking or mitigation.

| Test ID | Suite | Issue # | Root Cause | Mitigation | Owner | Resolved Date |
|---------|-------|---------|------------|------------|-------|---------------|
| — | — | — | — | — | — | — |

### Common Root Causes

- **Timing / async race conditions** — Add explicit waits, use `pytest-asyncio` fixtures
- **External service dependencies** — Mock at boundary, use VCR.py for HTTP
- **Shared state / database leakage** — Ensure transaction rollback per test
- **Randomized data** — Fix seeds for property-based tests
- **Resource contention** — Parallel test isolation issues

---

## Remediation Playbook

### When a flaky test is detected:

1. **Quarantine** (optional) — Mark with `@pytest.mark.skip(reason="flaky: #issue")`
2. **Investigate** — Run locally with `--times 20` to reproduce
3. **Root cause** — Check async timing, shared state, external deps
4. **Fix** — Apply appropriate mitigation from table above
5. **Verify** — Run flakiness tracker on the fix branch
6. **Close** — Remove quarantine marker, close tracking issue

### Quarantine Policy

- Tests with < 90% pass rate may be quarantined after 2 consecutive weeks
- Quarantined tests must have a linked GitHub issue
- Quarantined tests are excluded from main CI pass/fail but still run and reported
- Max quarantine duration: 4 weeks (escalate to team lead)

---

## Automation

This dashboard is maintained automatically:

- **Weekly update**: [`.github/workflows/flakiness-tracker.yml`](../../.github/workflows/flakiness-tracker.yml)
- **Data source**: `scripts/ci/flakiness_tracker.py --json`
- **Artifact retention**: 90 days
- **Issue creation**: Auto-created when flaky tests detected

### Manual Update

```bash
# Run locally and update dashboard
python scripts/ci/flakiness_tracker.py \
  --times 5 \
  --output docs/quality/flakiness-dashboard.md \
  --json docs/quality/flakiness-data.json
```

---

*This dashboard is version-controlled and reviewed quarterly.*
*For questions, contact the QA Architecture team.*
