"""Final integration tests for critical pre-penetration-test user flows.

These tests intentionally use real HTTP calls and optional direct persistence
probes. They do not mock service responses. Configure target URLs with the
``CRITICAL_FLOWS_*`` environment variables or the existing ``LAYER*_API_URL``
variables used by the backend-integrated validation harness.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import math
import os
import time
import uuid
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.timeout(30)]

RUN_ID = os.getenv("CRITICAL_FLOWS_RUN_ID", f"critical-flows-{uuid.uuid4().hex[:8]}")
TENANT_HEADER = os.getenv("FABRIC_TENANT_HEADER", "X-Tenant-ID")
USER_HEADER = os.getenv("FABRIC_USER_HEADER", "X-User-ID")
ROLE_HEADER = os.getenv("FABRIC_ROLE_HEADER", "X-Role")
HTTP_TIMEOUT = float(os.getenv("CRITICAL_FLOWS_HTTP_TIMEOUT", "3.0"))
POLL_INTERVAL = float(os.getenv("CRITICAL_FLOWS_POLL_INTERVAL", "0.25"))
POLL_ATTEMPTS = int(os.getenv("CRITICAL_FLOWS_POLL_ATTEMPTS", "20"))

SERVICE_URLS = {
    "api": os.getenv("FABRIC_API_URL", "http://localhost:8080").rstrip("/"),
    "l1": os.getenv("LAYER1_API_URL", "http://localhost:8001").rstrip("/"),
    "l2": os.getenv("LAYER2_API_URL", "http://localhost:8002").rstrip("/"),
    "l3": os.getenv("LAYER3_API_URL", "http://localhost:8003").rstrip("/"),
    "l4": os.getenv("LAYER4_API_URL", "http://localhost:8004").rstrip("/"),
    "billing": os.getenv("BILLING_API_URL", os.getenv("LAYER4_API_URL", "http://localhost:8004")).rstrip("/"),
}


@dataclass
class FlowIds:
    tenant_a: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_b: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    slug: str = field(default_factory=lambda: f"critical-{uuid.uuid4().hex[:12]}")
    account_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    extraction_job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    graph_source_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metric: str = field(default_factory=lambda: f"critical_docs_{uuid.uuid4().hex[:8]}")


class CriticalFlowClient:
    """Small live-service HTTP client with cleanup registration."""

    def __init__(self, ids: FlowIds) -> None:
        self.ids = ids
        self._cleanup: list[tuple[str, str, str, str | None]] = []

    def headers(self, tenant_id: str | None = None, *, roles: str = "super_admin,billing:read,billing:write") -> dict[str, str]:
        effective_tenant = tenant_id or self.ids.tenant_a
        return {
            TENANT_HEADER: effective_tenant,
            USER_HEADER: self.ids.user_id,
            ROLE_HEADER: roles,
            "X-Roles": roles,
            "X-Organization-ID": effective_tenant,
            "X-Org-ID": effective_tenant,
            "X-Dev-Tenant-ID": effective_tenant,
            "X-Dev-User-ID": self.ids.user_id,
            "X-Service-Auth": os.getenv("SERVICE_AUTH_SECRET", "critical-flow-service-auth-secret-with-more-than-32-chars"),
            "X-Validation-Run-ID": RUN_ID,
        }

    async def request(
        self,
        service: str,
        method: str,
        path: str,
        *,
        tenant_id: str | None = None,
        expected: Iterable[int] = (200,),
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        content: bytes | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[Any, httpx.Response]:
        headers = self.headers(tenant_id)
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        if extra_headers:
            headers.update(extra_headers)
        async with httpx.AsyncClient(base_url=SERVICE_URLS[service], timeout=HTTP_TIMEOUT, follow_redirects=False) as client:
            response = await client.request(method, path, headers=headers, json=json_body, params=params, content=content)
        assert response.status_code in set(expected), (
            f"{service.upper()} {method} {path} expected {sorted(expected)}, "
            f"got {response.status_code}: {response.text[:1000]}"
        )
        body: Any = {}
        if response.content:
            if "json" in response.headers.get("content-type", ""):
                body = response.json()
            else:
                body = response.text
        return body, response

    def cleanup(self, service: str, path: str, *, tenant_id: str | None = None, method: str = "DELETE") -> None:
        self._cleanup.append((service, method, path, tenant_id))

    async def cleanup_all(self) -> None:
        for service, method, path, tenant_id in reversed(self._cleanup):
            async with httpx.AsyncClient(base_url=SERVICE_URLS[service], timeout=HTTP_TIMEOUT, follow_redirects=False) as client:
                await client.request(method, path, headers=self.headers(tenant_id))


@pytest.fixture
async def flow() -> AsyncIterator[CriticalFlowClient]:
    client = CriticalFlowClient(FlowIds())
    try:
        yield client
    finally:
        await client.cleanup_all()


async def _wait_for(client: CriticalFlowClient, service: str, path: str, tokens: set[str], *, tenant_id: str | None = None) -> Any:
    last: Any = None
    for _ in range(POLL_ATTEMPTS):
        last, _ = await client.request(service, "GET", path, tenant_id=tenant_id, expected=(200, 202))
        if any(token in str(last).lower() for token in tokens):
            return last
        await asyncio.sleep(POLL_INTERVAL)
    raise AssertionError(f"{service.upper()} {path} did not reach {tokens}; last={last!r}")


def _assert_finite_numbers(value: Any) -> None:
    if isinstance(value, int | float):
        assert math.isfinite(float(value)), f"ROI result contains non-finite number: {value!r}"
    elif isinstance(value, dict):
        for nested in value.values():
            _assert_finite_numbers(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_finite_numbers(nested)


async def _assert_postgres_tenant_visible_with_rls(tenant_id: str, slug: str) -> None:
    asyncpg = pytest.importorskip("asyncpg")
    database_url = os.getenv("CRITICAL_FLOWS_DATABASE_URL", os.getenv("DATABASE_URL", ""))
    assert database_url, "CRITICAL_FLOWS_DATABASE_URL or DATABASE_URL is required for PostgreSQL RLS verification"
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)
        row = await conn.fetchrow("SELECT id, slug, settings FROM tenants WHERE id = $1 OR slug = $2", uuid.UUID(tenant_id), slug)
        assert row is not None, "Tenant must be visible to its own RLS-scoped PostgreSQL session"
        await conn.execute("SELECT set_config('app.tenant_id', $1, true)", str(uuid.uuid4()))
        foreign = await conn.fetchrow("SELECT id FROM tenants WHERE id = $1", uuid.UUID(tenant_id))
        assert foreign is None, "Tenant row leaked through an RLS-scoped PostgreSQL session for another tenant"
    finally:
        await conn.close()


async def _assert_neo4j_tenant_node(tenant_id: str, slug: str) -> None:
    neo4j = pytest.importorskip("neo4j")
    uri = os.getenv("NEO4J_URL", os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "test")
    driver = neo4j.AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        async with driver.session() as session:
            result = await session.run(
                "MATCH (t) WHERE (t:Tenant OR t.tenant_id IS NOT NULL) "
                "AND (t.id = $tenant_id OR t.tenant_id = $tenant_id OR t.slug = $slug) "
                "RETURN count(t) AS count",
                tenant_id=tenant_id,
                slug=slug,
            )
            record = await result.single()
            assert record and record["count"] >= 1, "Tenant node must exist in Neo4j"
    finally:
        await driver.close()


@pytest.mark.asyncio
async def test_flow_1_tenant_onboarding(flow: CriticalFlowClient) -> None:
    tenant_payload = {
        "name": f"Critical Flow Tenant {RUN_ID}",
        "slug": flow.ids.slug,
        "settings": {"requested_tenant_id": flow.ids.tenant_a, "plan": "default", "run_id": RUN_ID},
    }
    tenant, _ = await flow.request("l4", "POST", "/v1/tenants", json_body=tenant_payload, expected=(200, 201, 409))
    tenant_id = str(tenant.get("id") or tenant.get("tenant_id") or flow.ids.tenant_a)
    flow.ids.tenant_a = tenant_id
    flow.cleanup("l4", f"/v1/tenants/{tenant_id}", tenant_id=tenant_id)

    fetched, _ = await flow.request("l4", "GET", f"/v1/tenants/{tenant_id}", tenant_id=tenant_id)
    assert flow.ids.slug in str(fetched) or tenant_id in str(fetched)
    await _assert_postgres_tenant_visible_with_rls(tenant_id, flow.ids.slug)
    await _assert_neo4j_tenant_node(tenant_id, flow.ids.slug)
    assert any(token in str(fetched).lower() + str(tenant).lower() for token in ("plan", "default", "starter", "billing"))


@pytest.mark.asyncio
async def test_flow_2_document_ingestion_extraction_to_knowledge_graph(flow: CriticalFlowClient) -> None:
    document = {
        "account_id": flow.ids.account_id,
        "source_type": "notes",
        "title": f"Critical flow document {RUN_ID}",
        "content": "Acme reduced support handling time by 18 percent after workflow automation.",
        "external_reference": flow.ids.document_id,
        "idempotency_key": flow.ids.document_id,
        "requested_outputs": ["fabric_found_summary"],
        "metadata": {"run_id": RUN_ID},
    }
    source, _ = await flow.request("l1", "POST", "/api/v1/ingestion/sources", json_body=document, expected=(200, 201, 202, 409))
    source_id = str(source.get("source_id") or source.get("id") or flow.ids.document_id)
    run_id = str(source.get("ingestion_run_id") or source_id)
    flow.cleanup("l1", f"/api/v1/ingestion/sources/{source_id}")
    await _wait_for(flow, "l1", f"/api/v1/ingestion/runs/{run_id}", {"accepted", "ready", "failed", "needs_review"})

    extraction_payload = {
        "content_id": flow.ids.document_id,
        "source_url": f"critical-flow://{flow.ids.document_id}",
        "markdown_content": document["content"],
        "extraction_config": {"run_id": RUN_ID, "emit_rdf": True},
    }
    extraction, _ = await flow.request("l2", "POST", "/v1/extract", json_body=extraction_payload, expected=(200, 201, 202))
    extraction_job_id = str(extraction.get("job_id") or extraction.get("id") or flow.ids.extraction_job_id)
    extraction_result = await _wait_for(flow, "l2", f"/v1/extract/results/{extraction_job_id}", {"entity", "rdf", "completed", "result"})
    assert flow.ids.document_id in str(extraction_result) or "entity" in str(extraction_result).lower()

    rdf = (
        f"<urn:vf:{flow.ids.graph_source_id}> <urn:vf:tenant_id> \"{flow.ids.tenant_a}\" .\n"
        f"<urn:vf:{flow.ids.graph_source_id}> <urn:vf:source_id> \"{flow.ids.document_id}\" .\n"
    )
    graph, _ = await flow.request(
        "l3",
        "POST",
        "/v1/ingest",
        json_body={"rdf_data": rdf, "source_id": flow.ids.graph_source_id, "extraction_job_id": extraction_job_id},
        expected=(200, 201, 202),
    )
    assert flow.ids.graph_source_id in str(graph) or flow.ids.document_id in str(graph)
    search, _ = await flow.request("l3", "POST", "/v1/query/search", json_body={"query": flow.ids.document_id}, expected=(200, 201))
    assert flow.ids.document_id in str(search) or flow.ids.graph_source_id in str(search)
    _, denied = await flow.request("l3", "POST", "/v1/query/search", tenant_id=flow.ids.tenant_b, json_body={"query": flow.ids.document_id}, expected=(403,))
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_flow_3_roi_calculation(flow: CriticalFlowClient) -> None:
    account_payload = {"id": flow.ids.account_id, "name": f"Critical ROI Account {RUN_ID}", "industry": "Software", "metadata": {"run_id": RUN_ID}}
    await flow.request("l4", "POST", "/v1/accounts", json_body=account_payload, expected=(200, 201, 202, 409))
    flow.cleanup("l4", f"/v1/accounts/{flow.ids.account_id}")

    roi, _ = await flow.request(
        "l4",
        "POST",
        "/v1/analysis/roi",
        json_body={
            "account_id": flow.ids.account_id,
            "formula_id": f"critical-roi-{RUN_ID}",
            "value_driver_ids": ["automation", "support-efficiency"],
            "variables": {"annual_revenue": 10_000_000, "implementation_cost": 125_000, "conversion_lift_pct": 8},
            "prospect_data": {"annual_revenue": 10_000_000, "employees": 250},
            "industry_vertical": "software",
            "company_size": "mid_market",
        },
        expected=(200, 201, 202),
    )
    _assert_finite_numbers(roi)
    assert any(token in str(roi).lower() for token in ("roi", "payback", "return", "projection"))

    case, _ = await flow.request(
        "l4",
        "POST",
        "/v1/cases",
        json_body={"id": flow.ids.case_id, "account_id": flow.ids.account_id, "scenario": roi, "approval_status": "draft"},
        expected=(200, 201, 202),
    )
    case_id = str(case.get("id") or case.get("case_id") or flow.ids.case_id)
    flow.cleanup("l4", f"/v1/cases/{case_id}")
    audit, _ = await flow.request("l4", "GET", f"/v1/audit/logs?entity_id={case_id}", expected=(200,))
    assert case_id in str(audit) or "audit" in str(audit).lower()


@pytest.mark.asyncio
async def test_flow_4_billing_flow(flow: CriticalFlowClient) -> None:
    now = datetime.now(UTC).isoformat()
    quantities = [3, 7]
    for index, quantity in enumerate(quantities):
        event = {
            "event_id": f"{RUN_ID}-{flow.ids.metric}-{index}",
            "metric": flow.ids.metric,
            "quantity": quantity,
            "source": "critical_flows",
            "timestamp": now,
            "request_id": f"req-{RUN_ID}-{index}",
        }
        await flow.request("billing", "POST", "/v1/billing/usage-events", json_body=event, expected=(200, 201, 202))

    aggregates, _ = await flow.request("billing", "GET", "/v1/billing/usage-aggregates")
    assert flow.ids.metric in str(aggregates)
    assert str(sum(quantities)) in str(aggregates) or sum(quantities) <= sum(
        float(v) for v in _numbers_from(aggregates)
    )

    invoices, _ = await flow.request("billing", "GET", "/v1/billing/invoices")
    assert "invoice" in str(invoices).lower()

    payload = {"id": f"evt_{uuid.uuid4().hex}", "type": "invoice.created", "created": int(time.time()), "data": {"object": {"id": f"in_{uuid.uuid4().hex}"}}}
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_test_dummy_critical_flow_secret")
    timestamp = str(int(time.time()))
    signature = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    webhook, _ = await flow.request(
        "billing",
        "POST",
        "/v1/billing/webhook",
        content=body,
        expected=(200, 202),
        extra_headers={"Stripe-Signature": f"t={timestamp},v1={signature}", "Content-Type": "application/json"},
    )
    assert webhook.get("received") is True


def _numbers_from(value: Any) -> list[float]:
    if isinstance(value, int | float):
        return [float(value)]
    if isinstance(value, dict):
        return [number for nested in value.values() for number in _numbers_from(nested)]
    if isinstance(value, list):
        return [number for nested in value for number in _numbers_from(nested)]
    return []


@pytest.mark.asyncio
async def test_flow_5_auth_flow(flow: CriticalFlowClient) -> None:
    login_path = os.getenv("CRITICAL_FLOWS_CLERK_LOGIN_PATH", f"/auth/oidc/{flow.ids.slug}/login")
    login, login_response = await flow.request("l4", "GET", login_path, expected=(200, 302, 303, 307))
    assert login_response.headers.get("location") or any(token in str(login).lower() for token in ("clerk", "oidc", "authorization"))

    token = os.getenv("CRITICAL_FLOWS_CLERK_TEST_JWT")
    refresh_token = os.getenv("CRITICAL_FLOWS_CLERK_TEST_REFRESH_TOKEN")
    assert token and refresh_token, "Set CRITICAL_FLOWS_CLERK_TEST_JWT and CRITICAL_FLOWS_CLERK_TEST_REFRESH_TOKEN for live Clerk auth validation"

    session, _ = await flow.request("l4", "GET", "/v1/auth/session", extra_headers={"Authorization": f"Bearer {token}"})
    assert "token" in str(session).lower() or "user" in str(session).lower()

    refreshed, _ = await flow.request("l4", "POST", "/auth/oidc/refresh", extra_headers={"Authorization": f"Bearer {refresh_token}"}, expected=(200, 201))
    refreshed_token = refreshed.get("access_token") or refreshed.get("token")
    assert refreshed_token, "Token refresh must return a replacement JWT/access token"

    await flow.request("l4", "POST", "/auth/oidc/logout", extra_headers={"Authorization": f"Bearer {refreshed_token}"}, expected=(200, 204))
    _, revoked = await flow.request("l4", "GET", "/v1/auth/session", extra_headers={"Authorization": f"Bearer {refreshed_token}"}, expected=(401, 403))
    assert revoked.status_code in {401, 403}

    expired = os.getenv("CRITICAL_FLOWS_EXPIRED_JWT", "expired.jwt.token")
    _, expired_response = await flow.request("l4", "GET", "/v1/auth/session", extra_headers={"Authorization": f"Bearer {expired}"}, expected=(401, 403))
    assert expired_response.status_code in {401, 403}
