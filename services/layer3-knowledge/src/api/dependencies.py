"""FastAPI dependencies for Layer 3 API."""

import logging

from fastapi import FastAPI, Request
from neo4j import AsyncDriver
from neo4j.exceptions import (
    ConfigurationError,
    Neo4jError,
    ServiceUnavailable,
    TransientError,
)
from value_fabric.shared.error_handling.exceptions import ServiceUnavailableError

from ..agents import (
    NarrativeSynthesisAgent,
    ProvenanceTrackingAgent,
    ROICalculationAgent,
    ValueTreeProjectionAgent,
    WhitespaceAnalysisAgent,
)
from ..analytics import (
    CentralityAnalyzer,
    CommunityDetector,
    SimilarityAnalyzer,
)
from ..config import Settings, get_settings
from ..db.driver import get_driver, reset_driver
from ..ingestion import Neo4jLoader, SyncManager
from ..retrieval import GraphRAGEngine, HybridSearch, VectorStore
from ..schema import SchemaInitializer

logger = logging.getLogger(__name__)


def _extract_tenant_id(request: Request | None) -> str | None:
    """Extract tenant ID from request headers or state."""
    if request is None:
        return None
    if hasattr(request.state, "tenant_id") and request.state.tenant_id:
        return str(request.state.tenant_id)
    return None


class AppState:
    """Application state container for shared resources."""

    def __init__(self):
        self.settings: Settings = None
        self.neo4j_driver: AsyncDriver = None
        self.vector_store: VectorStore = None
        self.schema_initializer: SchemaInitializer = None
        self.neo4j_loader: Neo4jLoader = None
        self.sync_manager: SyncManager = None
        self.graph_rag: GraphRAGEngine = None
        self.hybrid_search: HybridSearch = None
        self.community_detector: CommunityDetector = None
        self.centrality_analyzer: CentralityAnalyzer = None
        self.similarity_analyzer: SimilarityAnalyzer = None
        # Backend Agents (Layer 3 service implementations)
        # NOTE: These Layer 3 agents are the service-layer implementations.
        # The canonical Layer 4 agent names are:
        #   ValueTreeProjectionAgent  → ValueModelAgent
        #   WhitespaceAnalysisAgent   → ValueModelAgent
        #   ROICalculationAgent       → ValueModelAgent
        #   NarrativeSynthesisAgent   → NarrativeAgent
        #   ProvenanceTrackingAgent   → IntegrityAgent (provenance is now GATE cross-cutting)
        # See docs/platform-contract/DEPRECATION_MAP.md for migration timeline.
        self.value_tree_projection_agent: ValueTreeProjectionAgent = None
        self.whitespace_analysis_agent: WhitespaceAnalysisAgent = None
        self.roi_calculation_agent: ROICalculationAgent = None
        self.narrative_synthesis_agent: NarrativeSynthesisAgent = None
        self.provenance_tracking_agent: ProvenanceTrackingAgent = None


