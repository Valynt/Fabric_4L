# Test Gap Matrix - Fabric 4L

**Document:** P0/P1 Security Test Gaps
**Date:** 2026-04-28
**Severity:** P0 = Blocks Release, P1 = Core Workflow Missing Coverage

---

## Legend

| Severity | Definition |
|----------|------------|
| **P0** | Security/data boundary untested or bypassable - **BLOCKS RELEASE** |
| **P1** | Core production workflow lacks failure/negative coverage |
| **P2** | Brittle, incomplete, or overly mocked coverage |
| **P3** | Cleanup or maintainability improvement |

---

## P0 Gaps (Critical - Address First)

| # | Boundary | Risk | Existing Coverage | Missing Positive | Missing Negative | Target File | Verification |
|---|----------|------|-------------------|------------------|------------------|-------------|--------------|
| 1 | **WebSocket Authentication** | Unauthenticated WebSocket access allowed | None - WebSocket routes lack auth tests | Valid token allows connection | Missing/invalid token rejected | `websocket/test_auth.py` | `pytest tests/websocket/` |
| 2 | **WebSocket Tenant Isolation** | Cross-tenant WebSocket data leak | None | Tenant-A user only sees Tenant-A events | Tenant-A cannot subscribe to Tenant-B events | `websocket/test_tenant_isolation.py` | `pytest tests/websocket/` |
| 3 | **Tenant Lifecycle Enforcement** | Suspended/pending tenants can access resources | Status check exists but not tested | Active tenant gets 200 | Suspended→403, Deleted→404, Pending→403 | `test_tenant_lifecycle.py` | `pytest -m tenant_lifecycle` |
| 4 | **Rate Limiting Bypass** | No Redis = no rate limiting in multi-worker | Tests exist but skipif logic not verified | Rate limit enforced with Redis | Rate limit fails safe without Redis | `test_rate_limiting.py` | `pytest -m rate_limit` |
| 5 | **JWT/Header Tenant Mismatch** | X-Tenant-ID header can override JWT | `validate_context_consistency` exists | Matching tenant succeeds | Mismatch rejected with error | `test_tenant_mismatch.py` | `pytest tests/security/` |

---

## P1 Gaps (High Priority)

| # | Boundary | Risk | Existing Coverage | Missing Positive | Missing Negative | Target File | Verification |
|---|----------|------|-------------------|------------------|------------------|-------------|--------------|
| 6 | **API Key Scope Enforcement** | API key with limited scopes bypassed | Basic API key auth tested | Scoped key works for allowed endpoint | Scoped key rejected for disallowed endpoint | `test_api_key_scopes.py` | `pytest -m api_key` |
| 7 | **Graph Query Tenant Injection** | Neo4j Cypher injection bypasses isolation | Query validator exists | Valid query returns tenant-scoped results | Malicious query rejected/injection blocked | `test_graph_injection.py` | `pytest tests/security/` |
| 8 | **Audit Log Completeness** | Security events not logged | Audit emitter exists | Auth success logged | Auth failure logged with details | `test_audit_completeness.py` | `pytest -m audit` |
| 9 | **Cross-Layer Tenant Propagation** | Tenant context lost between layers | 16 cross-layer tests exist | Context propagates correctly | Missing context fails safe | `test_context_propagation.py` | `pytest tests/integration/` |
| 10 | **Secret Redaction in Errors** | Secrets exposed in error messages | Basic redaction tests exist | Normal error safe | Error with secret redacted | `test_secret_redaction_negative.py` | `pytest tests/security/` |
| 11 | **Admin Endpoint Protection** | Admin routes accessible to non-admins | Some RBAC tests exist | Admin access with valid role | Non-admin rejected (403) | `test_admin_protection.py` | `pytest tests/security/` |
| 12 | **Bulk Operation Isolation** | Bulk reads/writes leak across tenants | Concurrent isolation tested | Bulk ops stay within tenant | Cross-tenant bulk blocked | `test_bulk_isolation.py` | `pytest tests/security/` |

---

## P2 Gaps (Technical Debt)

| # | Boundary | Issue | Current State | Recommendation |
|---|----------|-------|---------------|----------------|
| 13 | **Skipped Tests** | 113 `@pytest.mark.skip` markers | Many integration tests skip without DB | Audit each skip - require reason + expiration |
| 14 | **Mock Overuse** | Security boundaries mocked out | `test_adversarial_auth.py` uses real client, but others mock | Replace mocks with real boundary tests |
| 15 | **Vague Assertions** | `assert result is not None` patterns | Present in older tests | Replace with exact value assertions |
| 16 | **Flaky Timing** | `asyncio.sleep()` in tests | Some integration tests | Use deterministic synchronization |
| 17 | **Test Data Coupling** | Shared fixtures mutate state | `conftest.py` fixtures | Ensure fixture isolation |

---

## Priority 1: WebSocket Auth (P0-1)

**File:** `services/layer4-agents/src/api/websocket/routes.py`

