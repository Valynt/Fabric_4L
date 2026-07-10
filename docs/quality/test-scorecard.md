# Fabric_4L Test Quality Scorecard

> **Version:** 1.2.0 | **Last Updated:** 2024-06-15 | **Review Cycle:** Bi-weekly
>
> This scorecard provides a consolidated view of test quality across the Fabric_4L platform.
> Data is populated automatically by CI pipelines and manual audits.

---

## Scorecard (Current Sprint)

| # | Metric | Current | Target | Trend | Status |
|---|--------|---------|--------|-------|--------|
| 1 | **Line Coverage** | 82% | 80% | +2% | ✅ Exceeds |
| 2 | **Branch Coverage** | 71% | 75% | +1% | ⚠️ Below |
| 3 | **Mutation Score** | 68% | 70% | +3% | ⚠️ Below |
| 4 | **Flaky Tests** | 3 | 0 | -2 | ⚠️ Open |
| 5 | **E2E Pass Rate** | 96% | 98% | +1% | ⚠️ Below |
| 6 | **Avg Test Time (CI)** | 4.2m | < 5m | stable | ✅ Pass |
| 7 | **Security Tests** | 45 | 50 | +5 | ⚠️ Below |
| 8 | **Contract Test Coverage** | 60% | 90% | +5% | ⚠️ Below |
| 9 | **A11y Violations** | 2 | 0 | -3 | ⚠️ Open |
| 10 | **Test Documentation** | 75% | 100% | +10% | ⚠️ Below |
| 11 | **Parallel Test Efficiency** | 78% | 85% | +3% | ⚠️ Below |
| 12 | **Production Incident Coverage** | 85% | 95% | +5% | ⚠️ Below |

### Status Legend

| Icon | Meaning |
|------|---------|
| ✅ | At or above target |
| ⚠️ | Below target, improvement in progress |
| ❌ | Critically below target, blocking concern |
| 🔴 | Regression from previous period |

---

## Detailed Metric Definitions

### 1. Line Coverage
- **Definition:** Percentage of executable lines covered by tests
- **Tools:** pytest-cov (backend), Vitest coverage (frontend)
- **Calculation:** `covered_lines / total_lines * 100`
- **Enforcement:** CI fails if < 80% or if drop > 1% from baseline
- **Owner:** All engineers (pair programming requirement)

### 2. Branch Coverage
- **Definition:** Percentage of code branches (if/else, switch) covered
- **Tools:** Same as line coverage
- **Target rationale:** 75% ensures critical paths are tested
- **Action:** Focus on complex conditional logic in auth and tenant modules

### 3. Mutation Score
- **Definition:** Percentage of code mutations detected (killed) by tests
- **Tools:** mutmut (backend), Stryker (frontend)
- **Threshold:** 70% minimum; 80% by v1.3.0
- **Schedule:** Weekly CI run (Mondays 03:00 UTC)

### 4. Flaky Tests
- **Definition:** Tests with < 100% consistency across 5 consecutive runs
- **Tools:** `scripts/ci/flakiness_tracker.py`
- **Policy:** 0 flaky tests tolerated in main branch
- **Escalation:** > 3 flaky tests = halt non-critical releases

### 5. E2E Pass Rate
- **Definition:** Pass rate of Playwright E2E test suite
- **Tools:** Playwright (Chromium, Firefox, WebKit)
- **Environments:** Staging + production (smoke)
- **Retry policy:** Max 1 retry per test; > 2 failures = investigation

### 6. Avg Test Time (CI)
- **Definition:** Wall-clock time for full CI test pipeline
- **Target:** < 5 minutes for developer feedback loop
- **Optimization:** Parallel test execution, selective test running

### 7. Security Tests
- **Definition:** Count of dedicated security test cases
- **Categories:** Auth bypass, injection, XSS, CSRF, tenant isolation
- **Target:** 50 by v1.2.0 GA, 75 by v1.3.0

### 8. Contract Test Coverage
- **Definition:** Percentage of API endpoints covered by contract tests
- **Tools:** schemathesis, JSON Schema validators
- **Expansion plan:** See [contract-test-expansion.md](../../contract-test-expansion.md)

### 9. A11y Violations
- **Definition:** Automated accessibility issues (WCAG 2.1 AA)
- **Tools:** axe-core via Playwright, Lighthouse a11y audit
- **Policy:** 0 critical/blocker violations; max 5 minor

### 10. Test Documentation
- **Definition:** Percentage of test files with docstrings/comments
- **Standard:** Each test function must have a descriptive docstring
- **Tool:** Custom lint rule + manual review

### 11. Parallel Test Efficiency
- **Definition:** Ratio of actual parallel workers to theoretical max
- **Target:** 85% to maximize CI throughput
- **Bottleneck:** Sequential integration tests, shared DB fixtures

### 12. Production Incident Coverage
- **Definition:** Percentage of production incidents with regression tests
- **Process:** Every SEV2+ incident must have a follow-up test within 1 week
- **Tracking:** Incident → Jira ticket → test PR linkage

---

## Historical Trend (6-Month Rolling)