async def init_app_state(app: FastAPI) -> AppState:
    """Initialize application state with all dependencies.

    Neo4j connection failures are non-fatal at startup: the service starts in
    a degraded mode and each component retries the connection on first use.
    """
    state = AppState()
    state.settings = get_settings()

    # ── 1. Neo4j driver ──────────────────────────────────────────────────────
    try:
        state.neo4j_driver = await get_driver(state.settings)
        logger.info("Neo4j driver connected successfully")
    except (ConfigurationError, ServiceUnavailable, TransientError, Neo4jError) as exc:
        logger.warning(
            "Neo4j unavailable at startup (%s). Service will retry on first request.",
            exc,
            extra={
                "component": "layer3.api.dependencies",
                "dependency": "neo4j",
                "action": "init_driver",
                "fallback_used": "degraded_startup",
                "error_type": type(exc).__name__,
            },
        )
        state.neo4j_driver = None

    try:
        # Initialize schema (constraints and indexes)
        state.schema_initializer = SchemaInitializer(
            driver=state.neo4j_driver,
            settings=state.settings,
        )
        if state.neo4j_driver is not None:
            await state.schema_initializer.initialize_schema()
            logger.info("Schema initialized successfully")

        # Initialize Neo4j-native vector store (no Pinecone dependency)
        try:
            state.vector_store = VectorStore(
                driver=state.neo4j_driver,
                settings=state.settings,
            )
            logger.info("Neo4j-native vector store initialized")
        except (ConfigurationError, RuntimeError, ValueError, Neo4jError) as e:
            logger.warning(
                "Could not initialize vector store: %s",
                e,
                extra={
                    "component": "layer3.api.dependencies",
                    "dependency": "vector_store",
                    "action": "initialize",
                    "fallback_used": "vector_store_disabled",
                    "error_type": type(e).__name__,
                },
            )
            state.vector_store = None

        # Initialize ingestion components
        state.neo4j_loader = Neo4jLoader(
            driver=state.neo4j_driver,
            settings=state.settings,
        )
        state.sync_manager = SyncManager(
            loader=state.neo4j_loader,
            driver=state.neo4j_driver,
            settings=state.settings,
        )

        # Initialize retrieval components
        state.graph_rag = GraphRAGEngine(
            driver=state.neo4j_driver,
            vector_store=state.vector_store,
            settings=state.settings,
        )
        state.hybrid_search = HybridSearch(
            driver=state.neo4j_driver,
            vector_store=state.vector_store,
            settings=state.settings,
        )

        # Initialize analytics components
        state.community_detector = CommunityDetector(
            driver=state.neo4j_driver,
            settings=state.settings,
        )
        state.centrality_analyzer = CentralityAnalyzer(
            driver=state.neo4j_driver,
            settings=state.settings,
        )
        state.similarity_analyzer = SimilarityAnalyzer(
            driver=state.neo4j_driver,
            vector_store=state.vector_store,
            settings=state.settings,
        )

        # Initialize backend agents
        state.value_tree_projection_agent = ValueTreeProjectionAgent(
            driver=state.neo4j_driver,
        )
        state.whitespace_analysis_agent = WhitespaceAnalysisAgent(
            driver=state.neo4j_driver,
        )
        state.roi_calculation_agent = ROICalculationAgent(
            driver=state.neo4j_driver,
        )
        state.narrative_synthesis_agent = NarrativeSynthesisAgent()
        state.provenance_tracking_agent = ProvenanceTrackingAgent(
            driver=state.neo4j_driver,
        )
        logger.info("Backend agents initialized")

        # Attach state to app
        app.state.app_state = state
        logger.info(
            "Application state initialized (neo4j_connected=%s)",
            state.neo4j_driver is not None,
        )

        return state

    except (ConfigurationError, RuntimeError, ValueError, Neo4jError) as e:
        logger.error(
            "Failed to initialize application: %s",
            e,
            extra={
                "component": "layer3.api.dependencies",
                "dependency": "application_state",
                "action": "initialize",
                "fallback_used": "partial_state_cleanup",
                "error_type": type(e).__name__,
            },
        )
        await _cleanup_partial_state(state)
        app.state.app_state = (
            state  # attach partial state so health check can report it
        )
        return state


