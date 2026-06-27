from uuid import uuid4

import pytest

from app.clients.internal_api_client import InternalAPIClient
from app.clients.layer4_client import Layer4Client
from app.models.product import (
    AssumptionScoreRequest,
    CFONarrativeGenerateRequest,
    EvidenceExtractRequest,
    RealizationCompareRequest,
    ValueDriversMapRequest,
    ValueModelGenerateRequest,
    ValueModelQARequest,
    ValueModelValidateRequest,
)
from app.services.product_orchestrator import ProductOrchestrator


class _MockLayer4(Layer4Client):
    def __init__(self):
        pass

    async def generate_hypotheses(self, tenant_id, payload):
        return {"id": "wf-hyp-1", "status": "running"}

    async def run_roi_analysis(self, tenant_id, payload):
        return {"roi": 2.5}

    async def submit_workflow(self, tenant_id, workflow_type, inputs):
        return {"id": "wf-qa-1", "status": "running"}

    async def generate_narrative(self, tenant_id, payload):
        return {"narrative": "CFO summary"}


class _MockInternal(InternalAPIClient):
    def __init__(self):
        pass

    async def create_review(self, tenant_id, account_id, payload):
        return {"review_id": "rev-1", "valid": True}

    async def create_hypothesis(self, tenant_id, account_id, payload):
        return {"hypothesis_id": "hyp-1", "confidence": "high"}

    async def extract_signal(self, tenant_id, account_id, payload):
        return {"signal_id": "sig-1", "signals": []}

    async def patch_realization_actuals(self, tenant_id, account_id, plan_id, payload):
        return {"updated": True}

    async def get_realization_variance(self, tenant_id, account_id, plan_id):
        return {"variance": 0.1}


@pytest.fixture
def orchestrator():
    return ProductOrchestrator(layer4=_MockLayer4(), internal=_MockInternal())


@pytest.mark.asyncio
async def test_map_value_drivers_returns_async_job(orchestrator):
    response = await orchestrator.map_value_drivers(
        str(uuid4()), ValueDriversMapRequest(context="Grow revenue")
    )
    assert response.status == "accepted"
    assert response.product_code == "value_drivers"
    assert response.job_id == "wf-hyp-1"


@pytest.mark.asyncio
async def test_generate_value_model_returns_sync_result(orchestrator):
    response = await orchestrator.generate_value_model(
        str(uuid4()), ValueModelGenerateRequest(drivers=["revenue"])
    )
    assert response.status == "completed"
    assert response.result == {"roi": 2.5}


@pytest.mark.asyncio
async def test_validate_value_model_returns_sync_result(orchestrator):
    response = await orchestrator.validate_value_model(
        str(uuid4()), ValueModelValidateRequest(value_model={})
    )
    assert response.status == "completed"
    assert response.result["valid"] is True


@pytest.mark.asyncio
async def test_qa_value_model_returns_async_job(orchestrator):
    response = await orchestrator.qa_value_model(
        str(uuid4()), ValueModelQARequest(value_model={}, question="Q")
    )
    assert response.status == "accepted"
    assert response.job_id == "wf-qa-1"


@pytest.mark.asyncio
async def test_score_assumption_returns_sync_result(orchestrator):
    response = await orchestrator.score_assumption(
        str(uuid4()), AssumptionScoreRequest(assumption="A")
    )
    assert response.status == "completed"
    assert response.result["confidence"] == "high"


@pytest.mark.asyncio
async def test_extract_signals_returns_sync_result(orchestrator):
    response = await orchestrator.extract_value_signals(
        str(uuid4()), EvidenceExtractRequest(source_text="text")
    )
    assert response.status == "completed"
    assert response.result["signal_id"] == "sig-1"


@pytest.mark.asyncio
async def test_generate_cfo_narrative_returns_sync_result(orchestrator):
    response = await orchestrator.generate_cfo_narrative(
        str(uuid4()), CFONarrativeGenerateRequest(value_model={})
    )
    assert response.status == "completed"
    assert response.result["narrative"] == "CFO summary"


@pytest.mark.asyncio
async def test_compare_realization_returns_sync_result(orchestrator):
    response = await orchestrator.compare_realization(
        str(uuid4()), RealizationCompareRequest(plan_id="plan-1")
    )
    assert response.status == "completed"
    assert response.result["variance"] == 0.1
