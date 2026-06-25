---
skill_id: invariant-driven-testing
name: invariant-driven-testing
version: 1.0.0
description: Turn user workflows into testable business and security invariants through adversarial design, tenant isolation, full-stack automation, business-rule validation, failure injection, observability, environment engineering, and honest reporting.
side_effects: write
timeout_ms: 300000
required_context:
  - project_graph
  - test_inventory
  - production_invariants
allowed_agents:
  - "*"
---

# Invariant-Driven Testing

> **Prove the invariant, not the screen.**

This skill is about turning user workflows into testable **business and security invariants**. It is not about automating clicks. It is about asking, for every workflow: *what must remain true for this to be safe and correct?* and then proving that truth through tests.

A complete test of "export is disabled" must verify the disabled button, call the export API directly, confirm the server rejects drafts, approve with a separate reviewer, export successfully, and check the audit record.

---

## When to Use

Use this skill when:

- A user workflow is being added or changed and you need to know what could silently fail.
- A security or business boundary is claimed but not proven (tenant isolation, approvals, export rules).
- Existing tests rely on mocked auth, mocked APIs, or UI-only assertions.
- You need to write full-stack Playwright tests that exercise real auth, database, Redis, and workers.
- A failure mode is suspected but not reproduced (timeout, outage, retry, duplicate request).
- You need an honest readiness report that distinguishes mocked from live, UI from API-enforced, and passed from skipped.