**Current State:**
```python
@router.websocket("/ws/workflows/{workflow_id}")
async def workflow_websocket(websocket: WebSocket, workflow_id: str, token: str = Query(...)):
    # Token decoded but no negative test for invalid/missing token
    payload = decode_jwt(token, jwt_secret)  # What if this fails?
```

**Required Tests:**

### Positive Test
```python
async def test_websocket_valid_token_accepts_connection(client, valid_token):
    """Valid JWT allows WebSocket connection."""
    with client.websocket_connect(f"/ws/workflows/123?token={valid_token}") as ws:
        assert ws.accepted
```

### Negative Tests
```python
async def test_websocket_missing_token_rejects_connection(client):
    """Missing token rejects WebSocket upgrade."""
    response = client.get("/ws/workflows/123")  # No token
    assert response.status_code == 401

async def test_websocket_invalid_token_rejects_connection(client):
    """Invalid token rejects WebSocket."""
    response = client.get("/ws/workflows/123?token=invalid")
    assert response.status_code == 401

async def test_websocket_expired_token_rejects_connection(client, expired_token):
    """Expired token rejects WebSocket."""
    response = client.get(f"/ws/workflows/123?token={expired_token}")
    assert response.status_code == 401
```

---

## Priority 2: Tenant Lifecycle (P0-3)

**File:** `shared/identity/middleware.py:312-334`

**Current Logic:**
```python
if tenant_status == "suspended":
    return Response(status_code=403, ...)
if tenant_status == "pending":
    return Response(status_code=403, ...)
if tenant_status == "deleted":
    return Response(status_code=404, ...)  # Don't reveal existence
```

**Required Tests:**

### Positive Test
```python
def test_active_tenant_can_access_resources(client, active_tenant_token):
    """Active tenant gets normal access."""
    response = client.get("/api/v1/entities", headers={"Authorization": f"Bearer {active_tenant_token}"})
    assert response.status_code == 200
```

### Negative Tests
```python
def test_suspended_tenant_rejected_with_403(client, suspended_tenant_token):
    """Suspended tenant gets 403 with specific error."""
    response = client.get("/api/v1/entities", headers={"Authorization": f"Bearer {suspended_tenant_token}"})
    assert response.status_code == 403
    assert response.json()["error"] == "tenant_suspended"

def test_pending_tenant_rejected_with_403(client, pending_tenant_token):
    """Pending tenant gets 403 with onboarding message."""
    response = client.get("/api/v1/entities", headers={"Authorization": f"Bearer {pending_tenant_token}"})
    assert response.status_code == 403
    assert response.json()["error"] == "tenant_pending"

def test_deleted_tenant_rejected_with_404(client, deleted_tenant_token):
    """Deleted tenant gets 404 (don't reveal existence)."""
    response = client.get("/api/v1/entities", headers={"Authorization": f"Bearer {deleted_tenant_token}"})
    assert response.status_code == 404
    assert response.json()["error"] == "tenant_not_found"
```

---

## Priority 3: Tenant Context Mismatch (P0-5)

**File:** `shared/identity/middleware.py:657-679`

**Current Logic:**
```python
def validate_context_consistency(jwt_context, header_tenant_id):
    if jwt_context.tenant_id != header_tenant_uuid:
        raise ValueError(f"Conflicting tenant_id: JWT has {jwt_context.tenant_id}, header has {header_tenant_uuid}")
```

**Gap:** This function exists but may not be called in all paths, and lacks negative tests.

**Required Tests:**

```python
def test_jwt_tenant_mismatch_with_header_rejected(client, tenant_a_token):
    """JWT tenant A + Header tenant B = Rejected."""
    response = client.get(
        "/api/v1/entities",
        headers={
            "Authorization": f"Bearer {tenant_a_token}",
            "X-Tenant-ID": "tenant-b-id"
        }
    )
    assert response.status_code == 400
    assert "conflicting tenant" in response.json()["detail"].lower()
```

---

## Implementation Plan

### Week 1: P0 Critical Gaps

1. **Day 1-2:** WebSocket authentication tests (P0-1, P0-2)
2. **Day 3-4:** Tenant lifecycle enforcement tests (P0-3)
3. **Day 5:** Tenant mismatch validation tests (P0-5)

### Week 2: P1 High Priority

4. **Day 1-2:** API key scope enforcement (P1-6)
5. **Day 3:** Graph query injection (P1-7)
6. **Day 4-5:** Audit completeness (P1-8)

### Week 3: Cleanup

7. **Day 1-2:** Address skipped tests audit (P2-13)
8. **Day 3-5:** Refactor brittle tests (P2-14, P2-15)

---

## Success Criteria

- [ ] All P0 gaps have positive + negative tests
- [ ] All P1 gaps have at least negative tests
- [ ] Zero P0 tests skipped in CI
- [ ] `make test-security` passes with 100% boundary coverage
- [ ] `make verify` includes new tests
