from __future__ import annotations

"""Composition helpers that wire Layer 4 agents to concrete adapters."""

from collections.abc import Mapping
from typing import Any

from layer4_agents.adapters.company_knowledge_pipeline import (
    CrossLayerCompanyKnowledgePipelineAdapter,
)
from layer4_agents.adapters.context_clients import (
    create_context_financial_extraction_client,
    create_context_ingestion_client,
)
from layer4_agents.adapters.ground_truth_proxy import Layer5GroundTruthProxyAdapter
from layer4_agents.adapters.prospect_context import CrossLayerProspectContextAdapter
from layer4_agents.adapters.signal_clients import (
    create_signal_extraction_client,
    create_signal_knowledge_client,
)
from layer4_agents.adapters.signal_review import Layer3SignalReviewAdapter
from layer4_agents.agents.signal_detection import SignalDetectionAgent
from layer4_agents.agents.taxonomy import ContextExtractionAgent
from layer4_agents.config.settings import get_settings
from layer4_agents.integration.layer5_client import get_layer5_client
from layer4_agents.interfaces.company_knowledge_pipeline import CompanyKnowledgePipelinePort
from layer4_agents.interfaces.ground_truth_proxy import GroundTruthProxyPort
from layer4_agents.interfaces.prospect_context import ProspectContextPort
from layer4_agents.interfaces.signal_review import SignalReviewPort


def create_signal_detection_agent(config: Mapping[str, Any] | None = None) -> SignalDetectionAgent:
    """Create SignalDetectionAgent with production cross-layer client factories."""

    return SignalDetectionAgent(
        config=dict(config or {}),
        layer2_client_factory=create_signal_extraction_client,
        layer3_client_factory=create_signal_knowledge_client,
    )


def create_context_extraction_agent(config: Mapping[str, Any] | None = None) -> ContextExtractionAgent:
    """Create ContextExtractionAgent with production cross-layer client factories."""

    return ContextExtractionAgent(
        config=dict(config or {}),
        layer1_client_factory=create_context_ingestion_client,
        layer2_client_factory=create_context_financial_extraction_client,
    )


def create_company_knowledge_pipeline_client() -> CompanyKnowledgePipelinePort:
    """Create the production company knowledge pipeline adapter."""

    settings = get_settings()
    return CrossLayerCompanyKnowledgePipelineAdapter(
        layer1_url=str(settings.layer1_api_url),
        layer2_url=str(settings.layer2_api_url),
        layer3_url=str(settings.layer3_api_url),
    )


def create_signal_review_client(base_url: str) -> SignalReviewPort:
    """Create the production signal/evidence review adapter."""

    return Layer3SignalReviewAdapter(base_url=base_url)


def create_ground_truth_proxy_client() -> GroundTruthProxyPort:
    """Create the production Ground Truth proxy adapter."""

    return Layer5GroundTruthProxyAdapter(client=get_layer5_client())


def create_prospect_context_client(
    *,
    layer1_url: str,
    layer2_url: str,
    layer3_url: str,
    layer5_url: str,
) -> ProspectContextPort:
    """Create the production prospect context adapter."""

    return CrossLayerProspectContextAdapter(
        layer1_url=layer1_url,
        layer2_url=layer2_url,
        layer3_url=layer3_url,
        layer5_url=layer5_url,
    )
