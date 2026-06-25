from __future__ import annotations

"""Ground Truth proxy adapter backed by the Layer 5 integration client."""

from typing import Any, cast

from layer4_agents.integration.layer5_client import Layer5GroundTruthClient
from ..interfaces.ground_truth_proxy import GroundTruthProxyPort


class Layer5GroundTruthProxyAdapter(GroundTruthProxyPort):
    """GroundTruthProxyPort implementation backed by Layer5GroundTruthClient."""

    def __init__(self, client: Layer5GroundTruthClient) -> None:
        self._client = client

    async def list_truths(
        self,
        *,
        tenant_id: str,
        status: str | None = None,
        claim_type: str | None = None,
        min_maturity: int | None = None,
        min_confidence: float | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._client.list_truths(
                organization_id=tenant_id,
                status=status,
                claim_type=claim_type,
                min_maturity=min_maturity,
                min_confidence=min_confidence,
                limit=limit,
                offset=offset,
            ),
        )

    async def get_truth(self, *, truth_id: str, tenant_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._client.get_truth(
                truth_id=truth_id,
                organization_id=tenant_id,
            ),
        )

    async def get_truth_audit(self, *, truth_id: str, tenant_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._client.get_truth_audit(
                truth_id=truth_id,
                organization_id=tenant_id,
            ),
        )

    async def validate_truth(
        self,
        *,
        truth_id: str,
        action: str,
        actor: str,
        tenant_id: str,
        actor_type: str = "user",
        notes: str | None = None,
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._client.validate_truth(
                truth_id=truth_id,
                action=action,
                actor=actor,
                actor_type=actor_type,
                organization_id=tenant_id,
                notes=notes,
            ),
        )

    async def get_freshness_summary(self, *, tenant_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._client.get_freshness_summary(organization_id=tenant_id),
        )

    async def get_stale_truths(
        self,
        *,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._client.get_stale_truths(
                organization_id=tenant_id,
                limit=limit,
                offset=offset,
            ),
        )

    async def get_maturity_ladder(self, *, tenant_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._client.get_maturity_ladder(organization_id=tenant_id),
        )
