from __future__ import annotations

"""Company knowledge pipeline adapter backed by L1, L2, and L3 clients."""

from typing import Any, cast

from layer4_agents.integration.layer1_client import Layer1IngestionClient
from layer4_agents.integration.layer2_client import Layer2ExtractionClient
from layer4_agents.integration.layer3_client import Layer3Client

from ..interfaces.company_knowledge_pipeline import CompanyKnowledgePipelinePort


class CrossLayerCompanyKnowledgePipelineAdapter(CompanyKnowledgePipelinePort):
    """CompanyKnowledgePipelinePort implementation backed by cross-layer clients."""

    def __init__(
        self,
        *,
        layer1_url: str,
        layer2_url: str,
        layer3_url: str,
    ) -> None:
        self._layer1_url = layer1_url
        self._layer2_url = layer2_url
        self._layer3_url = layer3_url

    async def crawl_website(
        self,
        *,
        tenant_id: str,
        url: str,
        name: str,
    ) -> dict[str, Any]:
        client = Layer1IngestionClient(base_url=self._layer1_url, tenant_id=tenant_id)
        try:
            return cast(
                dict[str, Any],
                await client.crawl_website(
                    url=url,
                    tenant_id=tenant_id,
                    name=name,
                ),
            )
        finally:
            await client.close()

    async def extract_value_attributes(
        self,
        *,
        tenant_id: str,
        content_id: str,
        source_url: str,
        markdown_content: str,
    ) -> dict[str, Any]:
        client = Layer2ExtractionClient(base_url=self._layer2_url, tenant_id=tenant_id)
        try:
            return cast(
                dict[str, Any],
                await client.extract_value_attributes(
                    content_id=content_id,
                    source_url=source_url,
                    markdown_content=markdown_content,
                    tenant_id=tenant_id,
                ),
            )
        finally:
            await client.close()

    async def ingest_profile(
        self,
        *,
        tenant_id: str,
        ingestion_payload: dict[str, Any],
        passthrough_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        client = Layer3Client(base_url=self._layer3_url, tenant_id=tenant_id)
        try:
            return cast(
                dict[str, Any],
                await client.ingest(
                    ingestion_payload=ingestion_payload,
                    tenant_id=tenant_id,
                    passthrough_headers=passthrough_headers,
                ),
            )
        finally:
            await client.close()
