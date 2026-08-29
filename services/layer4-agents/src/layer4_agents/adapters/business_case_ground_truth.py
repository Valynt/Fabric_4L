from __future__ import annotations

"""Business-case Ground Truth adapter backed by the Layer 5 client."""

import os
from typing import Any, cast

from layer4_agents.config.settings import get_settings
from layer4_agents.harness.live_l5_validator import LiveL5Validator
from layer4_agents.harness.validation_hooks import ClaimValidationRequest
from layer4_agents.integration.layer5_client import Layer5GroundTruthClient, get_layer5_client

from ..interfaces.business_case_ground_truth import BusinessCaseGroundTruthPort


class Layer5BusinessCaseGroundTruthAdapter(BusinessCaseGroundTruthPort):
    """BusinessCaseGroundTruthPort implementation backed by Layer5GroundTruthClient."""

    def __init__(self, client: Layer5GroundTruthClient) -> None:
        self._client = client

    async def list_truths(
        self,
        *,
        organization_id: str,
        claim_type: str | None = None,
        min_maturity: int | None = None,
        min_confidence: float | None = None,
        applies_to_opportunity: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._client.list_truths(
                organization_id=organization_id,
                claim_type=claim_type,
                min_maturity=min_maturity,
                min_confidence=min_confidence,
                applies_to_opportunity=applies_to_opportunity,
                limit=limit,
                offset=offset,
            ),
        )

    async def submit_truth(
        self,
        *,
        claim: str,
        claim_type: str,
        confidence: float,
        organization_id: str,
        applies_to: dict[str, Any] | None = None,
        sources: list[dict[str, Any]] | None = None,
        raw_extraction_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._client.submit_truth(
                claim=claim,
                claim_type=claim_type,
                confidence=confidence,
                organization_id=organization_id,
                applies_to=applies_to,
                sources=sources,
                raw_extraction_data=raw_extraction_data,
            ),
        )

    async def validate_claim(
        self,
        *,
        tenant_id: str,
        claim_id: str,
        claim_text: str,
        evidence_refs: list[Any],
        account_id: str | None = None,
        value_pack_id: str = "business_case",
    ) -> dict[str, Any]:
        validator = LiveL5Validator(client=self._client)
        result = await validator.validate(
            ClaimValidationRequest(
                tenant_id=tenant_id,
                claim_id=claim_id,
                claim_text=claim_text,
                evidence_refs=evidence_refs,
                account_id=account_id,
                value_pack_id=value_pack_id,
            )
        )
        return {
            "status": result.validation_state.value,
            "reason": result.reason,
            "evidence_refs": result.evidence_refs,
        }

    async def sync_validated_truths(self, *, organization_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._client.sync_validated_truths(organization_id=organization_id),
        )

    async def close(self) -> None:
        await self._client.close()


def create_layer5_business_case_ground_truth_client(
    organization_id: str,
) -> BusinessCaseGroundTruthPort | None:
    """Create the production Ground Truth adapter for a business-case tenant."""

    layer5_url = get_settings().layer5_api_url
    if not layer5_url:
        return None
    service_token = os.getenv("LAYER5_SERVICE_TOKEN")
    client = get_layer5_client(
        base_url=layer5_url,
        service_token=service_token,
        tenant_id=organization_id if not service_token else None,
    )
    return Layer5BusinessCaseGroundTruthAdapter(client=client)