---

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workflow` | string | yes | The user workflow to test, e.g. "export approved evidence". |
| `target_layer` | string | yes | `frontend`, `layer1`, `layer2`, `layer3`, `layer4`, `layer5`, `layer6`, or `cross_layer`. |
| `scope` | array | no | Subskills to apply. Default: `all`. Options: `adversarial`, `tenant_isolation`, `full_stack`, `business_rules`, `failure_injection`, `observability`, `environment`, `readiness`. |
| `severity_threshold` | string | no | Minimum severity to address. `P0` (default), `P1`, `P2`, `P3`. |
| `generate_tests` | boolean | no | If true, produce actual test files. Default: `true`. |
| `report_path` | string | no | Where to write the readiness report. Default: `artifacts/testing/invariant-driven-report.md`. |

---

## Steps

1. **Decompose the workflow into invariants.**
   List every business and security claim the workflow implies. For each claim, write a positive, negative, and adversarial test intent.

2. **Apply the subskills in priority order.**
   Run the relevant subskills below against the workflow. Do not skip an earlier priority because a later one is easier.

3. **Generate tests that prove the invariant.**
   Prefer tests that bypass UI when the real boundary is the API, database, or worker. Use UI tests only when the behavior is genuinely UI-specific.

4. **Run the tests and collect evidence.**
   Capture network traces, DB state, logs, audit records, screenshots, and Playwright traces. Every conclusion must be reproducible.

5. **Produce an honest readiness report.**
   Label every finding as mocked/live, UI-tested/API-enforced, passed/skipped, verified/assumed.

---

## Subskills

### 1. Adversarial Test Design

Ask: *How could this appear to work while actually failing?*

Test vectors:
- Direct URL access to a resource the user should not reach.
- Direct API calls that bypass the UI path.
- Stale sessions, expired tokens, replayed cookies.
- Altered tenant IDs in headers, body, query string, or route.
- Skipped approvals, skipped confirmations, skipped MFA.
- Retries that double-apply, retries after partial failure.
- Concurrent edits that race against each other.
- Out-of-order events (webhook before action, action before precondition).

Required output:
- A list of adversarial scenarios for the workflow.
- At least one test per scenario that would fail if the boundary is missing.

Example:
```python
async def test_export_rejected_before_approval(client, reviewer, draft_export):
    # Bypass the UI: call the export endpoint directly on a draft.
    response = await client.post(
        f"/api/exports/{draft_export.id}/execute",
        headers=auth_headers_for(reviewer, tenant=tenant_a),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Export requires approved status"
```

### 2. Tenant-Isolation and Authorization Testing

Verify every read, write, search, export, download, agent retrieval, and background job across multiple tenants and roles. UI hiding is not sufficient.

Test vectors:
- Cross-tenant read (404 or 403, never 200 with foreign data).
- Cross-tenant write (denied, no side effects in other tenant).
- Cross-tenant search (foreign data absent from results).
- Cross-tenant export/download (denied).
- Agent retrieval across tenants (denied or empty).
- Background jobs scoped to tenant (cannot read foreign data).
- Role mismatch: admin action by member, member action by guest.
- Tenant ID mismatch between header, body, query, and route.
- Missing tenant context fails closed.

Required output:
- A matrix of tenant × role × operation with expected result.
- Tests for every denied operation that verify both the response and the side-effect absence.

Example:
```python
async def test_member_cannot_export_admin_only(client, member, admin_export):
    response = await client.post(
        f"/api/exports/{admin_export.id}/execute",
        headers=auth_headers_for(member, tenant=tenant_a),
    )
    assert response.status_code == 403
    # Also verify the export did not run in the audit log.
    audit = await get_audit_events(tenant=tenant_a, action="export_executed")
    assert not any(e.resource_id == admin_export.id for e in audit)
```

### 3. Full-Stack Playwright Automation

Exercise real authentication, frontend, API, database, Redis, workers, and audit records. Avoid tests based entirely on mocked responses.

Test vectors:
- Log in through the real auth provider, not a mock bypass.
- Perform the workflow in the browser.
- Intercept and inspect the real API calls (do not mock them unless the external dependency is the test target).
- Verify the database state after the workflow.
- Verify Redis/cache state after the workflow.
- Verify worker queue state and job completion.
- Verify audit records were written.
- Verify trace/span propagation.

Required output:
- A Playwright test file with semantic selectors and web-first assertions.
- A companion API/assertion module that verifies backend state independently.
- Evidence: screenshots, trace, and network HAR on failure.

Example:
```typescript
test('export workflow requires approval and creates audit record', async ({ page }) => {
  const exportPage = new ExportPage(page);
  await exportPage.loginAs(reviewer);
  await exportPage.open(draftExport.id);

  // UI layer: button is disabled for drafts
  await expect(exportPage.executeButton).toBeDisabled();

  // API layer: direct call is rejected
  const apiResponse = await page.request.post(`/api/exports/${draftExport.id}/execute`);
  expect(apiResponse.status()).toBe(409);

  // Approve with a different reviewer
  await exportPage.loginAs(approver);
  await exportPage.approve(draftExport.id);

  // Execute
  await exportPage.loginAs(reviewer);
  await exportPage.execute(draftExport.id);

  // Backend evidence
  const audit = await exportPage.getAuditEvents('export_executed');
  expect(audit).toContainEqual(expect.objectContaining({
    resource_id: draftExport.id,
    actor_id: reviewer.id,
  }));
});
```

### 4. Business-Rule Validation

Independently verify calculations, approval state transitions, evidence requirements, export restrictions, and audit obligations.

Test vectors:
- Recalculate totals and compare to the API response.
- Trigger every state transition and assert valid/invalid transitions.
- Assert that required evidence is present before progression.
- Assert export restrictions (format, size, retention, scope).
- Assert audit obligations (who, when, what changed, before/after values).
- Test with boundary values and realistic edge data.

Required output:
- Independent computation fixtures.
- A state-transition table with allowed and forbidden transitions.
- Tests that would fail if the rule is implemented only in the UI.

Example:
```python
async def test_roi_calculation_matches_independent_formula(client, tenant_a):
    response = await client.get(
        f"/api/roi/{opportunity_id}",
        headers=auth_headers_for(tenant=tenant_a),
    )
    assert response.status_code == 200
    api_result = response.json()

    expected = compute_roi_formula(
        revenue=api_result["revenue"],
        cost=api_result["cost"],
        discount_rate=DEFAULT_DISCOUNT_RATE,
    )
    assert abs(api_result["roi"] - expected) < 1e-6
```

### 5. Failure-Injection Testing

Test provider timeouts, Redis outages, failed workers, expired sessions, malformed responses, duplicate requests, and retry exhaustion.

Test vectors:
- Timeout the upstream provider and assert graceful degradation.
- Stop or flush Redis and assert the system fails closed.
- Kill a worker mid-job and assert retry/dlq behavior.
- Expire the session during the workflow and assert re-auth or failure.
- Return malformed JSON from a provider and assert safe handling.
- Send duplicate requests with the same idempotency key and assert no double effect.
- Exhaust retries and assert the alert/notification path.
- Corrupt a message in the queue and assert it goes to the DLQ.

Required output:
- A failure-mode matrix with injected fault and expected resilience behavior.
- Tests that exercise the real queue/cache/provider paths, not just unit stubs.

Example:
```python
async def test_export_retry_exhaustion_sends_alert(
    client, worker, monkeypatch, tenant_a
):
    monkeypatch.setattr("services.export.execute_export", raise_timeout)

    response = await client.post(
        "/api/exports",
        json=valid_export_request(tenant=tenant_a),
        headers=auth_headers_for(tenant=tenant_a),
    )
    assert response.status_code == 202

    await run_worker_until(worker, job_id=response.json()["job_id"], max_retries=3)

    alerts = await get_alerts(tenant=tenant_a, severity="critical")
    assert any("export retry exhausted" in a.message for a in alerts)

    # No duplicate export artifacts
    exports = await list_exports(tenant=tenant_a)
    assert len(exports) == 1
```

### 6. Observability and Evidence Collection

Inspect network requests, database state, traces, logs, audit events, screenshots, and Playwright traces. Every conclusion should be reproducible.

Test vectors:
- Capture all network requests and responses during the workflow.
- Query the database and assert the expected state change.
- Read structured logs and assert the expected log lines.
- Read distributed traces and assert span presence and attributes.
- Read audit events and assert actor, resource, action, and timestamp.
- Capture screenshots and Playwright traces on failure and on critical steps.
- Correlate evidence across layers: request ID, trace ID, job ID, audit ID.

Required output:
- An evidence collection plan attached to the test.
- A reproducible artifact set for every test failure.
- A cross-layer correlation ID that ties UI action to API call to DB row to audit event.

Example:
```python
# In the test teardown or fixture, collect:
- page.network_requests()  # HAR
- page.screenshot(path=f"{test_name}.png")
- page.context().tracing.stop(path=f"{test_name}.zip")
- db.snapshot(tenant=tenant_a, tables=["exports", "audit_log"])
- logs.query(trace_id=test_trace_id)
- traces.get(trace_id=test_trace_id)
```

### 7. Test-Environment Engineering

Create deterministic tenants, users, roles, accounts, and seeded data. Reset state cleanly and run against production-like infrastructure.

Test vectors:
- Spin up isolated tenants per test or per test file.
- Create users with known roles, passwords, and MFA states.
- Seed accounts, products, opportunities, evidence, and history deterministically.
- Reset state between tests without cross-contamination.
- Run against a Docker Compose stack that mirrors production (PostgreSQL, Redis, Neo4j, Keycloak, workers).
- Use production-like data volumes for at least one smoke test per critical path.
- Avoid reliance on shared staging accounts that may be mutated by other tests.

Required output:
- Fixture factories for tenant, user, role, account, and workflow data.
- A deterministic reset strategy (transaction rollback, isolated schema, or seeded fresh DB).
- A production-like stack configuration for local and CI runs.

Example:
```python
@pytest.fixture
async def isolated_tenant(env_factory):
    tenant = await env_factory.create_tenant(
        slug=f"tenant-{uuid.uuid4().hex[:8]}",
        plan="enterprise",
    )
    await env_factory.create_users(tenant, roles=["admin", "reviewer", "member"])
    await env_factory.seed_accounts(tenant, count=5)
    yield tenant
    await env_factory.destroy(tenant)
```

### 8. Honest Readiness Reporting

Distinguish:
- mocked from live,
- UI-tested from API-enforced,
- passed from skipped,
- verified from assumed.

Report format:
- For every invariant, state the evidence type and quality.
- Label `mocked` vs `live` explicitly.
- Label `ui_only` vs `api_enforced` vs `db_enforced` vs `worker_enforced`.
- Label `verified` vs `assumed`.
- Label `passed` vs `skipped` vs `failed` with a reason.
- List residual risk and what is still unverified.
- Recommend whether the workflow can ship.

Required output:
- A readiness report at the configured `report_path`.
- A verdict: `Go`, `Conditional Go`, or `No-Go`.

Example report row:
```markdown
| Invariant | Evidence | Live/Mocked | Enforced At | Verified/Assumed | Status |
|-----------|----------|-------------|-------------|------------------|--------|
| Export requires approval before execution | UI disabled + direct API 409 + audit log absent | Live | API + DB | Verified | Pass |
```

---

## Output

The skill produces:

1. `tests_written` — array of test file paths and test names.
2. `gap_matrix` — table of invariants vs. subskills with status.
3. `verification_result` — `pass`, `fail`, or `partial`.
4. `report_path` — path to the readiness report.
5. `readiness_assessment` — `Go`, `Conditional Go`, or `No-Go` with rationale.

---

## Edge Cases

- **No backend API exists yet**: document the invariant as a contract test or stub and mark it `assumed`.
- **External dependency unavailable**: run the test against a local simulator that mimics the real failure modes, but label it `mocked`.
- **Flaky environment**: run the test five times; if it is non-deterministic, fix the test or the environment, never mark it passed on a single run.
- **Cannot reset state**: redesign the test to use isolated fixtures; do not rely on shared state.
- **Test is too slow**: split it into smaller invariant tests, but do not drop the adversarial or backend-enforcement checks.

---

## Anti-Patterns

- **UI-only testing of a security boundary**: a hidden button is not proof of an enforced API.
- **Over-mocking auth or data**: if the mock is the only reason the test passes, it is not a test of the invariant.
- **Vague assertions**: `assert response.ok` or `assert len(data) > 0` prove nothing about the invariant.
- **Skipping negative tests**: happy-path coverage without adversarial coverage is incomplete.
- **Assuming environment state**: tests must create and verify their own preconditions.
- **No evidence on failure**: a failed test without trace, screenshot, or DB snapshot is unactionable.
- **Reporting passed when skipped**: a skipped test is not a passing test; report it honestly.

---

## Verification Checklist

Before marking the workflow as tested:

- [ ] Every business invariant has a positive and negative test.
- [ ] Every security boundary has an adversarial test that calls the real API or DB.
- [ ] Tenant isolation is tested across read, write, search, export, download, agent, and job operations.
- [ ] No test relies solely on UI state for an API-enforced rule.
- [ ] Failure modes are reproduced with real infrastructure, not just unit stubs.
- [ ] Evidence is collected and correlated across UI, API, DB, cache, worker, and audit layers.
- [ ] The test environment is deterministic and reset cleanly between tests.
- [ ] The readiness report honestly distinguishes mocked/live, UI/API, verified/assumed, and passed/skipped.
- [ ] The final verdict is `Go`, `Conditional Go`, or `No-Go` with a clear rationale.
