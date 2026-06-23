# Gate Domains Reference

## Table of Contents

1. [Security and Tenant Isolation](#1-security-and-tenant-isolation)
2. [Architecture Conformance and State Consistency](#2-architecture-conformance-and-state-consistency)
3. [Degraded Dependencies (Chaos)](#3-degraded-dependencies-chaos)
4. [Workflow Smoke Tests](#4-workflow-smoke-tests)
5. [Evidence and Provenance](#5-evidence-and-provenance)
6. [Observability, Audit, and Rollback](#6-observability-audit-and-rollback)

---

## 1. Security and Tenant Isolation

**Gate target**: `gate-security`
**Test directory**: `tests/security/`

### What to scan for

- Route files using deprecated DB dependencies without tenant context (RLS bypass)
- Write endpoints using optional auth (`get_optional_context`)
- Alembic migrations with `tenant_id` columns but no RLS policy
- RLS policies using unsafe `tenant_id IS NULL` pattern
- RLS policies without `FORCE ROW LEVEL SECURITY`
- Inconsistent GUC variable names across migrations (`app.tenant_id` vs `app.current_tenant`)
- Export/storage keys without tenant namespace prefix
- Background jobs without tenant context propagation
- JWT secret validation missing at startup

### Test patterns

**Route auth contract test** — scans all route files via AST/regex:
```python
def test_no_route_uses_deprecated_get_db():
    """Every authenticated route must use get_db_from_context, not get_db."""
    allowlist = {"oidc.py", "registration.py", "webhooks.py"}  # pre-auth
    for route_file in scan_route_files(ROUTE_DIRS):
        if os.path.basename(route_file) in allowlist:
            continue
        content = open(route_file).read()
        assert "Depends(get_db)" not in content, f"{route_file} bypasses RLS"
```

**RLS coverage test** — scans migrations:
```python
def test_all_tenant_tables_have_rls():
    """Every table with tenant_id must have an RLS policy."""
    rls_tables = extract_rls_tables_from_migrations(MIGRATIONS_DIR)
    model_tables = extract_tenant_id_tables_from_migrations(MIGRATIONS_DIR)
    missing = model_tables - rls_tables
    assert not missing, f"Tables without RLS: {missing}"
```

**Export namespace test** — verifies S3 keys include tenant_id:
```python
def test_export_keys_include_tenant_prefix():
    """Export S3 keys must be prefixed with tenant_id."""
    content = open(EXPORT_ROUTE_FILE).read()
    # Find upload_bytes calls and verify key construction includes tenant
    upload_calls = re.findall(r'object_key\s*=\s*(.+)', content)
    for call in upload_calls:
        assert "tenant_id" in call, f"Export key missing tenant prefix: {call}"
```

**Startup validation test** — verifies boot-time security checks:
```python
def test_jwt_secret_strength_in_production():
    """Production must reject JWT secrets shorter than 32 characters."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production", "JWT_SECRET": "short"}):
        with pytest.raises(SystemExit):
            validate_security_config()
```

---

## 2. Architecture Conformance and State Consistency

**Gate target**: `gate-state`
**Test directory**: `tests/state/`

### What to scan for

- Backend enum values missing from frontend TypeScript types
- Frontend type literals with no backend equivalent (orphan values)
- Duplicate enum aliases in backend (e.g., `WHITESPACE_ANALYSIS` and `WHITESPACE_ANALYSIS_WORKFLOW`)
- Workflow types defined in backend but unreachable from frontend create requests

### Test patterns

**State enum alignment** — parses both languages:
```python
def test_backend_statuses_exist_in_frontend():
    """Every backend WorkflowStatus must have a frontend equivalent."""
    backend = extract_python_enum(BACKEND_AGENT_STATE, "WorkflowStatus")
    frontend = extract_ts_type_literals(FRONTEND_WORKFLOWS_TS, "WorkflowStatus")
    missing = backend - frontend
    assert not missing, f"Backend statuses missing from frontend: {missing}"
```

---

## 3. Degraded Dependencies (Chaos)

**Gate target**: `gate-chaos`
**Test directory**: `tests/chaos/`

### What to test

- Redis timeout returns structured 503 (not 500 with stack trace)
- Database disconnect triggers connection pool recovery
- LLM provider timeout falls back to secondary provider
- No stack trace leakage in any error response
- Circuit breakers trip after threshold failures

### Test patterns

**Fault injection** — mock external dependencies:
```python
def test_redis_timeout_returns_503():
    """When Redis times out, the API returns 503 with structured error."""
    with patch("redis.Redis.get", side_effect=TimeoutError):
        response = client.get("/api/v1/some-cached-endpoint")
        assert response.status_code == 503
        body = response.json()
        assert "error" in body
        assert "traceback" not in json.dumps(body).lower()
```

---

## 4. Workflow Smoke Tests

**Gate target**: `gate-smoke`
**Test directory**: `tests/smoke/`

### What to test

- Each core workflow type can be created, transitions through expected states, and completes
- Workflow output conforms to expected schema
- Workflow cancellation works from any active state

### Test patterns

**End-to-end workflow** — uses test client with mocked LLM:
```python
def test_roi_workflow_completes():
    """ROI Calculator workflow transitions from pending to completed."""
    response = client.post("/api/v1/workflows", json={
        "workflow_type": "roi_calculator",
        "input_data": SAMPLE_ROI_INPUT,
    }, headers=tenant_a_headers)
    assert response.status_code == 201
    wf_id = response.json()["id"]
    # Poll or advance until completion
    status = advance_workflow(wf_id)
    assert status == "completed"
```

---

## 5. Evidence and Provenance

**Gate target**: `gate-agent`
**Test directory**: `tests/evals/`

### What to test

- Agent outputs conform to their Pydantic schemas
- Every citation resolves to a valid source document
- Golden trace regression (agent paths match known-good baselines)
- Export provenance metadata includes tenant, timestamp, user, and source hash

### Test patterns

**Schema conformance** — validate against Pydantic models:
```python
def test_agent_output_conforms_to_schema():
    """Every agent output must validate against its declared schema."""
    for agent_class in discover_agents():
        sample_output = run_agent_with_mock_input(agent_class)
        schema = agent_class.output_schema
        schema.model_validate(sample_output)  # Raises on invalid
```

---

## 6. Observability, Audit, and Rollback

**Gate target**: `gate-obs`
**Test directory**: `tests/obs/`

### What to test

- State-mutating API calls generate audit events
- Error responses increment Prometheus counters
- Trace IDs propagate from API gateway to background workers
- Grafana dashboard JSON references only metrics that exist in code
- Alembic migrations are reversible (downgrade functions exist and are non-empty)

### Test patterns

**Audit completeness** — verify audit emission:
```python
def test_state_mutations_generate_audit_events():
    """Every POST/PUT/DELETE endpoint must emit an audit event."""
    with capture_audit_events() as events:
        client.post("/api/v1/accounts", json=SAMPLE_ACCOUNT, headers=auth_headers)
    assert len(events) >= 1
    assert events[0]["action"] == "account.created"
    assert events[0]["tenant_id"] == TENANT_A_ID
```
