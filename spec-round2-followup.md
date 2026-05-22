# Spec: Round-2 Code Review Follow-up

**Date:** 2026-05-21  
**Status:** Draft — awaiting confirmation  
**Commits addressed:** `1816a95`, `8d5470c`

---

## Problem Statement

Commits `1816a95` and `8d5470c` introduced several improvements: fail-closed timeout parsing, sys.path priority hardening, JWT tenant normalization, centralized tenant extraction via `api_key.metadata["tenant_id"]`, WebSocket auth hardening, and a new CI import-drift guard. The code review identified four follow-up items that must be addressed before these changes are considered production-safe:

1. **Regression test gap** — `test_benchmark_policies_route.py` uses the old `api_key.tenant_id` shape; hostile cases for missing/empty/null `metadata.tenant_id` are absent.
2. **Inconsistent tenant extraction** — `value_packs.py` still uses `api_key.tenant_id` (with a `'default'` fallback), diverging from the `api_key.metadata["tenant_id"]` pattern now canonical in `benchmarks.py` and `formula_governance.py`.
3. **Generated state in source control** — `.agent/memory/episodic/AGENT_LEARNINGS.jsonl` is operational runtime state that should not be tracked in Git.
4. **CI guard not wired** — `scripts/ci/check_runtime_canonical_imports.py` exists but is not invoked by any CI workflow, leaving import drift invisible.

---

## Requirements

### R1 — Fix test_benchmark_policies_route.py to match new API-key contract

The existing tests construct `api_key = SimpleNamespace(tenant_id=...)`. After the `1816a95` migration, `_get_authenticated_tenant_id` reads from `api_key.metadata["tenant_id"]`. The tests must be updated to the new shape and extended with hostile cases.

**Happy-path update:**
```python
api_key = SimpleNamespace(metadata={"tenant_id": "tenant-a"})
```

**Hostile regression cases (parametrized):**
```python
@pytest.mark.parametrize("api_key", [
    SimpleNamespace(metadata={}),
    SimpleNamespace(metadata={"tenant_id": ""}),
    SimpleNamespace(metadata={"tenant_id": None}),
    SimpleNamespace(metadata=None),
    SimpleNamespace(),  # no metadata attr at all
])
async def test_rejects_api_key_without_valid_tenant_metadata(api_key, monkeypatch):
    ...
```

**Expected assertions for hostile cases:**
- Raises `HTTPException` with `status_code=401`.
- Does **not** execute the tenant-scoped Neo4j query.
- Does **not** fall back to `api_key.tenant_id`, request body, path, or query params.

Scope: `services/layer3-knowledge/tests/test_benchmark_policies_route.py`

---

### R2 — Migrate value_packs.py to api_key.metadata["tenant_id"]

`value_packs.py` line 1469 uses:
```python
tenant_id = api_key.tenant_id if hasattr(api_key, 'tenant_id') else 'default'
```

This must be replaced with the same `_get_authenticated_tenant_id(api_key)` helper pattern used in `benchmarks.py` and `formula_governance.py`:

```python
def _get_authenticated_tenant_id(api_key: APIKey) -> str:
    tenant_id = str(api_key.metadata.get("tenant_id", "") or "").strip()
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid tenant context")
    return tenant_id
```

The `'default'` fallback must be removed — it silently bypasses tenant isolation.

Scope: `services/layer3-knowledge/src/api/routes/value_packs.py`

---

### R3 — Remove AGENT_LEARNINGS.jsonl from Git tracking

`.agent/memory/episodic/AGENT_LEARNINGS.jsonl` is generated operational state (agent tool-call reflections). It must not be tracked in source control: it creates merge churn, leaks runtime metadata, and is not reproducible.

**Actions:**
1. Add `.agent/memory/episodic/` to `.gitignore`.
2. Run `git rm --cached .agent/memory/episodic/AGENT_LEARNINGS.jsonl` to untrack the file without deleting the local copy.

Scope: `.gitignore`, `.agent/memory/episodic/AGENT_LEARNINGS.jsonl` (index only)

---

### R4 — Wire check_runtime_canonical_imports.py into CI (warn-only)