| Month | Line Cov | Branch Cov | Mutation | Flaky | E2E Pass | Avg Time | Security |
|-------|----------|------------|----------|-------|----------|----------|----------|
| 2024-01 | 74% | 62% | 58% | 8 | 91% | 5.8m | 28 |
| 2024-02 | 76% | 65% | 61% | 6 | 92% | 5.4m | 32 |
| 2024-03 | 77% | 66% | 63% | 5 | 93% | 5.1m | 35 |
| 2024-04 | 79% | 68% | 65% | 4 | 94% | 4.8m | 38 |
| 2024-05 | 81% | 70% | 66% | 5 | 95% | 4.5m | 42 |
| 2024-06 | 82% | 71% | 68% | 3 | 96% | 4.2m | 45 |

### Trend Visualization

```
Line Coverage:   74% → 76% → 77% → 79% → 81% → 82%  ▲ +8% (6mo)
Branch Coverage: 62% → 65% → 66% → 68% → 70% → 71%  ▲ +9% (6mo)
Mutation Score:  58% → 61% → 63% → 65% → 66% → 68%  ▲ +10% (6mo)
Flaky Tests:      8  →  6  →  5  →  4  →  5  →  3   ▼ -5 (6mo)
E2E Pass Rate:   91% → 92% → 93% → 94% → 95% → 96%  ▲ +5% (6mo)
```

---

## Generation Instructions

### Automated Generation

The scorecard is partially auto-generated by CI:

```yaml
# .github/workflows/quality-scorecard.yml
name: quality-scorecard

on:
  schedule:
    - cron: "0 9 * * 1"  # Weekly: Monday 09:00 UTC
  workflow_dispatch:

jobs:
  scorecard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Collect metrics
        run: |
          python scripts/ci/coverage_trends.py \
            --backend-cov coverage.xml \
            --frontend-cov apps/web/coverage/coverage-final.json \
            --output-json /tmp/coverage.json

          python scripts/ci/flakiness_tracker.py \
            --times 3 --json /tmp/flakiness.json

      - name: Generate scorecard
        run: |
          python scripts/ci/generate_scorecard.py \
            --coverage /tmp/coverage.json \
            --flakiness /tmp/flakiness.json \
            --output docs/quality/test-scorecard.md
```

### Manual Update Process

1. **Coverage data:** Run `make test` and extract from pytest-cov / Vitest output
2. **Mutation score:** Check latest mutmut / Stryker CI run
3. **Flaky tests:** Review latest flakiness-tracker report
4. **E2E pass rate:** Check Playwright dashboard (weekly average)
5. **Security tests:** Count `@pytest.mark.security` tests + security/ directory
6. **A11y violations:** Run `npx playwright test --grep a11y` and count failures
7. **Update this file:** Edit the Current column for each metric
8. **Commit:** `git commit -m "quality: update test scorecard W24"`

### Scorecard Template (for copying)

```markdown
| # | Metric | Current | Target | Trend | Status |
|---|--------|---------|--------|-------|--------|
| 1 | Line Coverage | __% | 80% | _% | |
| 2 | Branch Coverage | __% | 75% | _% | |
| 3 | Mutation Score | __% | 70% | _% | |
| 4 | Flaky Tests | _ | 0 | _ | |
| 5 | E2E Pass Rate | __% | 98% | _% | |
| 6 | Avg Test Time | _._m | < 5m | | |
| 7 | Security Tests | _ | 50 | _ | |
| 8 | Contract Coverage | __% | 90% | _% | |
| 9 | A11y Violations | _ | 0 | _ | |
| 10 | Test Documentation | __% | 100% | _% | |
| 11 | Parallel Efficiency | __% | 85% | _% | |
| 12 | Incident Coverage | __% | 95% | _% | |
```

---

## Action Items

| Priority | Metric | Action | Owner | Due Date |
|----------|--------|--------|-------|----------|
| P0 | Branch Coverage (71% → 75%) | Add branch tests for auth module | @backend-team | 2024-06-30 |
| P0 | Mutation Score (68% → 70%) | Kill 2 surviving mutants in tenant service | @qa-team | 2024-06-25 |
| P1 | Flaky Tests (3 → 0) | Fix async timing in `test_websocket_events` | @backend-team | 2024-06-28 |
| P1 | E2E Pass Rate (96% → 98%) | Stabilize checkout flow test | @frontend-team | 2024-07-05 |
| P1 | Security Tests (45 → 50) | Add 5 auth bypass tests | @security-team | 2024-07-10 |
| P2 | Contract Coverage (60% → 90%) | Expand schemathesis to all endpoints | @backend-team | 2024-07-20 |
| P2 | A11y Violations (2 → 0) | Fix color contrast in dark mode | @frontend-team | 2024-07-15 |

---

## Escalation Matrix

| Condition | Action | Decision Maker |
|-----------|--------|----------------|
| ≥ 3 metrics critically below target | Halt feature work, all-hands quality sprint | Engineering Manager |
| Flaky tests > 5 | Block all non-hotfix merges to main | Tech Lead |
| Coverage drops > 2% in a single PR | Revert PR, mandatory code review | Tech Lead + QA |
| E2E pass rate < 90% | Stop deployments to production | Engineering Manager |
| Mutation score < 60% | Dedicated testing sprint | Engineering Manager |

---

*Scorecard reviewed and approved by QA Architecture on 2024-06-15.*
*Next review scheduled: 2024-06-29.*
