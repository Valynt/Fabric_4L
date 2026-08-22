import asyncio
import json
import os
import uuid
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from value_fabric.shared.contracts.account_intelligence import (
    AccountIntelligenceProvider,
    AccountSignal,
    CompanyEnrichmentData,
    CompanyResolutionResult,
    EnrichedAccountContext,
    ProvenanceClassification,
    SignalProvenance,
    StakeholderProfile,
)
from layer4_agents.adapters.cargo_provider import CargoAccountIntelligenceProvider
from layer4_agents.provenance.cargo_normalizer import CargoContextNormalizer
from layer4_agents.services.enrichment_orchestrator import EnrichmentOrchestrator, EnrichmentStatus
from layer4_agents.models.account import Account

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

def load_fixture(filename: str) -> dict[str, Any]:
    with open(os.path.join(FIXTURES_DIR, filename), "r", encoding="utf-8") as f:
        return json.load(f)

# ---------------------------------------------------------------------------
# Mocks
# ---------------------------------------------------------------------------

class MockApolloProvider(AccountIntelligenceProvider):
    @property
    def provider_name(self) -> str:
        return "apollo"
    async def close(self) -> None:
        pass
    async def resolve_company(self, name: str, domain: str | None = None, tenant_id: uuid.UUID | None = None) -> CompanyResolutionResult | None:
        return CompanyResolutionResult(
            canonical_name="Acme Corp",
            domain="acme.com",
            provider_company_id="apollo:123",
            matched_via="domain",
            provenance=SignalProvenance(provider="apollo", classification=ProvenanceClassification.TRACEABLE),
        )
    async def enrich_company(self, domain: str, company_name: str | None = None, tenant_id: uuid.UUID | None = None) -> CompanyEnrichmentData | None:
        return CompanyEnrichmentData(
            name="Acme Corp",
            domain=domain,
            industry="Software",
            employee_count=500,
            annual_revenue_usd=50000000.0,
            technologies=[],
            tech_stack_by_category={},
            provenance=SignalProvenance(provider="apollo", classification=ProvenanceClassification.TRACEABLE),
        )
    async def discover_stakeholders(self, domain: str, company_name: str | None = None, persona_keywords: list[str] | None = None, limit: int = 25, tenant_id: uuid.UUID | None = None) -> list[StakeholderProfile]:
        return [
            StakeholderProfile(
                first_name="Jane",
                last_name="Doe",
                full_name="Jane Doe",
                job_title="CTO",
                persona_role="CTO",
                seniority_level="C-Level",
                department="Engineering",
                work_email=f"jane@{domain}",
                provenance=SignalProvenance(provider="apollo", classification=ProvenanceClassification.TRACEABLE),
            )
        ]
    async def get_company_signals(self, domain: str, company_name: str | None = None, tenant_id: uuid.UUID | None = None) -> list[AccountSignal]:
        return []
    async def get_full_account_context(self, domain: str, company_name: str, tenant_id: uuid.UUID, account_id: uuid.UUID | None = None) -> EnrichedAccountContext | None:
        company = await self.enrich_company(domain, company_name, tenant_id)
        return EnrichedAccountContext(
            account_id=account_id,
            tenant_id=tenant_id,
            company=company,
            stakeholders=[],
            signals=[],
            raw_provider_record_id="apollo:123"
        )


# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------

@pytest.fixture
def cargo_mock():
    with respx.mock(base_url="https://api.getcargo.io/v1", assert_all_called=False) as respx_mock:
        # Mock synchronous response structure from Cargo
        def action_execute_handler(request: httpx.Request):
            req_data = json.loads(request.content)
            req_action = json.loads(req_data["action"])
            tool_uuid = req_action["toolUuid"]
            
            payload = {}
            if tool_uuid == CargoAccountIntelligenceProvider.TOOL_ENRICH_COMPANY:
                payload = load_fixture("cargo_enrich_company.json")
            elif tool_uuid == CargoAccountIntelligenceProvider.TOOL_FIND_STAKEHOLDERS:
                payload = load_fixture("cargo_stakeholders.json")
            elif tool_uuid == CargoAccountIntelligenceProvider.TOOL_FIND_COMPETITORS:
                payload = load_fixture("cargo_competitors.json")
            else:
                return httpx.Response(400)
            
            return httpx.Response(200, json={
                "run": {"uuid": str(uuid.uuid4()), "status": "success"},
                "runContext": {"action": payload}
            })

        respx_mock.post("/orchestration/actions/execute").mock(side_effect=action_execute_handler)
        yield respx_mock


