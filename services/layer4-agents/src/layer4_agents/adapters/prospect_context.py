from __future__ import annotations

"""Cross-layer prospect context adapter."""

from typing import Any

from layer4_agents.integration.layer1_client import Layer1IngestionClient
from layer4_agents.integration.layer2_client import Layer2ExtractionClient
from layer4_agents.integration.layer3_client import Layer3Client, Layer3ClientError
from layer4_agents.integration.layer5_client import Layer5GroundTruthClient
from layer4_agents.interfaces.prospect_context import ProspectContextPort, ProspectContextSources


class CrossLayerProspectContextAdapter(ProspectContextPort):
    """ProspectContextPort backed by Layer 1, 2, 3, and 5 clients."""

    def __init__(
        self,
        *,
        layer1_url: str,
        layer2_url: str,
        layer3_url: str,
        layer5_url: str,
    ) -> None:
        self._layer1_url = layer1_url
        self._layer2_url = layer2_url
        self._layer3_url = layer3_url
        self._layer5_url = layer5_url

    async def load_context_sources(
        self,
        *,
        prospect_id: str,
        tenant_id: str,
    ) -> ProspectContextSources:
        layer3 = Layer3Client(base_url=self._layer3_url, tenant_id=tenant_id)
        layer1 = Layer1IngestionClient(base_url=self._layer1_url)
        layer2 = Layer2ExtractionClient(base_url=self._layer2_url)
        layer5 = Layer5GroundTruthClient(base_url=self._layer5_url, tenant_id=tenant_id)

        try:
            profile_data = await self._load_profile(layer3, prospect_id, tenant_id)
            role_value = await self._infer_role(layer2, prospect_id, profile_data)
            truth_items = await self._load_truth_items(layer5, tenant_id)
            return ProspectContextSources(
                profile_data=profile_data,
                role_value=role_value,
                truth_items=truth_items,
            )
        finally:
            await layer1.close()
            await layer2.close()
            await layer3.close()
            await layer5.close()

    async def _load_profile(
        self,
        layer3: Layer3Client,
        prospect_id: str,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        try:
            return await layer3.get_entity(prospect_id, tenant_id=tenant_id)
        except Layer3ClientError:
            return None

    async def _infer_role(
        self,
        layer2: Layer2ExtractionClient,
        prospect_id: str,
        profile_data: dict[str, Any] | None,
    ) -> str | None:
        role_hint = (profile_data or {}).get("title") or (profile_data or {}).get("role")
        if role_hint:
            return str(role_hint)

        extraction = await layer2.extract_financial_metrics(
            document_text=f"Infer contact role for prospect {prospect_id}",
            metrics=["contact_role"],
        )
        maybe_role = extraction.get("contact_role") or extraction.get("metrics", {}).get("contact_role")
        return str(maybe_role) if maybe_role else None

    async def _load_truth_items(
        self,
        layer5: Layer5GroundTruthClient,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        truths = await layer5.list_truths(
            organization_id=tenant_id,
            claim_type=None,
            status="VALIDATED",
            limit=25,
        )
        truth_items = truths.get("items", []) if isinstance(truths, dict) else []
        return truth_items if isinstance(truth_items, list) else []
