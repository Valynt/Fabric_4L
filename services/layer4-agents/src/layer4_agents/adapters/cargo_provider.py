import asyncio
import json
import os
import time
import uuid
from typing import Any
from uuid import UUID

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
import structlog

from value_fabric.shared.contracts.account_intelligence import (
    AccountIntelligenceProvider,
    AccountSignal,
    CompanyEnrichmentData,
    CompanyResolutionResult,
    EnrichedAccountContext,
    StakeholderProfile,
)
from layer4_agents.provenance.cargo_normalizer import CargoContextNormalizer


logger = structlog.get_logger()


class CargoAPIError(Exception):
    """Raised when the Cargo HTTP API fails."""
    pass


class CargoAccountIntelligenceProvider(AccountIntelligenceProvider):
    """
    Retrieves and normalizes account intelligence via Cargo.
    Migrated from CLI subprocesses to direct HTTP calls for production resiliency.
    """

    # Cargo Action/Tool UUIDs
    TOOL_ENRICH_COMPANY = "a896f1d8-d289-4cca-af2f-bc8f7c1bf78f"
    TOOL_FIND_STAKEHOLDERS = "863912f9-9ff5-4e9b-8b18-862fb91cdc67"
    TOOL_FIND_COMPETITORS = "f5557dfb-c342-40aa-b3d0-f5a194fcea57"
    
    BASE_URL = "https://api.getcargo.io/v1"

    def __init__(self, api_key: str | None = None, enable_mock_fallback: bool = False):
        self._api_key = api_key or os.environ.get("CARGO_API_KEY")
        self._enable_mock_fallback = enable_mock_fallback
        
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            } if self._api_key else {}
        )

        self.metrics = {
            "requests_total": 0,
            "errors_total": 0,
            "last_latency_ms": 0.0,
        }

    @property
    def provider_name(self) -> str:
        return "cargo"

    async def close(self) -> None:
        await self._client.aclose()

    async def _execute_tool_action_http(self, tool_uuid: str, data_payload: dict[str, Any]) -> dict[str, Any] | None:
        """
        Executes a Cargo tool action via HTTP API with exponential backoff.
        Polls for completion if execution is async.
        """
        if not self._api_key:
            logger.warning("cargo_api_key_missing_skipping_execution")
            return None

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((httpx.RequestError, CargoAPIError)),
            reraise=True
        ):
            with attempt:
                try:
                    payload = {
                        "action": json.dumps({"kind": "tool", "toolUuid": tool_uuid, "config": {}}),
                        "data": json.dumps(data_payload)
                    }
                    
                    response = await self._client.post("/orchestration/actions/execute", json=payload)
                    response.raise_for_status()
                    
                    run_data = response.json()
                    
                    # Sometimes the API returns synchronous responses
                    if "runContext" in run_data:
                        return run_data["runContext"].get("action")
                        
                    run_uuid = run_data.get("run", {}).get("uuid")
                    if not run_uuid:
                        raise CargoAPIError("Missing run UUID in response")

                    for _ in range(20):
                        await asyncio.sleep(2)
                        poll_resp = await self._client.get(f"/orchestration/runs/{run_uuid}")
                        poll_resp.raise_for_status()
                        poll_data = poll_resp.json()
                        status = poll_data.get("run", {}).get("status")
                        
                        if status == "success":
                            return poll_data.get("runContext", {}).get("action")
                        elif status == "failed":
                            raise CargoAPIError(f"Cargo run failed: {run_uuid}")
                    
                    raise CargoAPIError(f"Timeout waiting for Cargo run {run_uuid}")

                except httpx.HTTPStatusError as e:
                    if e.response.status_code in (429, 502, 503, 504):
                        logger.warning("cargo_api_transient_error", status=e.response.status_code)
                        raise CargoAPIError(f"Transient HTTP error {e.response.status_code}")
                    self.metrics["errors_total"] += 1
                    logger.error("cargo_api_terminal_error", status=e.response.status_code, response=e.response.text)
                    return None
                except Exception as e:
                    self.metrics["errors_total"] += 1
                    logger.error("cargo_api_execution_failed", error=str(e))
                    raise CargoAPIError(f"Execution failed: {str(e)}")
        
        return None

    async def resolve_company(self, name: str, domain: str | None = None, tenant_id: UUID | None = None) -> CompanyResolutionResult | None:
        """Resolve generic name/domain to Cargo's canonical representation."""
        if not domain:
            return None
        
        start_time = time.perf_counter()
        self.metrics["requests_total"] += 1
        log = logger.bind(provider="cargo", action="resolve_company", domain=domain)

        out = await self._execute_tool_action_http(
            self.TOOL_ENRICH_COMPANY,
            {"companyDomain": domain}
        )
        
        self.metrics["last_latency_ms"] = (time.perf_counter() - start_time) * 1000

        if out and "name" in out:
            log.info("cargo_resolve_company_live_success", latency_ms=self.metrics["last_latency_ms"])
            return CargoContextNormalizer.normalize_company_resolution(
                raw_data=out, fallback_name=name, fallback_domain=domain
            )
            
        return None

    async def enrich_company(
        self, domain: str, company_name: str | None = None, tenant_id: UUID | None = None
    ) -> CompanyEnrichmentData | None:
        """Enrich company firmographics and tech stack via Cargo."""
        start_time = time.perf_counter()
        self.metrics["requests_total"] += 2
        log = logger.bind(provider="cargo", action="enrich_company", domain=domain)

        enrich_task = asyncio.create_task(
            self._execute_tool_action_http(self.TOOL_ENRICH_COMPANY, {"companyDomain": domain})
        )
        comp_task = asyncio.create_task(
            self._execute_tool_action_http(self.TOOL_FIND_COMPETITORS, {"companyDomain": domain})
        )

        enrich_out, comp_out = await asyncio.gather(enrich_task, comp_task, return_exceptions=True)

        latency_ms = (time.perf_counter() - start_time) * 1000
        self.metrics["last_latency_ms"] = latency_ms

        competitors = []
        if isinstance(comp_out, dict) and "competitors" in comp_out:
            competitors = CargoContextNormalizer.normalize_competitors(comp_out["competitors"])

        if isinstance(enrich_out, dict) and "name" in enrich_out:
            log.info("cargo_enrich_company_live_success", latency_ms=latency_ms, competitors_count=len(competitors))
            return CargoContextNormalizer.normalize_company_enrichment(
                raw_data=enrich_out,
                domain=domain,
                company_name=company_name,
                competitors=competitors,
            )

        return None

    async def discover_stakeholders(
        self,
        domain: str,
        company_name: str | None = None,
        persona_keywords: list[str] | None = None,
        limit: int = 25,
        tenant_id: UUID | None = None,
    ) -> list[StakeholderProfile]:
        """Discover key leadership and buying personas via Cargo."""
        start_time = time.perf_counter()
        self.metrics["requests_total"] += 1
        log = logger.bind(provider="cargo", action="discover_stakeholders", domain=domain, limit=limit)

        titles_query = ", ".join(persona_keywords) if persona_keywords else "CFO, Chief Operating Officer, VP Operations, VP Engineering, VP Sales"

        stake_out = await self._execute_tool_action_http(
            self.TOOL_FIND_STAKEHOLDERS,
            {"companyDomain": domain, "titles": titles_query},
        )
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        self.metrics["last_latency_ms"] = latency_ms

        if stake_out and "stakeholders" in stake_out:
            raw_leads = stake_out["stakeholders"]
            log.info("cargo_stakeholders_live_success", count=len(raw_leads), latency_ms=latency_ms)
            return CargoContextNormalizer.normalize_stakeholders(raw_leads, domain=domain)

        return []

    async def get_company_signals(
        self,
        domain: str,
        company_name: str | None = None,
        tenant_id: UUID | None = None,
    ) -> list[AccountSignal]:
        """Acquire active buying signals and operational observations."""
        self.metrics["requests_total"] += 1
        return []

    async def get_full_account_context(
        self,
        domain: str,
        company_name: str,
        tenant_id: UUID,
        account_id: UUID | None = None,
    ) -> EnrichedAccountContext | None:
        """Assemble full normalized account context."""
        log = logger.bind(provider="cargo", action="get_full_account_context", domain=domain, tenant_id=str(tenant_id))
        log.info("cargo_assembling_full_context_started")

        enrichment_task = asyncio.create_task(self.enrich_company(domain, company_name, tenant_id))
        stakeholders_task = asyncio.create_task(self.discover_stakeholders(domain, company_name, tenant_id=tenant_id))
        signals_task = asyncio.create_task(self.get_company_signals(domain, company_name, tenant_id=tenant_id))

        company_data, stakeholders, signals = await asyncio.gather(
            enrichment_task,
            stakeholders_task,
            signals_task,
            return_exceptions=False,
        )

        if not company_data:
            log.warning("cargo_full_context_failed_no_company_data")
            return None

        # Just return basic Context since assemble_context was a mock-specific helper in tests perhaps? 
        # Actually CargoContextNormalizer doesn't have assemble_context natively, the test used it.
        # Let's construct it directly.
        return EnrichedAccountContext(
            account_id=account_id,
            tenant_id=tenant_id,
            company=company_data,
            stakeholders=stakeholders,
            signals=signals,
            raw_provider_record_id=company_data.provenance.provider_record_id,
        )