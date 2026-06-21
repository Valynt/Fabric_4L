from __future__ import annotations

"""Concrete signal-detection client factories for Layer 2 and Layer 3."""

from collections.abc import Mapping
from typing import Any

from layer4_agents.integration.layer2_client import Layer2ExtractionClient
from layer4_agents.integration.layer3_client import Layer3Client
from layer4_agents.interfaces.signal_clients import SignalExtractionPort, SignalKnowledgePort


def create_signal_extraction_client(config: Mapping[str, Any]) -> SignalExtractionPort:
    """Build the default Layer 2 client for signal extraction."""

    return Layer2ExtractionClient(
        base_url=str(config.get("layer2_url", "http://layer2-extraction:8000")),
        api_key=config.get("layer2_api_key"),
    )


def create_signal_knowledge_client(config: Mapping[str, Any]) -> SignalKnowledgePort:
    """Build the default Layer 3 client for signal enrichment and persistence."""

    return Layer3Client(
        base_url=str(config.get("layer3_url", "http://layer3-knowledge:8000")),
    )