`scripts/ci/check_runtime_canonical_imports.py` detects non-canonical `value_fabric.layer*` runtime imports in service code. It is not yet invoked by any CI workflow.

**Actions:**
1. Add a CI step to an appropriate existing workflow (e.g., `contract-compliance.yml` or `drift-check.yml`) that runs:
   ```bash
   python scripts/ci/check_runtime_canonical_imports.py
   ```
   without `--strict` so it reports violations but does not block the pipeline.
2. The step should print findings to CI logs (stdout is sufficient; the script already formats output).
3. Add a comment in the workflow step noting the `--strict` promotion path once violations reach zero.

Scope: `.github/workflows/` (one existing workflow file)

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | `test_benchmark_policies_route.py` uses `SimpleNamespace(metadata={"tenant_id": ...})` for all happy-path cases |
| AC2 | A parametrized hostile test covers: empty `metadata`, `tenant_id=""`, `tenant_id=None`, `metadata=None`, and missing `metadata` attr — all assert `HTTPException(401)` |
| AC3 | Hostile tests assert the Neo4j session is **not** called when tenant extraction fails |
| AC4 | `value_packs.py` uses `_get_authenticated_tenant_id(api_key)` (or equivalent inline logic reading `api_key.metadata["tenant_id"]`); the `'default'` fallback is removed |
| AC5 | `.gitignore` contains `.agent/memory/episodic/` |
| AC6 | `AGENT_LEARNINGS.jsonl` is no longer tracked by Git (`git ls-files` does not list it) |
| AC7 | A CI workflow step runs `check_runtime_canonical_imports.py` in warn-only mode |
| AC8 | The CI step does not block the pipeline on violations (exit code 0 when `--strict` is absent) |
| AC9 | All existing L3 tests pass after the `value_packs.py` and test-file changes |

---

## Implementation Steps

1. **Update `test_benchmark_policies_route.py`**
   - Replace all `SimpleNamespace(tenant_id=...)` with `SimpleNamespace(metadata={"tenant_id": ...})`.
   - Add a parametrized `test_rejects_api_key_without_valid_tenant_metadata` test covering the five hostile shapes.
   - Assert `HTTPException(status_code=401)` is raised and the Neo4j session mock is not called.

2. **Migrate `value_packs.py` tenant extraction**
   - Add a `_get_authenticated_tenant_id(api_key)` helper near the top of the route module (after imports).
   - Replace line 1469's `api_key.tenant_id if hasattr(...)` pattern with a call to the helper.
   - Remove the `'default'` fallback entirely.

3. **Untrack AGENT_LEARNINGS.jsonl**
   - Append `.agent/memory/episodic/` to `.gitignore`.
   - Run `git rm --cached .agent/memory/episodic/AGENT_LEARNINGS.jsonl`.

4. **Wire CI import-drift check**
   - Add a warn-only step for `check_runtime_canonical_imports.py` to `contract-compliance.yml` (alongside the other import-check steps).
   - Include a comment indicating the `--strict` promotion path per `DEPRECATED.md` timeline (target: 2026-06-30).

5. **Run targeted tests**
   - `pytest services/layer3-knowledge/tests/test_benchmark_policies_route.py -v`
   - `pytest services/layer3-knowledge/tests/ -v --tb=short` (full L3 suite)
   - Verify `git ls-files .agent/` no longer lists `AGENT_LEARNINGS.jsonl`.

---

## Risk / Follow-up

- **`value_packs.py` callers**: Any caller that previously relied on the `'default'` tenant fallback will now receive a `401`. This is the correct fail-closed behavior, but callers should be audited if integration tests exist for that endpoint.
- **`check_runtime_canonical_imports.py` robustness**: The script uses regex-over-text, which may produce false positives from comments or string literals. Promotion to `--strict` should be deferred until the false-positive rate is confirmed acceptable or AST-based detection is evaluated.
- **WebSocket manager singleton**: In-memory singleton state (`_ws_manager`) is not addressed in this spec. Multi-instance deployment behavior should be documented separately.
- **`--strict` CI promotion**: Once the current non-canonical import count reaches zero (per `DEPRECATED.md` timeline targeting 2026-06-30), the CI step added in step 4 should be updated to `--strict`.