async def recover_neo4j_state(app: FastAPI) -> AppState:
    """Reconnect Neo4j-backed application state after a degraded startup.

    Docker Compose can mark Neo4j HTTP as healthy before the Bolt endpoint and
    schema operations are ready. Startup therefore intentionally degrades instead
    of crashing, and health checks call this helper to perform a bounded lazy
    recovery once Neo4j becomes reachable.
    """
    state = getattr(app.state, "app_state", None)
    if state is None:
        state = AppState()
        state.settings = get_settings()
        app.state.app_state = state

    if state.settings is None:
        state.settings = get_settings()

    if state.neo4j_driver is not None and state.schema_initializer is not None:
        return state

    try:
        state.neo4j_driver = await get_driver(state.settings)
        state.schema_initializer = SchemaInitializer(
            driver=state.neo4j_driver,
            settings=state.settings,
        )
        await state.schema_initializer.initialize_schema()
        logger.info("Neo4j state recovered after degraded startup")
    except (ConfigurationError, ServiceUnavailable, TransientError, Neo4jError) as exc:
        logger.warning(
            "Neo4j recovery attempt failed: %s",
            exc,
            extra={
                "component": "layer3.api.dependencies",
                "dependency": "neo4j",
                "action": "recover_state",
                "fallback_used": "remain_degraded",
                "error_type": type(exc).__name__,
            },
        )
        state.neo4j_driver = None
        state.schema_initializer = SchemaInitializer(
            driver=None,
            settings=state.settings,
        )
        return state

    state.vector_store = VectorStore(driver=state.neo4j_driver, settings=state.settings)
    state.neo4j_loader = Neo4jLoader(driver=state.neo4j_driver, settings=state.settings)
    state.sync_manager = SyncManager(
        loader=state.neo4j_loader,
        driver=state.neo4j_driver,
        settings=state.settings,
    )
    state.graph_rag = GraphRAGEngine(
        driver=state.neo4j_driver,
        vector_store=state.vector_store,
        settings=state.settings,
    )
    state.hybrid_search = HybridSearch(
        driver=state.neo4j_driver,
        vector_store=state.vector_store,
        settings=state.settings,
    )
    state.community_detector = CommunityDetector(
        driver=state.neo4j_driver,
        settings=state.settings,
    )
    state.centrality_analyzer = CentralityAnalyzer(
        driver=state.neo4j_driver,
        settings=state.settings,
    )
    state.similarity_analyzer = SimilarityAnalyzer(
        driver=state.neo4j_driver,
        vector_store=state.vector_store,
        settings=state.settings,
    )
    state.value_tree_projection_agent = ValueTreeProjectionAgent(driver=state.neo4j_driver)
    state.whitespace_analysis_agent = WhitespaceAnalysisAgent(driver=state.neo4j_driver)
    state.roi_calculation_agent = ROICalculationAgent(driver=state.neo4j_driver)
    state.narrative_synthesis_agent = NarrativeSynthesisAgent()
    state.provenance_tracking_agent = ProvenanceTrackingAgent(driver=state.neo4j_driver)
    return state




def _record_cleanup_error(cleanup_errors: list[str], resource: str, exc: Exception, *, action: str, fallback_used: str) -> None:
    cleanup_errors.append(f"{resource}: {exc}")
    logger.warning(
        "Resource cleanup operation failed",
        extra={
            "component": "layer3.api.dependencies",
            "dependency": resource,
            "action": action,
            "fallback_used": fallback_used,
            "error_type": type(exc).__name__,
        },
    )

