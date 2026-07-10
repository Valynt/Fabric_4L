# Fabric_4L Mutation Testing Configuration v1.2.0

> **Status:** Active | **Current Mutation Score Threshold:** 70% | **Target (v1.3.0):** 80%
>
> ![Mutation Score](https://img.shields.io/badge/mutation-70%25-yellow)

---

## Overview

Mutation testing validates test suite effectiveness by introducing small code mutations
and verifying that tests detect them. A "killed" mutant means tests caught the change;
"survived" mutants indicate gaps in test coverage.

**Mutation Score** = Killed Mutants / Total Mutants × 100

---

## Backend: Python (mutmut)

### Installation

```bash
pip install mutmut
```

### Configuration (`setup.cfg`)

Add this section to `setup.cfg` at repository root:

```ini
[mutmut]
# Paths to mutate (relative to setup.cfg)
paths_to_mutate = fabric_4l/
backup = False
runner = python -m pytest -x -q --tb=no --disable-warnings
tests_dir = tests/
# Historical file for incremental runs
history_file = .mutmut-cache/history.json
# Cache directory for mutant state
cache_dir = .mutmut-cache
# Test timeout per mutant (seconds)
timeout = 30
# Exclude auto-generated / boilerplate
exclude = 
    fabric_4l/__init__.py
    fabric_4l/**/migrations/*
    fabric_4l/**/alembic/*
    fabric_4l/**/generated/*
    fabric_4l/**/vendor/*
# Dynamic test discovery (pytest)
dynamic_test_discovery = True
# Test file patterns
test_file_pattern = test_*.py
```

### Usage

```bash
# Full mutation test run (slow — run nightly or weekly)
mutmut run

# Show results summary
mutmut results

# Generate HTML report
mutmut results --html-report mutmut-report.html

# Show surviving mutants
mutmut results -- survived

# Apply a surviving mutant to inspect (creates .bak file)
mutmut apply <mutant-id>

# Run on a single file only
mutmut run --paths-to-mutate fabric_4l/core/auth.py

# Incremental: only mutants changed since last run
mutmut run --use-cache
```

### CI Integration

```yaml
# .github/workflows/mutation-test.yml
name: mutation-test

on:
  schedule:
    - cron: "0 3 * * 1"  # Weekly: Monday 03:00 UTC
  workflow_dispatch:

jobs:
  mutation-test:
    runs-on: ubuntu-latest
    timeout-minutes: 240  # Mutation testing is slow
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
      - run: pip install mutmut pytest
      - run: mutmut run
      - run: mutmut results --html-report mutmut-report.html
      - uses: actions/upload-artifact@v4
        with:
          name: mutmut-report
          path: mutmut-report.html
      # Enforce minimum mutation score
      - name: Check mutation score
        run: |
          SCORE=$(mutmut results --json | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('mutation_score', 0))")
          echo "Mutation score: ${SCORE}%"
          if (( $(echo "$SCORE < 70" | bc -l) )); then
            echo "Mutation score $SCORE% below threshold 70%"
            exit 1
          fi
```

---

## Frontend: TypeScript / React (Stryker)

### Installation

```bash
cd apps/web
npm install --save-dev @stryker-mutator/core @stryker-mutator/vitest-runner
```

### Configuration (`apps/web/stryker.config.json`)

```json
{
  "$schema": "./node_modules/@stryker-mutator/core/schema/stryker-schema.json",
  "packageManager": "npm",
  "reporters": ["html", "json", "progress", "dashboard"],
  "testRunner": "vitest",
  "testRunner_comment": "Uses Vitest for test execution",
  "coverageAnalysis": "perTest",
  "coverageAnalysis_comment": "Enables incremental mutation testing per test file",
  "mutate": [
    "src/**/*.ts",
    "src/**/*.tsx",
    "!src/**/*.test.ts",
    "!src/**/*.test.tsx",
    "!src/**/*.spec.ts",
    "!src/**/*.spec.tsx",
    "!src/**/*.d.ts",
    "!src/**/__mocks__/**",
    "!src/**/generated/**",
    "!src/**/vendor/**"
  ],
  "vitest": {
    "configFile": "vitest.config.ts",
    "dir": "src"
  },
  "thresholds": {
    "high": 80,
    "low": 60,
    "break": 70
  },
  "thresholds_comment": "break=70 enforces CI failure below 70%",
  "dashboard": {
    "reportType": "full"
  },
  "htmlReporter": {
    "baseDir": "reports/mutation/html"
  },
  "jsonReporter": {
    "fileName": "reports/mutation/mutation.json"
  },
  "timeoutMS": 15000,
  "timeoutFactor": 2.5,
  "maxConcurrentTestRunners": 4,
  "incremental": true,
  "incrementalFile": "reports/mutation/incremental.json"
}
```

### Package scripts (`apps/web/package.json`)

```json
{
  "scripts": {
    "test:mutation": "stryker run",
    "test:mutation:ci": "stryker run --reporters html json progress --dashboard.reportType full",
    "test:mutation:incremental": "stryker run --incremental"
  }
}
```

### Usage

```bash
cd apps/web

# Full mutation test run
npm run test:mutation

# CI mode (fails if below threshold)
npm run test:mutation:ci

# Incremental (faster, only changed files)
npm run test:mutation:incremental

# Run on a single file
npx stryker run --mutate src/components/AuthForm.tsx
```

### CI Integration

```yaml
# .github/workflows/mutation-test-frontend.yml
name: mutation-test-frontend

on:
  schedule:
    - cron: "0 4 * * 1"  # Weekly: Monday 04:00 UTC (after backend)
  workflow_dispatch:

jobs:
  mutation-test:
    runs-on: ubuntu-latest
    timeout-minutes: 120
    defaults:
      run:
        working-directory: apps/web
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: apps/web/package-lock.json
      - run: npm ci
      - run: npm run test:mutation:ci
      - uses: actions/upload-artifact@v4
        with:
          name: stryker-report
          path: apps/web/reports/mutation/
```

---

## Unified Makefile Target

Add to root `Makefile`:

```makefile
# ── Mutation Testing ──────────────────────────────────────────────────────────

MUTATION_SCORE_THRESHOLD := 70
MUTATION_DIR := reports/mutation

## Run all mutation tests (backend + frontend)
mutation-test: mutation-test-backend mutation-test-frontend
	@echo "=== Mutation Testing Complete ==="
	@echo "Backend:  see $(MUTATION_DIR)/backend-report.html"
	@echo "Frontend: see $(MUTATION_DIR)/frontend/html/index.html"

## Run backend mutation tests (mutmut)
mutation-test-backend:
	@echo "Running backend mutation tests (mutmut)..."
	@mkdir -p $(MUTATION_DIR)
	mutmut run
	mutmut results --html-report $(MUTATION_DIR)/backend-report.html
	mutmut results --json > $(MUTATION_DIR)/backend-report.json
	@echo "Checking mutation score >= $(MUTATION_SCORE_THRESHOLD)%..."
	@python -c "
import json, sys
with open('$(MUTATION_DIR)/backend-report.json') as f:
    data = json.load(f)
score = data.get('mutation_score', 0)
print(f'Backend mutation score: {score}%')
if score < $(MUTATION_SCORE_THRESHOLD):
    print(f'FAIL: Score {score}% below threshold $(MUTATION_SCORE_THRESHOLD)%')
    sys.exit(1)
print(f'PASS: Score {score}% meets threshold')
"

## Run frontend mutation tests (Stryker)
mutation-test-frontend:
	@echo "Running frontend mutation tests (Stryker)..."
	cd apps/web && npm run test:mutation:ci

## Check mutation score without re-running (uses cached results)
mutation-check-score:
	@echo "Checking cached mutation scores..."
	@python -c "
import json, sys, os
backend_file = '$(MUTATION_DIR)/backend-report.json'
frontend_file = 'apps/web/reports/mutation/mutation.json'
scores = {}
if os.path.exists(backend_file):
    with open(backend_file) as f: scores['backend'] = json.load(f).get('mutation_score', 0)
if os.path.exists(frontend_file):
    with open(frontend_file) as f: scores['frontend'] = json.load(f).get('mutationScore', 0)
for name, score in scores.items():
    status = 'PASS' if score >= $(MUTATION_SCORE_THRESHOLD) else 'FAIL'
    print(f'{name}: {score}% [{status}]')
if any(s < $(MUTATION_SCORE_THRESHOLD) for s in scores.values()):
    sys.exit(1)
"
```

---

## Score Thresholds & Escalation

| Version | Minimum Score | Target Score | Enforcement |
|---------|---------------|--------------|-------------|
| v1.2.0  | 70% | 75% | Warning in CI |
| v1.3.0  | 80% | 85% | Hard gate in CI |
| v1.4.0  | 85% | 90% | Hard gate in CI |

### Escalation Matrix

| Score Range | Action | Owner |
|-------------|--------|-------|
| ≥ 80% | No action | Team |
| 70-79% | Create tech-debt ticket, plan remediation | Tech Lead |
| 60-69% | Block non-critical releases | EM + Tech Lead |
| < 60% | Halt feature work, prioritize test gaps | EM |

---

## Interpreting Reports

### Mutmut HTML Report

- **Killed** 🟢 — Tests detected the mutation. Good.
- **Survived** 🔴 — Tests did NOT detect the mutation. Add or improve tests.
- **Timeout** ⏱️ — Mutation caused infinite loop / hang.
- **Skipped** ⏭️ — Excluded from mutation (e.g., `pragma: no mutate`).

### Stryker Dashboard

- **Killed** — Equivalent to mutmut's "killed"
- **Survived** — Equivalent to mutmut's "survived"
- **No coverage** — No tests cover this code at all
- **Ignored** — Explicitly excluded via config

### Code Annotation

Both tools support inline annotations. In VS Code:

```bash
# Mutmut: show surviving mutants inline
mutmut show <id>

# Stryker: generates mutation-report.html with per-line detail
open apps/web/reports/mutation/html/index.html
```

---

## FAQ

**Q: Why is mutation testing so slow?**
A: Each mutant requires a full test run. For N mutants and T test time, total time ≈ N × T. Use incremental mode and run on CI schedules, not per-PR.

**Q: Can I run mutation tests in parallel?**
A: Stryker supports `maxConcurrentTestRunners`. mutmut supports parallelization via GNU parallel: `mutmut run --runner-parallel 4`.

**Q: How do I exclude a line from mutation?**
A: Add a pragma comment:
```python
# pragma: no mutate
x = expensive_debug_computation()
```
```typescript
// Stryker disable next-line
const debugOnly = computeDebugInfo();
```

**Q: What if the score drops?**
A: CI will fail. Check the report for newly survived mutants and add tests to kill them.

---

*Configuration maintained by QA Architecture. Last reviewed: 2024-06-15*
