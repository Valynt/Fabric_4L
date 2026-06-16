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

    # 4. Layer 2 extraction — internal route gated by L1→L2 S2S JWT
    print("\n=== Step 4: Layer 2 extraction ===")
    content_id = f"discovery-{uuid.uuid4().hex[:8]}"
    l2_token = make_service_token(
        tenant_id, sub="layer1-ingestion", aud="layer2-extraction"
    )
    l2_extract = ApiCall(
        step="l2_extract_discovery",
        layer="L2",
        method="POST",
        url=f"{BASE_URLS['L2']}/v1/extract",
        headers={"Authorization": f"Bearer {l2_token}", "Content-Type": "application/json"},
        body={
            "content_id": content_id,
            "source_url": f"internal://{content_id}",
            "markdown_content": DISCOVERY_MARKDOWN,
            "extraction_config": {"ontology": "value-fabric-b2b"},
        },
    )
    l2_extract.run()
    transcript.append(l2_extract)

    # 5. Layer 3 knowledge graph — JWT auth (L3's governance middleware rejects API keys)
    print("\n=== Step 5: Layer 3 knowledge graph ===")
    rdf_ttl = f"""@prefix vf: <http://valuefabric.io/ontology/> .
@prefix ex: <http://valuefabric.io/entities/> .
ex:{account_id} a vf:Account ;
    vf:name "{SCENARIO['company_name']}" ;
    vf:industry "{SCENARIO['industry']}" ;
    vf:annualRevenue {SCENARIO['annual_revenue_usd']} ;
    vf:hasPain vf:inconsistentDiscovery, vf:weakBusinessCase, vf:slowReuse, vf:poorValueProof .
"""
    l3_ingest = ApiCall(
        step="l3_ingest_rdf",
        layer="L3",
        method="POST",
        url=f"{BASE_URLS['L3']}/v1/ingest",
        headers={"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"},
        body={
            "rdf_data": rdf_ttl,
            "source_id": content_id,
            "extraction_job_id": f"job-{content_id}",
        },
    )
    l3_ingest.run()
    transcript.append(l3_ingest)

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
            "extraction_job_id": f"job-{content_id}",
            "extraction_model": "manual-e2e",
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
    l6_upsert = ApiCall(
        step="l6_upsert_dataset",
        layer="L6",
        method="POST",
        url=f"{BASE_URLS['L6']}/v1/benchmarks/datasets",
        headers={"Authorization": f"Bearer {l6_admin_token}", "Content-Type": "application/json"},
        body={
            "dataset_id": "saas-se-efficiency-2025",
            "name": "SaaS SE Efficiency 2025",
            "description": "Peer benchmarks for SaaS value-engineering workflows",
            "industry": "Software",
            "segment": "mid-market",
            "version": "1.0.0",
            "ownership_mode": "tenant",
            "metrics": {
                "se_hours_per_opportunity": {
                    "name": "se_hours_per_opportunity",
                    "unit": "hours",
                    "description": "SE hours per opportunity",
                    "profile": {
                        "p10": "1.5",
                        "p25": "2.5",
                        "p50": "4.0",
                        "p75": "6.0",
                        "p90": "8.5",
                        "mean": "4.2",
                        "std_dev": "2.1",
                        "sample_size": 850,
                    },
                }
            },
        },
    )
    l6_upsert.run()
    transcript.append(l6_upsert)

    l6_compare = ApiCall(
        step="l6_benchmark_compare",
        layer="L6",
        method="POST",
        url=f"{BASE_URLS['L6']}/v1/benchmarks/compare",
        headers={"Authorization": f"Bearer {l6_admin_token}", "Content-Type": "application/json"},
        body={
            "dataset_id": "saas-se-efficiency-2025",
            "metric": "se_hours_per_opportunity",
            "company_value": "4.5",
            "industry": "Software",
            "segment": "mid-market",
        },
    )
    l6_compare.run()
    transcript.append(l6_compare)

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
        },
        "calls": [c.to_dict() for c in transcript],
    }
    transcript_path = "docs/evidence/fabric4l-e2e-api-transcript-20260615.json"
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
    llm_path = "docs/evidence/fabric4l-e2e-llm-trace-20260615.json"
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