async def _cleanup_partial_state(state: AppState) -> None:
    """Clean up partially initialized state to prevent resource leaks."""
    logger.info("Cleaning up partially initialized state...")

    # Close components in reverse order of initialization
    cleanup_errors = []

    # Analytics and retrieval components (have close() methods)
    if state.similarity_analyzer and hasattr(state.similarity_analyzer, "close"):
        try:
            await state.similarity_analyzer.close()
        except Exception as e:
            # Broad catch intentionally retained for shutdown resilience: cleanup must continue.
            _record_cleanup_error(cleanup_errors, "similarity_analyzer", e, action="close_partial", fallback_used="continue_cleanup")

    if state.centrality_analyzer and hasattr(state.centrality_analyzer, "close"):
        try:
            await state.centrality_analyzer.close()
        except Exception as e:
            # Broad catch intentionally retained for shutdown resilience: cleanup must continue.
            _record_cleanup_error(cleanup_errors, "centrality_analyzer", e, action="close_partial", fallback_used="continue_cleanup")

    if state.community_detector and hasattr(state.community_detector, "close"):
        try:
            await state.community_detector.close()
        except Exception as e:
            # Broad catch intentionally retained for shutdown resilience: cleanup must continue.
            _record_cleanup_error(cleanup_errors, "community_detector", e, action="close_partial", fallback_used="continue_cleanup")

    if state.hybrid_search and hasattr(state.hybrid_search, "close"):
        try:
            await state.hybrid_search.close()
        except Exception as e:
            # Broad catch intentionally retained for shutdown resilience: cleanup must continue.
            _record_cleanup_error(cleanup_errors, "hybrid_search", e, action="close_partial", fallback_used="continue_cleanup")

    if state.graph_rag and hasattr(state.graph_rag, "close"):
        try:
            await state.graph_rag.close()
        except Exception as e:
            # Broad catch intentionally retained for shutdown resilience: cleanup must continue.
            _record_cleanup_error(cleanup_errors, "graph_rag", e, action="close_partial", fallback_used="continue_cleanup")

    if state.sync_manager and hasattr(state.sync_manager, "close"):
        try:
            await state.sync_manager.close()
        except Exception as e:
            # Broad catch intentionally retained for shutdown resilience: cleanup must continue.
            _record_cleanup_error(cleanup_errors, "sync_manager", e, action="close_partial", fallback_used="continue_cleanup")

    if state.schema_initializer and hasattr(state.schema_initializer, "close"):
        try:
            await state.schema_initializer.close()
        except Exception as e:
            # Broad catch intentionally retained for shutdown resilience: cleanup must continue.
            _record_cleanup_error(cleanup_errors, "schema_initializer", e, action="close_partial", fallback_used="continue_cleanup")

    # Note: Backend agents don't have close() methods - they don't hold resources

    if cleanup_errors:
        logger.warning(f"Errors during partial cleanup: {cleanup_errors}")
    else:
        logger.info("Partial state cleanup completed")


async def close_app_state(app: FastAPI) -> None:
    """Close all application resources."""
    state: AppState = getattr(app.state, "app_state", None)

    if state:
        logger.info("Closing application resources...")
        cleanup_errors = []

        # Close components that own their drivers
        if state.similarity_analyzer:
            try:
                await state.similarity_analyzer.close()
            except Exception as e:
                # Broad catch intentionally retained for shutdown resilience: cleanup must continue.
                _record_cleanup_error(cleanup_errors, "similarity_analyzer", e, action="close_app", fallback_used="continue_shutdown")
        if state.centrality_analyzer:
            try:
                await state.centrality_analyzer.close()
            except Exception as e:
                # Broad catch intentionally retained for shutdown resilience: cleanup must continue.
                _record_cleanup_error(cleanup_errors, "centrality_analyzer", e, action="close_app", fallback_used="continue_shutdown")
        if state.community_detector:
            try:
                await state.community_detector.close()
            except Exception as e:
                # Broad catch intentionally retained for shutdown resilience: cleanup must continue.
                _record_cleanup_error(cleanup_errors, "community_detector", e, action="close_app", fallback_used="continue_shutdown")
        if state.hybrid_search:
            try:
                await state.hybrid_search.close()
            except Exception as e:
                # Broad catch intentionally retained for shutdown resilience: cleanup must continue.
                _record_cleanup_error(cleanup_errors, "hybrid_search", e, action="close_app", fallback_used="continue_shutdown")
        if state.graph_rag:
            try:
                await state.graph_rag.close()
            except Exception as e:
                # Broad catch intentionally retained for shutdown resilience: cleanup must continue.
                _record_cleanup_error(cleanup_errors, "graph_rag", e, action="close_app", fallback_used="continue_shutdown")
        if state.sync_manager:
            try:
                await state.sync_manager.close()
            except Exception as e:
                # Broad catch intentionally retained for shutdown resilience: cleanup must continue.
                _record_cleanup_error(cleanup_errors, "sync_manager", e, action="close_app", fallback_used="continue_shutdown")
        if state.schema_initializer:
            try:
                await state.schema_initializer.close()
            except Exception as e:
                # Broad catch intentionally retained for shutdown resilience: cleanup must continue.
                _record_cleanup_error(cleanup_errors, "schema_initializer", e, action="close_app", fallback_used="continue_shutdown")

        # Close the shared driver singleton
        try:
            await reset_driver()
        except Exception as exc:
            # Broad catch intentionally retained for shutdown resilience: cleanup must continue.
            _record_cleanup_error(cleanup_errors, "neo4j_driver_singleton", exc, action="reset_driver", fallback_used="continue_shutdown")

        if cleanup_errors:
            logger.warning(f"Errors during resource cleanup: {cleanup_errors}")
        else:
            logger.info("Application resources closed")


