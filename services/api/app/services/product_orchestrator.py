from __future__ import annotations

import uuid
from typing import Any

from app.clients.internal_api_client import InternalAPIClient
from app.clients.layer4_client import Layer4Client
from app.models.product import (
    AssumptionScoreRequest,
    CFONarrativeGenerateRequest,
    EvidenceExtractRequest,
    ProductJobResponse,
    RealizationCompareRequest,
    ValueDriversMapRequest,
    ValueModelGenerateRequest,
    ValueModelQARequest,
    ValueModelValidateRequest,
)


class ProductOrchestrator:
    """Maps monetized product endpoints to existing internal and Layer 4 services."""

    def __init__(
        self,
        layer4: Layer4Client | None = None,
        internal: InternalAPIClient | None = None,
    ):
        self.layer4 = layer4 or Layer4Client()
        self.internal = internal or InternalAPIClient()

    def _sync_job(self, product_code: str, result: dict[str, Any]) -> ProductJobResponse:
        return ProductJobResponse(
            job_id=f"job_{uuid.uuid4().hex}",
            product_code=product_code,
            status="completed",
            result=result,
        )

    def _async_job(
        self, product_code: str, workflow_id: str
    ) -> ProductJobResponse:
        return ProductJobResponse(
            job_id=workflow_id,
            product_code=product_code,
            status="accepted",
            result=None,
        )

    async def map_value_drivers(
        self, tenant_id: str, payload: ValueDriversMapRequest
    ) -> ProductJobResponse:
        account_id = payload.account_id or "default"
        workflow = await self.layer4.generate_hypotheses(
            tenant_id,
            {
                "account_id": account_id,
                "context": payload.context,
                "industry": payload.industry,
            },
        )
        workflow_id = workflow.get("id") or workflow.get("workflow_id") or str(uuid.uuid4())
        return self._async_job("value_drivers", workflow_id)

    async def generate_value_model(
        self, tenant_id: str, payload: ValueModelGenerateRequest
    ) -> ProductJobResponse:
        account_id = payload.account_id or "default"
        roi_result = await self.layer4.run_roi_analysis(
            tenant_id,
            {
                "account_id": account_id,
                "value_driver_ids": payload.drivers,
                "prospect_data": payload.assumptions or {},
            },
        )
        return self._sync_job("value_models", roi_result)

    async def validate_value_model(
        self, tenant_id: str, payload: ValueModelValidateRequest
    ) -> ProductJobResponse:
        account_id = payload.account_id or "default"
        review = await self.internal.create_review(
            tenant_id,
            account_id,
            {"scope": "value_model", "artifact": payload.value_model},
        )
        return self._sync_job("value_models", review)

    async def qa_value_model(
        self, tenant_id: str, payload: ValueModelQARequest
    ) -> ProductJobResponse:
        account_id = payload.account_id or "default"
        workflow = await self.layer4.submit_workflow(
            tenant_id,
            workflow_type="value_model_qa",
            inputs={
                "account_id": account_id,
                "value_model": payload.value_model,
                "question": payload.question,
            },
        )
        workflow_id = workflow.get("id") or workflow.get("workflow_id") or str(uuid.uuid4())
        return self._async_job("value_models", workflow_id)

    async def score_assumption(
        self, tenant_id: str, payload: AssumptionScoreRequest
    ) -> ProductJobResponse:
        account_id = payload.account_id or "default"
        hypothesis = await self.internal.create_hypothesis(
            tenant_id,
            account_id,
            {
                "claim": payload.assumption,
                "evidence": payload.evidence,
                "confidence": "medium",
            },
        )
        return self._sync_job("assumptions", hypothesis)

    async def extract_value_signals(
        self, tenant_id: str, payload: EvidenceExtractRequest
    ) -> ProductJobResponse:
        account_id = payload.account_id or "default"
        signal = await self.internal.extract_signal(
            tenant_id,
            account_id,
            {"extracted_text": payload.source_text},
        )
        return self._sync_job("evidence", signal)

    async def generate_cfo_narrative(
        self, tenant_id: str, payload: CFONarrativeGenerateRequest
    ) -> ProductJobResponse:
        account_id = payload.account_id or "default"
        narrative = await self.layer4.generate_narrative(
            tenant_id,
            {
                "account_id": account_id,
                "audience": payload.audience,
                "account_data": payload.value_model,
            },
        )
        return self._sync_job("cfo_narratives", narrative)

    async def compare_realization(
        self, tenant_id: str, payload: RealizationCompareRequest
    ) -> ProductJobResponse:
        account_id = payload.account_id or "default"
        plan_id = payload.plan_id or "default"
        await self.internal.patch_realization_actuals(
            tenant_id, account_id, plan_id, payload.actuals or {}
        )
        variance = await self.internal.get_realization_variance(
            tenant_id, account_id, plan_id
        )
        return self._sync_job("realization", variance)
