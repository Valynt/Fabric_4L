from __future__ import annotations

"""Concrete context-extraction client factories for Layer 1 and Layer 2."""

from collections.abc import Mapping
from typing import Any

from layer4_agents.interfaces.context_clients import (
    ContextFinancialExtractionPort,
    ContextIngestionPort,
)


def create_context_ingestion_client(config: Mapping[str, Any]) -> ContextIngestionPort:
    """Build the default Layer 1 client for context extraction."""

    from layer4_agents.integration.layer1_client import Layer1IngestionClient

    return Layer1IngestionClient(
        base_url=str(config.get("layer1_url", "http://layer1-ingestion:8000")),
        api_key=config.get("layer1_api_key"),
    )


def create_context_financial_extraction_client(
    config: Mapping[str, Any],
) -> ContextFinancialExtractionPort:
    """Build the default Layer 2 client for context financial extraction."""

    from layer4_agents.integration.layer2_client import Layer2ExtractionClient

    return Layer2ExtractionClient(
        base_url=str(config.get("layer2_url", "http://layer2-extraction:8000")),
    )
