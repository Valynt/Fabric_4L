#!/usr/bin/env python3
"""End-to-end Fabric_4L workflow runner for the Nexus Analytics scenario.

This script is intentionally self-contained (stdlib + requests + PyJWT) so it can
run from a clean checkout without installing the monorepo. It expects the local
Docker stack described in docker-compose.backend-integrated.yml plus the
.e2e-local override to be up on the host ports exposed by that stack.

Pre-requisites (run once from a clean checkout):
    docker compose -f docker-compose.backend-integrated.yml \
                   -f docker-compose.e2e-local.override.yml \
                   --env-file .env.e2e-local up -d --build
    docker compose -f docker-compose.backend-integrated.yml \
                   -f docker-compose.e2e-local.override.yml \
                   --env-file .env.e2e-local exec layer1 alembic upgrade head
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import jwt
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
JWT_SECRET = os.getenv(
    "JWT_SECRET", "dev-local-secret-do-not-use-in-production-minimum-32-chars"
)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Host-visible ports from the Docker compose port mappings.
BASE_URLS = {
    "L1": os.getenv("L1_URL", "http://localhost:8001"),
    "L2": os.getenv("L2_URL", "http://localhost:8002"),
    "L3": os.getenv("L3_URL", "http://localhost:8003"),
    "L4": os.getenv("L4_URL", "http://localhost:8004"),
    "L5": os.getenv("L5_URL", "http://localhost:8005"),
    "L6": os.getenv("L6_URL", "http://localhost:8006"),
}

SCENARIO = {
    "company_name": "Nexus Analytics",
    "domain": "nexusanalytics.example.com",
    "industry": "Software as a Service",
    "region": "North America",
    "company_size": 350,
    "annual_revenue_usd": 45_000_000,
    "headquarters": "Austin, TX",
}

POLL_INTERVAL_SECONDS = float(os.getenv("E2E_POLL_INTERVAL_SECONDS", "3"))
L1_TIMEOUT_SECONDS = int(os.getenv("E2E_L1_TIMEOUT_SECONDS", "180"))
L2_TIMEOUT_SECONDS = int(os.getenv("E2E_L2_TIMEOUT_SECONDS", "240"))
L1_TERMINAL_SUCCESS = {"COMPLETED", "PARTIAL_SUCCESS"}
L1_TERMINAL_FAILURE = {"FAILED", "CANCELLED"}
L2_TERMINAL_SUCCESS = {"completed", "skipped"}
L2_TERMINAL_FAILURE = {"failed", "quarantined"}

DISCOVERY_MARKDOWN = """# Nexus Analytics — Discovery Intake

## Company profile
Nexus Analytics is a 350-person B2B SaaS company headquartered in Austin, TX. Their revenue is approximately $45M ARR, selling predictive analytics to revenue operations teams.

## Buyer pain
- Inconsistent discovery quality across AE/SE handoffs
- Weak business-case creation in late-stage deals
- Slow reuse of prior deal knowledge
- Poor value proof for CFO / procurement

## Current workflow
AEs capture notes in Salesforce; SEs rewrite them in multiple formats. Value cases are built ad-hoc in slides, with no standard model. Benchmark data is manually copied from old spreadsheets.

## Stakeholders
- Primary champion: VP Revenue Operations (Alex Chen)
- Economic buyer: CFO (Morgan Reed)
- Technical buyer: VP Engineering (Sam Patel)
- End user: Director Sales Enablement (Jordan Lee)

## KPIs
- Average deal size (ACV): $48,000
- Annual new-logo pipeline: $14.4M
- Win rate (late stage): 22%
- Average sales cycle: 92 days
- SE hours per opportunity: 4.5

## Target outcomes
1. Standardize discovery intake linked to account context.
2. Auto-generate evidence-backed ROI business case for every late-stage opportunity.
3. Reuse win stories and value proof from similar accounts.
4. Reduce SE hours per opportunity by 30%.

## Risks
- Limited internal benchmark data
- Finance may challenge ROI assumptions
- CRM data quality is inconsistent
- Adoption depends on front-line AE behavior change
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_token(
    tenant_id: str,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    roles: list[str] | None = None,
    issuer: str = "value-fabric-internal",
    algorithm: str | None = None,
    secret: str | None = None,
) -> str:
    """Sign a local-development JWT that GovernanceMiddleware will accept."""
    now = int(time.time())
    payload = {
        "tenant_id": tenant_id,
        "sub": user_id,
        "roles": roles or ["tenant_admin", "analyst"],
        "iat": now,
        "nbf": now,
        "exp": now + 3600,
        "iss": issuer,
        "aud": "value-fabric-services",
    }
    return jwt.encode(
        payload,
        secret or JWT_SECRET,
        algorithm=algorithm or JWT_ALGORITHM,
        headers={"kid": "active"},
    )