def get_app_state(request: Request) -> AppState:
    """Get application state from request."""
    state = getattr(request.app.state, "app_state", None)
    if state is None:
        # Create minimal state for health checks when app not fully initialized
        state = AppState()
        state.settings = get_settings()
    return state


def get_settings_from_state(request: Request) -> Settings:
    """Get settings from application state."""
    return get_app_state(request).settings


def get_neo4j_driver(request: Request) -> AsyncDriver:
    """Get Neo4j driver from application state."""
    driver = get_app_state(request).neo4j_driver
    if driver is None:
        raise ServiceUnavailableError(message = "Neo4j database is currently unavailable. Please retry shortly.")
    return driver


def get_vector_store(request: Request) -> VectorStore:
    """Get vector store from application state."""
    store = get_app_state(request).vector_store
    if store is None:
        raise ServiceUnavailableError(message = "Vector store not available")
    return store


def get_sync_manager(request: Request) -> SyncManager:
    """Get sync manager from application state."""
    return get_app_state(request).sync_manager


def get_graph_rag(request: Request) -> GraphRAGEngine:
    """Get GraphRAG engine from application state."""
    return get_app_state(request).graph_rag


def get_hybrid_search(request: Request) -> HybridSearch:
    """Get hybrid search from application state."""
    return get_app_state(request).hybrid_search


def get_community_detector(request: Request) -> CommunityDetector:
    """Get community detector from application state."""
    return get_app_state(request).community_detector


def get_centrality_analyzer(request: Request) -> CentralityAnalyzer:
    """Get centrality analyzer from application state."""
    return get_app_state(request).centrality_analyzer


def get_similarity_analyzer(request: Request) -> SimilarityAnalyzer:
    """Get similarity analyzer from application state."""
    return get_app_state(request).similarity_analyzer


def get_schema_initializer(request: Request) -> SchemaInitializer:
    """Get schema initializer from application state."""
    return get_app_state(request).schema_initializer


def get_value_tree_projection_agent(request: Request) -> ValueTreeProjectionAgent:
    """Get value tree projection agent from application state."""
    return get_app_state(request).value_tree_projection_agent


def get_whitespace_analysis_agent(request: Request) -> WhitespaceAnalysisAgent:
    """Get whitespace analysis agent from application state."""
    return get_app_state(request).whitespace_analysis_agent


def get_roi_calculation_agent(request: Request) -> ROICalculationAgent:
    """Get ROI calculation agent from application state."""
    return get_app_state(request).roi_calculation_agent


def get_narrative_synthesis_agent(request: Request) -> NarrativeSynthesisAgent:
    """Get narrative synthesis agent from application state."""
    return get_app_state(request).narrative_synthesis_agent


def get_provenance_tracking_agent(request: Request) -> ProvenanceTrackingAgent:
    """Get provenance tracking agent from application state."""
    return get_app_state(request).provenance_tracking_agent
