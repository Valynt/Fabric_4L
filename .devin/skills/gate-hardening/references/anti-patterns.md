# False-Confidence Anti-Patterns

A catalog of patterns that make gate systems report green while the application is broken. Detect and eliminate these before writing any new tests.

## Table of Contents

1. [Simulated Results](#1-simulated-results)
2. [File-Existence Checks](#2-file-existence-checks)
3. [Empty Test Directory Pass-Through](#3-empty-test-directory-pass-through)
4. [Timeout Fallback to Pass](#4-timeout-fallback-to-pass)
5. [Fabricated Metrics](#5-fabricated-metrics)
6. [Optional Auth on Write Endpoints](#6-optional-auth-on-write-endpoints)
7. [Conditional Import Fallback](#7-conditional-import-fallback)
8. [Runner Abstraction Layer](#8-runner-abstraction-layer)

---

## 1. Simulated Results

**Pattern**: Gate runner generates fake test results when real tests fail or are missing.

```python
# BAD — found in real codebase
def _simulate_eval_results(self):
    return {"passed": 12, "failed": 0, "score": 0.95}
```

**Detection**: `grep -rn '_simulate\|simulated\|fake_result\|mock_result' scripts/gates/`

**Fix**: Delete the simulation function. If tests cannot run, the gate must fail.

---

## 2. File-Existence Checks

**Pattern**: Gate checks if a config file exists on disk instead of verifying runtime behavior.

```python
# BAD — passes if grafana.json exists, even if it references nonexistent metrics
def check_observability():
    return os.path.exists("monitoring/grafana/dashboard.json")
```

**Detection**: `grep -rn 'os.path.exists\|Path.*exists' scripts/gates/`

**Fix**: Replace with a test that verifies the system emits the expected telemetry.

---

## 3. Empty Test Directory Pass-Through

**Pattern**: Gate runner counts tests in a directory. Zero tests = zero failures = pass.

```python
# BAD — no tests means no failures means gate passes
total = max(len(test_files), 10)  # Pretend 10 tests ran
failures = 0
return failures / total < threshold
```

**Detection**: `grep -rn 'max(.*total.*10\|max(.*len.*10' scripts/gates/`

**Fix**: If `len(test_files) == 0`, the gate must fail with "no tests found."

---

## 4. Timeout Fallback to Pass

**Pattern**: Gate runner catches subprocess timeout and returns a passing result.

```python
# BAD — if pytest hangs, gate passes
try:
    result = subprocess.run(["pytest", ...], timeout=60)
except subprocess.TimeoutExpired:
    return {"passed": True, "note": "timed out, assuming pass"}
```

**Detection**: `grep -rn 'TimeoutExpired\|timeout.*pass\|timeout.*True' scripts/gates/`

**Fix**: Timeout must be a hard failure. Return `passed=False`.

---

## 5. Fabricated Metrics

**Pattern**: Gate hardcodes metrics that should come from test execution.

```python
# BAD — these numbers are invented
return {
    "illegal_transitions": 0,
    "reconciliation_success_rate": 99.95,
    "total_tests": max(total_tests, 10),
}
```

**Detection**: `grep -rn 'illegal_transitions.*0\|success_rate.*99\|max(.*total' scripts/gates/`

**Fix**: Every metric must come from actual test execution output.

---

## 6. Optional Auth on Write Endpoints

**Pattern**: Write endpoint uses `get_optional_context` instead of `require_authenticated`.

```python
# BAD — export of confidential data allows anonymous access
@router.get("/export/{id}")
async def export_data(context = Depends(get_optional_context)):
    data = fetch_data(id)
    if context:
        data = filter_by_tenant(data, context.tenant_id)
    return data  # Without context, returns ALL tenant data
```

**Detection**: Run `scan_route_auth.py` from this skill's scripts directory.

**Fix**: Replace `get_optional_context` with `require_authenticated` on all endpoints that access tenant-scoped data.

---

## 7. Conditional Import Fallback

**Pattern**: Route file tries to import tenant-aware dependency, falls back to unsafe one.

```python
# BAD — if shared.identity fails to import, ALL requests bypass auth
try:
    from shared.identity import require_authenticated
    IDENTITY_AVAILABLE = True
except ImportError:
    IDENTITY_AVAILABLE = False

# Later in route:
db_dep = get_db_from_context if IDENTITY_AVAILABLE else get_db
```

**Detection**: `grep -rn 'IDENTITY_AVAILABLE\|SHARED_IDENTITY\|except ImportError' **/routes/`

**Fix**: Remove the try/except. If the import fails, the application must crash at startup.

---

## 8. Runner Abstraction Layer

**Pattern**: A custom framework sits between pytest and CI, adding knobs for overrides, simulation, and policy-based pass/fail decisions.

**Why it's dangerous**: The framework itself becomes a source of false confidence. If it has any mechanism to override a test result, the entire gate system is untrustworthy.

**Detection**: Look for `scripts/gates/`, `gate_runner`, `policy_engine`, `evidence_collector`, or any non-pytest binary in CI gate steps.

**Fix**: Delete the framework. CI invokes `pytest` directly. A non-zero exit code blocks the release. Nothing else.