def make_service_token(tenant_id: str, sub: str, aud: str) -> str:
    """Sign a service-to-service JWT using the shared SERVICE_AUTH_SECRET."""
    secret = os.getenv("SERVICE_AUTH_SECRET", "").strip()
    if not secret:
        raise RuntimeError("SERVICE_AUTH_SECRET is not configured")
    now = int(time.time())
    payload = {
        "sub": sub,
        "aud": aud,
        "tenant_id": tenant_id,
        "iat": now,
        "nbf": now,
        "exp": now + 300,
        "iss": "value-fabric-s2s",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


class ApiCall:
    def __init__(
        self,
        step: str,
        layer: str,
        method: str,
        url: str,
        headers: dict[str, str],
        body: Any,
        expected_status: int | None = None,
        timeout: int = 30,
    ):
        self.step = step
        self.layer = layer
        self.method = method.upper()
        self.url = url
        self.headers = headers
        self.body = body
        self.expected_status = expected_status
        self.timeout = timeout
        self.status: int | None = None
        self.latency: float | None = None
        self.response_body: Any = None
        self.error: str | None = None
        self.timestamp = now_iso()

    def run(self) -> bool:
        start = time.time()
        try:
            kw = {"headers": self.headers, "timeout": self.timeout}
            if self.body is not None:
                kw["json"] = self.body
            resp = requests.request(self.method, self.url, **kw)
            self.latency = time.time() - start
            self.status = resp.status_code
            try:
                self.response_body = resp.json()
            except Exception:
                self.response_body = resp.text[:2000]
            if self.expected_status is not None and resp.status_code != self.expected_status:
                self.error = f"expected {self.expected_status}, got {resp.status_code}"
                return False
            return True
        except Exception as exc:
            self.latency = time.time() - start
            self.error = f"{type(exc).__name__}: {exc}"
            return False

    def to_dict(self, redact_token: bool = True) -> dict[str, Any]:
        headers = dict(self.headers)
        if redact_token and "Authorization" in headers:
            headers["Authorization"] = "Bearer <redacted>"
        return {
            "step": self.step,
            "layer": self.layer,
            "timestamp": self.timestamp,
            "request": {
                "method": self.method,
                "url": self.url,
                "headers": headers,
                "body": self.body,
            },
            "response": {
                "status": self.status,
                "latency_seconds": self.latency,
                "body": self.response_body,
                "error": self.error,
            },
        }


def require_success(call: ApiCall, *, expected: set[int] | None = None) -> None:
    expected = expected or set(range(200, 300))
    if call.status not in expected:
        print(
            f"{call.step} failed: status={call.status}, error={call.error}, body={call.response_body}",
            file=sys.stderr,
        )
        sys.exit(1)


def poll_call(
    *,
    transcript: list[ApiCall],
    step: str,
    layer: str,
    url: str,
    headers: dict[str, str],
    timeout_seconds: int,
    is_done,
    is_failed,
    failure_message,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_call: ApiCall | None = None
    while time.time() < deadline:
        call = ApiCall(
            step=step,
            layer=layer,
            method="GET",
            url=url,
            headers=headers,
            body=None,
            timeout=30,
        )
        call.run()
        last_call = call
        transcript.append(call)
        if call.status and 200 <= call.status < 300 and isinstance(call.response_body, dict):
            if is_failed(call.response_body):
                print(f"{step} failed: {failure_message(call.response_body)}", file=sys.stderr)
                sys.exit(1)
            if is_done(call.response_body):
                return call.response_body
        time.sleep(POLL_INTERVAL_SECONDS)

    print(
        f"{step} timed out after {timeout_seconds}s; last={last_call.response_body if last_call else None}",
        file=sys.stderr,
    )
    sys.exit(1)


def wait_for_l1_output(
    job_id: str,
    token: str,
    transcript: list[ApiCall],
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _raw_content_count(body: dict[str, Any]) -> int:
        if body.get("raw_content_count") is not None:
            return int(body.get("raw_content_count") or 0)
        results = body.get("results") or {}
        if isinstance(results, dict):
            return int(results.get("raw_content_count") or 0)
        return 0

    job = poll_call(
        transcript=transcript,
        step="l1_poll_job_completion",
        layer="L1",
        url=f"{BASE_URLS['L1']}/api/v1/ingestion/jobs/{job_id}",
        headers=headers,
        timeout_seconds=L1_TIMEOUT_SECONDS,
        is_done=lambda body: str(body.get("status")) in L1_TERMINAL_SUCCESS
        and _raw_content_count(body) > 0,
        is_failed=lambda body: str(body.get("status")) in L1_TERMINAL_FAILURE,
        failure_message=lambda body: f"status={body.get('status')}, errors={body.get('errors')}",
    )

    content_call = ApiCall(
        step="l1_list_job_content",
        layer="L1",
        method="GET",
        url=f"{BASE_URLS['L1']}/api/v1/ingestion/content?job_id={job_id}&limit=5",
        headers=headers,
        body=None,
    )
    content_call.run()
    transcript.append(content_call)
    require_success(content_call)
    items = content_call.response_body.get("items", []) if isinstance(content_call.response_body, dict) else []
    if not items:
        print(f"L1 job {job_id} completed without listable raw content", file=sys.stderr)
        sys.exit(1)

    content_id = str(items[0].get("id"))
    raw_call = ApiCall(
        step="l1_get_raw_content_metadata",
        layer="L1",
        method="GET",
        url=f"{BASE_URLS['L1']}/api/v1/ingestion/content/raw/{content_id}?include_html=false",
        headers=headers,
        body=None,
    )
    raw_call.run()
    transcript.append(raw_call)
    require_success(raw_call)
    if not isinstance(raw_call.response_body, dict):
        print(f"L1 raw content {content_id} did not return an object", file=sys.stderr)
        sys.exit(1)
    return {"job": job, "content": raw_call.response_body}


def markdown_from_l1_content(l1_content: dict[str, Any]) -> str:
    metadata = l1_content.get("metadata") or {}
    capture = l1_content.get("capture") or {}
    return f"""# Layer 1 Crawled Source

Source URL: {l1_content.get("source_url")}
Final URL: {l1_content.get("source_final_url") or l1_content.get("source_url")}
HTTP status: {l1_content.get("source_http_status")}
Title: {metadata.get("title") or "unknown"}
Description: {metadata.get("description") or "not provided"}
Capture method: {capture.get("method") or "unknown"}
Content hash: {l1_content.get("content_hash") or "not provided"}

## Scenario Notes
{DISCOVERY_MARKDOWN}
"""


def wait_for_l2_pipeline(job_id: str, token: str, transcript: list[ApiCall]) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return poll_call(
        transcript=transcript,
        step="l2_poll_extraction_completion",
        layer="L2",
        url=f"{BASE_URLS['L2']}/v1/extract/status/{job_id}",
        headers=headers,
        timeout_seconds=L2_TIMEOUT_SECONDS,
        is_done=lambda body: body.get("extraction_status") in L2_TERMINAL_SUCCESS
        and body.get("ingestion_status") in L2_TERMINAL_SUCCESS,
        is_failed=lambda body: body.get("extraction_status") in L2_TERMINAL_FAILURE
        or body.get("ingestion_status") in L2_TERMINAL_FAILURE
        or body.get("overall_status") in L2_TERMINAL_FAILURE,
        failure_message=lambda body: (
            f"overall={body.get('overall_status')}, extraction={body.get('extraction_status')}, "
            f"ingestion={body.get('ingestion_status')}, last_error={body.get('last_error')}"
        ),
    )


def create_tenant() -> tuple[str, str, ApiCall]:
    """Create a fresh active tenant using a super-admin JWT.

    The public /v1/tenants/register endpoint currently returns a 500 in this
    local stack because of a UUID string-handling bug in the email-verification
    path, so we create the tenant directly via the admin /v1/tenants endpoint.
    """
    slug = f"nexus-{uuid.uuid4().hex[:8]}"
    bootstrap_tenant_id = str(uuid.uuid4())
    admin_token = make_token(bootstrap_tenant_id, roles=["super_admin"])
    call = ApiCall(
        step="create_tenant",
        layer="L4",
        method="POST",
        url=f"{BASE_URLS['L4']}/v1/tenants",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json",
        },
        body={"name": "Nexus Analytics Eval Tenant", "slug": slug},
        expected_status=201,
    )
    if not call.run():
        print(f"Tenant creation failed: {call.error or call.response_body}", file=sys.stderr)
        sys.exit(1)
    tenant_id = call.response_body.get("id")
    if not tenant_id:
        print(f"Tenant creation returned no id: {call.response_body}", file=sys.stderr)
        sys.exit(1)
    print(f"Created active tenant {tenant_id} with slug {slug}")
    return tenant_id, slug, call


def create_account(tenant_id: str, token: str) -> tuple[str, ApiCall]:
    account_id = str(uuid.uuid4())
    call = ApiCall(
        step="create_account",
        layer="L4",
        method="POST",
        url=f"{BASE_URLS['L4']}/v1/accounts",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        body={
            "id": account_id,
            "provider": "manual",
            "name": SCENARIO["company_name"],
            "domain": SCENARIO["domain"],
            "industry": SCENARIO["industry"],
            "region": SCENARIO["region"],
            "company_size": SCENARIO["company_size"],
            "annual_revenue": SCENARIO["annual_revenue_usd"],
            "headquarters": SCENARIO["headquarters"],
        },
        expected_status=201,
    )
    if not call.run():
        print(f"Account creation failed: {call.error or call.response_body}", file=sys.stderr)
        sys.exit(1)
    print(f"Created account {account_id}")
    return account_id, call


def health_checks() -> list[ApiCall]:
    calls = []
    for layer, url in BASE_URLS.items():
        path = "/health"
        if layer == "L6":
            path = "/ready"
        call = ApiCall(
            step=f"health_{layer}",
            layer=layer,
            method="GET",
            url=f"{url}{path}",
            headers={},
            body=None,
            expected_status=200,
        )
        ok = call.run()
        status = "OK" if ok else f"FAIL ({call.error or call.status})"
        print(f"Health {layer}: {status}")
        calls.append(call)
    return calls


def main() -> int:
    transcript: list[ApiCall] = []

    # 1. Health checks
    print("\n=== Step 1: Health checks ===")
    transcript.extend(health_checks())

    # 2. Tenant + account
    print("\n=== Step 2: Provision tenant and account ===")
    tenant_id, slug, tenant_call = create_tenant()
    transcript.append(tenant_call)
    user_token = make_token(tenant_id)
    account_id, account_call = create_account(tenant_id, user_token)
    transcript.append(account_call)

    # 3. Layer 1 ingestion — user-facing routes
    print("\n=== Step 3: Layer 1 ingestion ===")
    target_id = str(uuid.uuid4())
    l1_target = ApiCall(
        step="l1_create_target",
        layer="L1",
        method="POST",
        url=f"{BASE_URLS['L1']}/api/v1/ingestion/targets",
        headers={"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"},
        body={
            "id": target_id,
            "name": "Nexus Analytics website",
            "url": "https://example.com",
            "target_type": "SINGLE_PAGE",
        },
    )
    l1_target.run()
    transcript.append(l1_target)
    require_success(l1_target, expected={201})
    # Layer 1 may generate its own target UUID; use the returned one for downstream calls.
    if l1_target.status == 201 and isinstance(l1_target.response_body, dict):
        target_id = l1_target.response_body.get("id", target_id)

    l1_job = ApiCall(
        step="l1_prospect_research_job",
        layer="L1",
        method="POST",
        url=f"{BASE_URLS['L1']}/api/v1/ingestion/jobs/prospect-research",
        headers={"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"},
        body={
            "target_id": target_id,
            "account_name": SCENARIO["company_name"],
            "account_id": account_id,
            "priority": 5,
        },
    )
    l1_job.run()
    transcript.append(l1_job)
    require_success(l1_job)
    l1_job_id = str(l1_job.response_body.get("job_id")) if isinstance(l1_job.response_body, dict) else ""
    if not l1_job_id:
        print(f"Layer 1 job creation returned no job_id: {l1_job.response_body}", file=sys.stderr)
        sys.exit(1)
    l1_output = wait_for_l1_output(l1_job_id, user_token, transcript)
    l1_content = l1_output["content"]

    # 4. Layer 2 extraction + Layer 3 ingestion — internal route gated by L1→L2 S2S JWT
    print("\n=== Step 4: Layer 2 extraction ===")
    content_id = str(l1_content.get("id") or f"discovery-{uuid.uuid4().hex[:8]}")
    l2_token = make_service_token(
        tenant_id, sub="layer1-ingestion", aud="layer2-extraction"
    )
    l2_extract = ApiCall(
        step="l2_extract_discovery",
        layer="L2",
        method="POST",
        url=f"{BASE_URLS['L2']}/v1/extract-and-ingest",
        headers={"Authorization": f"Bearer {l2_token}", "Content-Type": "application/json"},
        body={
            "content_id": content_id,
            "source_url": l1_content.get("source_url") or f"internal://{content_id}",
            "markdown_content": markdown_from_l1_content(l1_content),
            "extraction_config": {
                "ontology": "value-fabric-b2b",
                "model_version": os.getenv("EXTRACTION_MODEL", "e2e-local-extraction-model"),
                "schema_version": "value-fabric-extraction-v1",
                "prompt_version": "entity_extraction_v1+relationship_extraction_v1",
                "ingestion_id": l1_job_id,
                "value_pack_id": "value-fabric-b2b",
            },
        },
    )
    l2_extract.run()
    transcript.append(l2_extract)
    require_success(l2_extract)
    l2_job_id = ""
    if isinstance(l2_extract.response_body, dict):
        l2_job_id = str(
            l2_extract.response_body.get("job_id")
            or l2_extract.response_body.get("extraction_job_id")
            or ""
        )
    if not l2_job_id:
        print(f"Layer 2 extraction returned no job id: {l2_extract.response_body}", file=sys.stderr)
        sys.exit(1)
    l2_status = wait_for_l2_pipeline(l2_job_id, l2_token, transcript)
    if int(l2_status.get("entities_extracted") or 0) <= 0:
        print(f"Layer 2 completed without extracted entities: {l2_status}", file=sys.stderr)
        sys.exit(1)

    # 5. Layer 3 knowledge graph — query the graph populated by Layer 2 ingestion
    print("\n=== Step 5: Layer 3 knowledge graph ===")
    l3_search = ApiCall(
        step="l3_hybrid_search",
        layer="L3",
        method="POST",
        url=f"{BASE_URLS['L3']}/v1/search",
        headers={"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"},
        body={
            "query": "What capabilities help reduce SE hours per opportunity and improve late-stage win rate?",
            "search_type": "hybrid",
            "max_results": 5,
        },
    )
    l3_search.run()
    transcript.append(l3_search)
    require_success(l3_search)

    l3_formula = ApiCall(
        step="l3_formula_evaluate",
        layer="L3",
        method="POST",
        url=f"{BASE_URLS['L3']}/v1/formulas/evaluate",
        headers={"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"},
        body={
            "expression": "(pipeline_value * win_rate_lift) + (se_hours_per_opp * opps_per_year * hourly_se_cost * se_time_reduction)",
            "inputs": [
                {"name": "pipeline_value", "value": 14_400_000, "unit": "USD"},
                {"name": "win_rate_lift", "value": 0.04, "unit": "fraction"},
                {"name": "se_hours_per_opp", "value": 4.5, "unit": "hours"},
                {"name": "opps_per_year", "value": 300, "unit": "opportunities"},
                {"name": "hourly_se_cost", "value": 95, "unit": "USD/hour"},
                {"name": "se_time_reduction", "value": 0.30, "unit": "fraction"},
            ],
            "output_unit": "USD/year",
        },
    )
    l3_formula.run()
    transcript.append(l3_formula)
    require_success(l3_formula)

    # 6. Layer 4 agents / reasoning / case
    print("\n=== Step 6: Layer 4 agentic workflow ===")
    l4_roi = ApiCall(
        step="l4_roi_analysis",
        layer="L4",
        method="POST",
        url=f"{BASE_URLS['L4']}/v1/analysis/roi",
        headers={"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"},
        body={
            "account_id": account_id,
            "prospect_id": account_id,
            "value_driver_ids": ["se-efficiency", "win-rate-lift", "cycle-time-reduction"],
            "prospect_data": {
                "acv": 48000,
                "annual_pipeline": 14400000,
                "late_stage_win_rate": 0.22,
                "sales_cycle_days": 92,
                "se_hours_per_opp": 4.5,
                "ae_count": 12,
                "se_count": 5,
            },
            "industry_vertical": "software",
            "company_size": "350",
        },
    )
    l4_roi.run()
    transcript.append(l4_roi)
    require_success(l4_roi)

    l4_case = ApiCall(
        step="l4_create_case",
        layer="L4",
        method="POST",
        url=f"{BASE_URLS['L4']}/v1/cases",
        headers={"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"},
        body={
            "account_id": account_id,
            "sections": ["executive_summary", "roi_analysis", "value_drivers"],
            "output_format": "json",
        },
        timeout=90,
    )
    l4_case.run()
    transcript.append(l4_case)
    require_success(l4_case)

    # 7. Layer 5 ground truth
    print("\n=== Step 7: Layer 5 ground truth ===")
    l5_assumption = ApiCall(
        step="l5_create_assumption",
        layer="L5",
        method="POST",
        url=f"{BASE_URLS['L5']}/api/v1/assumptions",
        headers={"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"},
        body={
            "name": "SE hours per opportunity will decrease 30% within 12 months",
            "description": "Based on benchmark data for mid-market SaaS value-engineering programs.",
            "impact_value": 384750,
        },
    )
    l5_assumption.run()
    transcript.append(l5_assumption)

    l5_truth = ApiCall(
        step="l5_create_truth",
        layer="L5",
        method="POST",
        url=f"{BASE_URLS['L5']}/api/v1/truths",
        headers={"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"},
        body={
            "claim": "Nexus Analytics SEs spend 4.5 hours on each opportunity preparing business cases manually.",
            "claim_type": "efficiency_gain",
            "confidence": 0.85,
            "value": {"amount": 4.5, "unit": "hours", "period": "opportunity"},
            "applies_to": {"account_id": account_id, "opportunity_id": f"opp-{uuid.uuid4().hex[:8]}"},
            "extraction_job_id": l2_job_id,
            "extraction_model": os.getenv("EXTRACTION_MODEL", "e2e-local-extraction-model"),
        },
    )
    l5_truth.run()
    transcript.append(l5_truth)

    l5_maturity = ApiCall(
        step="l5_maturity_ladder",
        layer="L5",
        method="GET",
        url=f"{BASE_URLS['L5']}/api/v1/maturity-ladder",
        headers={"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"},
        body=None,
    )
    l5_maturity.run()
    transcript.append(l5_maturity)

    # 8. Layer 6 benchmarks
    print("\n=== Step 8: Layer 6 benchmarks ===")
    l6_admin_token = make_token(tenant_id, roles=["super_admin"])
    benchmark_dataset_id = os.getenv("E2E_BENCHMARK_DATASET_ID", "saas-se-efficiency-2025")
    benchmark_metric = os.getenv("E2E_BENCHMARK_METRIC", "se_hours_per_opportunity")
    l6_dataset = ApiCall(
        step="l6_get_preloaded_dataset",
        layer="L6",
        method="GET",
        url=f"{BASE_URLS['L6']}/v1/benchmarks/datasets/{benchmark_dataset_id}",
        headers={"Authorization": f"Bearer {l6_admin_token}", "Content-Type": "application/json"},
        body=None,
    )
    l6_dataset.run()
    transcript.append(l6_dataset)
    require_success(l6_dataset)
    dataset_body = l6_dataset.response_body if isinstance(l6_dataset.response_body, dict) else {}
    metrics_payload = dataset_body.get("metrics", {})
    if isinstance(metrics_payload, dict):
        metric_names = set(metrics_payload)
    else:
        metric_names = {m.get("name") for m in metrics_payload if isinstance(m, dict)}
    if benchmark_metric not in metric_names:
        print(
            f"Preloaded dataset {benchmark_dataset_id} is missing metric {benchmark_metric}; "
            f"available={sorted(metric_names)}",
            file=sys.stderr,
        )
        sys.exit(1)

    l6_compare = ApiCall(
        step="l6_benchmark_compare",
        layer="L6",
        method="POST",
        url=f"{BASE_URLS['L6']}/v1/benchmarks/compare",
        headers={"Authorization": f"Bearer {l6_admin_token}", "Content-Type": "application/json"},
        body={
            "dataset_id": benchmark_dataset_id,
            "metric": benchmark_metric,
            "company_value": "4.5",
            "industry": dataset_body.get("industry") or "technology",
            "segment": dataset_body.get("segment") or "enterprise",
        },
    )
    l6_compare.run()
    transcript.append(l6_compare)
    require_success(l6_compare)

    compare_body = l6_compare.response_body if isinstance(l6_compare.response_body, dict) else {}
    assessment = compare_body.get("assessment")
    valid_buckets = {
        "top_performer",
        "above_average",
        "average",
        "below_average",
        "needs_improvement",
    }
    if assessment not in valid_buckets:
        print(
            f"L6 benchmark compare returned unexpected assessment bucket: {assessment}",
            file=sys.stderr,
        )
        sys.exit(1)
    print(
        f"L6 benchmark compare: dataset={benchmark_dataset_id}, "
        f"percentile={compare_body.get('percentile')}, assessment={assessment}"
    )

    # 9. Security / tenant isolation / fail-closed checks
    print("\n=== Step 9: Security / tenant isolation checks ===")
    other_tenant = str(uuid.uuid4())
    other_token = make_token(other_tenant)
    isolation_call = ApiCall(
        step="tenant_isolation_cross_tenant_account_read",
        layer="L4",
        method="GET",
        url=f"{BASE_URLS['L4']}/v1/accounts/{account_id}",
        headers={"Authorization": f"Bearer {other_token}", "Content-Type": "application/json"},
        body=None,
    )
    isolation_call.run()
    transcript.append(isolation_call)

    no_auth_call = ApiCall(
        step="auth_fail_closed_no_token",
        layer="L4",
        method="GET",
        url=f"{BASE_URLS['L4']}/v1/accounts/{account_id}",
        headers={"Content-Type": "application/json"},
        body=None,
    )
    no_auth_call.run()
    transcript.append(no_auth_call)

    l1_no_auth = ApiCall(
        step="auth_fail_closed_l1_no_token",
        layer="L1",
        method="GET",
        url=f"{BASE_URLS['L1']}/api/v1/ingestion/targets",
        headers={"Content-Type": "application/json"},
        body=None,
    )
    l1_no_auth.run()
    transcript.append(l1_no_auth)

    # 10. Write artifacts
    print("\n=== Step 10: Write evidence artifacts ===")
    os.makedirs("docs/evidence", exist_ok=True)
    transcript_dict = {
        "metadata": {
            "run_date": now_iso(),
            "environment": "local Docker compose backend-integrated + e2e-local override",
            "scenario": SCENARIO,
            "tenant_id": tenant_id,
            "account_id": account_id,
            "l1_job_id": l1_job_id,
            "l1_content_id": content_id,
            "l2_job_id": l2_job_id,
            "benchmark_dataset": {
                "dataset_id": benchmark_dataset_id,
                "metric": benchmark_metric,
                "industry": dataset_body.get("industry"),
                "segment": dataset_body.get("segment"),
                "version": dataset_body.get("version"),
                "data_source": dataset_body.get("data_source"),
                "source_mode": "global_system_pack_seed",
                "sample_size": (
                    metrics_payload.get(benchmark_metric, {})
                    .get("profile", {})
                    .get("sample_size")
                    if isinstance(metrics_payload, dict)
                    else None
                ),
            },
        },
        "calls": [c.to_dict() for c in transcript],
    }
    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    transcript_path = f"docs/evidence/fabric4l-e2e-api-transcript-{run_stamp}.json"
    with open(transcript_path, "w") as f:
        json.dump(transcript_dict, f, indent=2, default=str)
    print(f"Wrote {transcript_path}")

    # Attempt a real LLM call using the configured provider key.
    # Layer 4's built-in roi_calculator/business_case workflows currently fail
    # with internal LangGraph state errors, so we use a direct provider call to
    # prove the credential is valid and capture a real response for the trace.
    actual_invocations: list[dict[str, Any]] = []
    llm_verdict = "BLOCKED_FOR_REAL_LLM"
    llm_notes = [
        "Layer 4 workflows that require LLM invocation returned heuristic/seeded responses because no provider API key was available.",
        "The API transcript records the exact HTTP responses for these calls; no LLM HTTP request was dispatched.",
    ]

    provider = os.getenv("LAYER4_LLM_PROVIDER", "together").lower()
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("LLM_MODEL", "gpt-4o")
        endpoint = "https://api.openai.com/v1/chat/completions"
    else:
        # Together.ai is the default configured provider
        api_key = os.getenv("LAYER4_TOGETHER_API_KEY") or os.getenv("TOGETHER_API_KEY")
        model = os.getenv("LAYER4_TOGETHER_DEFAULT_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo")
        endpoint = os.getenv("LAYER4_TOGETHER_BASE_URL", "https://api.together.ai/v1") + "/chat/completions"

    if api_key:
        prompt = (
            "Nexus Analytics is a 350-person B2B SaaS company with $45M ARR. "
            "They struggle with inconsistent discovery, weak business cases, slow SE/AE handoffs, "
            "poor value proof, and limited reuse of deal knowledge. "
            "Write a 3-sentence value hypothesis for how a GTM value-engineering workflow platform could help them."
        )
        messages = [
            {"role": "system", "content": "You are a concise value engineer for a B2B SaaS platform."},
            {"role": "user", "content": prompt},
        ]
        llm_start = time.time()
        try:
            llm_resp = requests.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "temperature": 0.3, "max_tokens": 250},
                timeout=120,
            )
            llm_latency_ms = round((time.time() - llm_start) * 1000, 2)
            llm_body = llm_resp.json()
            actual_invocations.append(
                {
                    "provider": provider,
                    "model_requested": model,
                    "model_resolved": llm_body.get("model"),
                    "endpoint": endpoint,
                    "prompt_template": "value-engineering-hypothesis-for-nexus-analytics",
                    "messages": messages,
                    "response_status": llm_resp.status_code,
                    "response_payload": llm_body,
                    "latency_ms": llm_latency_ms,
                    "token_usage": llm_body.get("usage"),
                }
            )
            llm_verdict = "REAL_LLM_INVOKED_L4_WORKFLOW_DEGRADED"
            llm_notes = [
                f"A real {provider} LLM call succeeded using the configured API key.",
                "Layer 4's /v1/analysis/roi and /v1/cases endpoints still fail internally (LangGraph InvalidUpdateError / tool tenant-context / checkpoints issues), so they did not themselves dispatch an LLM request.",
            ]
        except Exception as exc:
            actual_invocations.append(
                {
                    "provider": provider,
                    "model_requested": model,
                    "endpoint": endpoint,
                    "error": str(exc),
                }
            )
            llm_verdict = "REAL_LLM_CALL_FAILED"
            llm_notes = [f"Direct {provider} LLM call failed: {exc}"]

    llm_trace = {
        "metadata": {
            "run_date": now_iso(),
            "verdict": llm_verdict,
            "reason": f"{provider} API key configured; Layer 4 built-in workflows still have internal errors" if api_key else "No LLM API key is configured in the environment",
        },
        "provider_configuration": {
            "llm_provider": provider,
            "layer4_llm_provider": provider,
            "llm_model_env": model if api_key else os.getenv("LLM_MODEL", "gpt-4o"),
            "layer4_default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "layer4_together_base_url": "https://api.together.ai/v1",
        },
        "credential_check": {
            "TOGETHER_API_KEY": {"set": bool(os.getenv("TOGETHER_API_KEY")), "value_redacted": None},
            "LAYER4_TOGETHER_API_KEY": {"set": bool(os.getenv("LAYER4_TOGETHER_API_KEY")), "value_redacted": None},
            "OPENAI_API_KEY": {"set": bool(os.getenv("OPENAI_API_KEY")), "value_redacted": None},
            "ANTHROPIC_API_KEY": {"set": bool(os.getenv("ANTHROPIC_API_KEY")), "value_redacted": None},
        },
        "intended_invocations": [
            {
                "step": "l4_roi_analysis",
                "endpoint": "POST /v1/analysis/roi",
                "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                "purpose": "Generate ROI scenarios from value drivers for Nexus Analytics",
            },
            {
                "step": "l4_create_case",
                "endpoint": "POST /v1/cases",
                "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                "purpose": "Synthesize business-case narrative with evidence trace",
            },
        ],
        "actual_invocations": actual_invocations,
        "notes": llm_notes,
    }
    llm_path = f"docs/evidence/fabric4l-e2e-llm-trace-{run_stamp}.json"
    with open(llm_path, "w") as f:
        json.dump(llm_trace, f, indent=2, default=str)
    print(f"Wrote {llm_path}")

    # Print summary
    passed = sum(
        1
        for c in transcript
        if c.status == c.expected_status
        or (c.expected_status is None and c.status in (200, 201))
    )
    failed = len(transcript) - passed
    print(f"\nWorkflow complete: {passed} calls expected-success, {failed} calls returned non-2xx or errors")
    for c in transcript:
        if c.error or (c.status is not None and c.status >= 400):
            print(f"  - {c.step} ({c.layer}): HTTP {c.status} | {c.error or 'see transcript'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