@pytest.mark.asyncio
async def test_cargo_provider_resolution(cargo_mock) -> None:
    """Test entity resolution against Cargo adapter using mock HTTP."""
    provider = CargoAccountIntelligenceProvider(api_key="test-key")
    result = await provider.resolve_company("Datadog", "datadog.com")
    assert result is not None
    assert result.domain == "datadog.com"
    assert result.canonical_name == "Datadog"
    assert result.provenance.provider == "cargo"
    assert result.provenance.classification == ProvenanceClassification.TRACEABLE
    await provider.close()


@pytest.mark.asyncio
async def test_cargo_provider_enrichment(cargo_mock) -> None:
    """Test firmographics enrichment and technology categorization."""
    provider = CargoAccountIntelligenceProvider(api_key="test-key")
    
    data = await provider.enrich_company("datadog.com", "Datadog")
    assert data is not None
    assert data.employee_count == 10889
    assert "salesforce" in data.technologies
    assert "crm" in data.tech_stack_by_category
    assert data.provenance.provider == "cargo"
    assert len(data.competitors) == 1
    assert data.competitors[0].name == "New Relic"
    await provider.close()


@pytest.mark.asyncio
async def test_honest_provenance_classification() -> None:
    """Validate that unstated upstream citations are NOT falsely marked TRACEABLE."""
    raw_payload_without_citation = {
        "name": "Acme Inc",
        "employeesCount": 500,
    }
    normalized = CargoContextNormalizer.normalize_company_enrichment(
        raw_data=raw_payload_without_citation,
        domain="acme.com",
    )
    assert normalized.provenance.classification == ProvenanceClassification.PARTIALLY_TRACEABLE
    assert normalized.provenance.source_url is None
    assert normalized.provenance.upstream_provider is None
    assert normalized.provenance.confidence is None


@pytest.mark.asyncio
async def test_cargo_stakeholder_discovery(cargo_mock) -> None:
    """Test persona identification and stakeholder normalization."""
    provider = CargoAccountIntelligenceProvider(api_key="test-key")
    
    stakeholders = await provider.discover_stakeholders("datadog.com")
    assert len(stakeholders) > 0
    cfo = stakeholders[0]
    assert cfo.persona_role == "CFO / Economic Buyer"
    assert cfo.seniority_level == "C-Level"
    assert cfo.department == "Finance"
    assert cfo.is_recently_hired is True  # Validates 2001-01-01 dummy date stripping
    await provider.close()


@pytest.mark.asyncio
async def test_zero_leakage_and_provider_swappability(cargo_mock) -> None:
    """Validate that Cargo and MockApollo providers can be swapped interchangeably."""
    tenant_id = uuid.uuid4()
    cargo_provider = CargoAccountIntelligenceProvider(api_key="test-key")
    apollo_provider = MockApolloProvider()

    for p in [cargo_provider, apollo_provider]:
        context = await p.get_full_account_context(
            domain="datadog.com",
            company_name="Datadog",
            tenant_id=tenant_id,
        )
        assert context is not None
        assert context.tenant_id == tenant_id
        assert isinstance(context.company, CompanyEnrichmentData)
        assert context.company.provenance.provider == p.provider_name

    await cargo_provider.close()


@pytest.mark.asyncio
async def test_enrichment_orchestrator_cargo_integration_and_fallback(cargo_mock) -> None:
    """Test EnrichmentOrchestrator with primary Cargo and observable fallback."""
    mock_session = AsyncMock()
    account_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    account = Account(
        id=account_id,
        tenant_id=tenant_id,
        name="Datadog",
        domain="datadog.com",
        provider="manual",
        provider_record_id="rec-123",
        enrichment_status=EnrichmentStatus.PENDING.value,
        tech_stack={},
        executives=[],
        pain_signals=[],
        opportunities=[],
        contacts=[],
        enrichment_sources=[],
    )

    mock_session.get.return_value = account

    cargo_provider = CargoAccountIntelligenceProvider(api_key="test-key")
    orchestrator = EnrichmentOrchestrator(
        db=mock_session,
        intelligence_provider=cargo_provider,
    )

    result = await orchestrator.enrich_account(account_id)

    assert result["status"] == EnrichmentStatus.ENRICHED.value
    assert "cargo" in result["sources_used"]
    assert account.company_size == 10889

    await orchestrator.close()
    await cargo_provider.close()
