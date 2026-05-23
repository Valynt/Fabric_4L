"""Pytest configuration for Layer 4 Agents tests.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

# ── Path Setup ─────────────────────────────────────────────────────────────
_tests_dir = Path(__file__).parent.resolve()
_layer4_dir = _tests_dir.parent.resolve()
_repo_root = _layer4_dir.parent.parent.resolve()  # layer4-agents -> services -> repo root

# Add repo root to path BEFORE any imports
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Add src/ so bare `from harness.X` imports in src/harness/__init__.py resolve
_src_dir = _layer4_dir / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

# Settings are instantiated by several service imports during collection.
# Keep tests hermetic while still allowing callers to provide real endpoints.
os.environ.setdefault("LAYER4_LAYER1_API_URL", "http://localhost:8001")
os.environ.setdefault("LAYER4_LAYER2_API_URL", "http://localhost:8002")
os.environ.setdefault("LAYER4_LAYER3_API_URL", "http://localhost:8003")
os.environ.setdefault("LAYER4_LAYER5_API_URL", "http://localhost:8005")
os.environ.setdefault("LAYER4_ALLOW_INSECURE_SERVICE_HTTP_IN_DEVELOPMENT", "true")

import pytest
from unittest.mock import MagicMock

# Stub optional heavy deps before any imports that transitively require them

# neo4j — pulled in by layer3-knowledge services; must be stubbed before any
# import that transitively reaches layer3-knowledge.
try:
    import neo4j  # noqa: F401
except ImportError:
    import types as _types
    _neo4j = _types.ModuleType("neo4j")
    _neo4j.__path__ = []  # type: ignore[attr-defined]
    _neo4j.AsyncDriver = MagicMock()
    _neo4j.AsyncSession = MagicMock()
    _neo4j.AsyncGraphDatabase = MagicMock()
    _neo4j_exc = _types.ModuleType("neo4j.exceptions")
    _neo4j_graph = _types.ModuleType("neo4j.graph")
    sys.modules["neo4j"] = _neo4j
    sys.modules["neo4j.exceptions"] = _neo4j_exc
    sys.modules["neo4j.graph"] = _neo4j_graph

try:
    import anthropic  # noqa: F401
except ImportError:
    import types as _types
    sys.modules["anthropic"] = _types.ModuleType("anthropic")

# canonical.llm_output_parser and services.llm_output_parser —
# platform-contract package not installed in the test environment; stub both
# so governed_llm_client and signal_detection can be imported without the
# full platform-contract wheel or a services/__init__.py.
try:
    from canonical.llm_output_parser import parse_llm_json  # noqa: F401
except (ImportError, ModuleNotFoundError):
    import types as _types
    import json as _json

    def _parse_llm_json(text: str):  # type: ignore[return]
        try:
            return _json.loads(text)
        except Exception:
            return {}

    _canonical = _types.ModuleType("canonical")
    _canonical.__path__ = []  # type: ignore[attr-defined]
    _canonical_llm = _types.ModuleType("canonical.llm_output_parser")
    _canonical_llm.parse_llm_json = _parse_llm_json  # type: ignore[attr-defined]
    sys.modules["canonical"] = _canonical
    sys.modules["canonical.llm_output_parser"] = _canonical_llm

# services.llm_output_parser — src/services/ has no __init__.py so the bare
# `from services.llm_output_parser import parse_llm_json` in governed_llm_client
# fails unless we stub the module directly.
# Only create and mutate a new stub; never touch an existing real module.
try:
    from services.llm_output_parser import parse_llm_json as _  # noqa: F401
except (ImportError, ModuleNotFoundError):
    import types as _types
    import json as _json2

    def _parse_llm_json2(text: str):  # type: ignore[return]
        try:
            return _json2.loads(text)
        except Exception:
            return {}

    if "services" not in sys.modules:
        _svc_pkg = _types.ModuleType("services")
        _svc_pkg.__path__ = []  # type: ignore[attr-defined]
        sys.modules["services"] = _svc_pkg
    _svc_llm = _types.ModuleType("services.llm_output_parser")
    _svc_llm.parse_llm_json = _parse_llm_json2  # type: ignore[attr-defined]
    sys.modules["services.llm_output_parser"] = _svc_llm

try:
    import jinja2  # noqa: F401
except ImportError:
    sys.modules["jinja2"] = MagicMock()

try:
    import redis.asyncio  # noqa: F401
except ImportError:
    import types
    _redis = types.ModuleType("redis")
    _redis.asyncio = MagicMock()
    sys.modules["redis"] = _redis
    sys.modules["redis.asyncio"] = _redis.asyncio

try:
    import opentelemetry  # noqa: F401
except ImportError:
    pass

import types
import importlib.util

def _make_pkg(name):
    m = types.ModuleType(name)
    m.__path__ = []
    spec = importlib.util.spec_from_loader(name, loader=None)
    spec.submodule_search_locations = []
    m.__spec__ = spec
    sys.modules[name] = m
    return m

# Idempotently ensure opentelemetry stubs exist (another conftest may have created a partial stub)
_otel = sys.modules.get("opentelemetry") or _make_pkg("opentelemetry")
if not hasattr(_otel, "trace"):
    _otel.trace = _make_pkg("opentelemetry.trace")

_exp = sys.modules.get("opentelemetry.exporter") or _make_pkg("opentelemetry.exporter")
_otlp = sys.modules.get("opentelemetry.exporter.otlp") or _make_pkg("opentelemetry.exporter.otlp")
_proto = sys.modules.get("opentelemetry.exporter.otlp.proto") or _make_pkg("opentelemetry.exporter.otlp.proto")
_http = sys.modules.get("opentelemetry.exporter.otlp.proto.http") or _make_pkg("opentelemetry.exporter.otlp.proto.http")
_txe = sys.modules.get("opentelemetry.exporter.otlp.proto.http.trace_exporter") or _make_pkg("opentelemetry.exporter.otlp.proto.http.trace_exporter")
_txe.OTLPSpanExporter = getattr(_txe, "OTLPSpanExporter", type("OTLPSpanExporter", (), {}))

_inst = sys.modules.get("opentelemetry.instrumentation") or _make_pkg("opentelemetry.instrumentation")
if not hasattr(_inst, "fastapi"):
    _inst.fastapi = _make_pkg("opentelemetry.instrumentation.fastapi")
_inst.fastapi.FastAPIInstrumentor = getattr(_inst.fastapi, "FastAPIInstrumentor", type("FastAPIInstrumentor", (), {}))

_sdk_res = sys.modules.get("opentelemetry.sdk.resources") or _make_pkg("opentelemetry.sdk.resources")
_sdk_res.SERVICE_NAME = getattr(_sdk_res, "SERVICE_NAME", "test")
_sdk_res.Resource = getattr(_sdk_res, "Resource", type("Resource", (), {}))

_sdk_trace = sys.modules.get("opentelemetry.sdk.trace") or _make_pkg("opentelemetry.sdk.trace")
_sdk_trace.TracerProvider = getattr(_sdk_trace, "TracerProvider", type("TracerProvider", (), {}))

_sdk_trace_exp = sys.modules.get("opentelemetry.sdk.trace.export") or _make_pkg("opentelemetry.sdk.trace.export")
_sdk_trace_exp.BatchSpanProcessor = getattr(_sdk_trace_exp, "BatchSpanProcessor", type("BatchSpanProcessor", (), {}))

try:
    import botocore  # noqa: F401
except ImportError:
    import types
    _botocore = types.ModuleType("botocore")
    _botocore.client = types.ModuleType("botocore.client")
    _botocore.client.BaseClient = MagicMock()
    _botocore.config = types.ModuleType("botocore.config")
    _botocore.config.Config = MagicMock()
    sys.modules["botocore"] = _botocore
    sys.modules["botocore.client"] = _botocore.client
    sys.modules["botocore.config"] = _botocore.config

try:
    import langgraph.checkpoint.postgres  # noqa: F401
except ImportError:
    import types
    _lg_pg = types.ModuleType("langgraph.checkpoint.postgres")
    _lg_pg_aio = types.ModuleType("langgraph.checkpoint.postgres.aio")
    _lg_pg_aio.AsyncPostgresSaver = MagicMock()
    _lg_pg.aio = _lg_pg_aio
    sys.modules["langgraph.checkpoint.postgres"] = _lg_pg
    sys.modules["langgraph.checkpoint.postgres.aio"] = _lg_pg_aio

try:
    import openai  # noqa: F401
except ImportError:
    import types
    _openai = types.ModuleType("openai")
    _openai.AsyncOpenAI = MagicMock
    sys.modules["openai"] = _openai


# ── Fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def inmemory_checkpointer():
    """Provide LangGraph InMemorySaver for fast checkpoint testing."""
    try:
        from langgraph.checkpoint.memory import InMemorySaver
        return InMemorySaver()
    except ImportError:
        pytest.skip("langgraph InMemorySaver not available")


@pytest.fixture(scope="session")
def redis_container():
    """Provide Redis container for integration tests (requires Docker)."""
    try:
        from testcontainers.redis import RedisContainer
    except ImportError:
        pytest.skip("testcontainers not installed")

    try:
        with RedisContainer("redis:7-alpine") as redis:
            yield redis.get_connection_url()
    except Exception as e:
        pytest.fail(f"Redis container failed to start: {e}")


# ── Workflow Test Fixtures ─────────────────────────────────────────────────
# These fixtures reduce boilerplate in workflow tests by providing
# pre-configured mocks for common dependencies.

from unittest.mock import AsyncMock, MagicMock, Mock


@pytest.fixture
def mock_tool_registry():
    """Create a mocked ToolRegistry for workflow testing.

    Returns a Mock spec'd to ToolRegistry with execute method as AsyncMock.
    Usage:
        def test_workflow(self, mock_tool_registry):
            mock_tool_registry.execute.return_value = {"result": "mocked"}
            workflow = BusinessCaseGeneratorWorkflow(tool_registry=mock_tool_registry)
    """
    from value_fabric.layer4.tools.registry import ToolRegistry
    registry = Mock(spec=ToolRegistry)
    registry.execute = AsyncMock()
    return registry


@pytest.fixture
def mock_openai_response():
    """Factory fixture for creating mock AsyncOpenAI responses."""
    def _make_response(content: str = "Mock LLM content") -> MagicMock:
        """Create a mock AsyncOpenAI chat completion response."""
        mock_choice = MagicMock()
        mock_choice.message.content = content
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        return mock_response
    return _make_response


@pytest.fixture
def mock_openai_client(mock_openai_response):
    """Create a mocked AsyncOpenAI client for workflow testing.

    Returns a mock client with chat.completions.create as AsyncMock.
    Usage:
        def test_workflow(self, mock_openai_client):
            mock_openai_client.chat.completions.create.return_value = mock_openai_response("content")
            workflow = MyWorkflow(openai_client=mock_openai_client)
    """
    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = AsyncMock()
    client.chat.completions.create.return_value = mock_openai_response("Mock LLM content")
    return client


@pytest.fixture
def business_case_workflow(mock_tool_registry, mock_openai_client):
    """Create a BusinessCaseGeneratorWorkflow with mocked dependencies.

    This fixture provides a workflow instance ready for testing with
    all external calls (LLM, tools) pre-mocked.
    """
    from value_fabric.layer4.workflows.business_case import BusinessCaseGeneratorWorkflow
    return BusinessCaseGeneratorWorkflow(
        tool_registry=mock_tool_registry,
        openai_client=mock_openai_client,
    )


@pytest.fixture
def roi_calculator_workflow(mock_tool_registry):
    """Create a ROICalculatorWorkflow with mocked dependencies."""
    from value_fabric.layer4.workflows.roi_calculator import ROICalculatorWorkflow
    return ROICalculatorWorkflow(
        tool_registry=mock_tool_registry,
    )


# ── Checkpoint/Resume Test Fixtures ─────────────────────────────────────────
# These fixtures reduce duplication in test_checkpoint_resume.py

from datetime import UTC, datetime
from typing import Any

import pytest_asyncio
from langgraph.checkpoint.memory import InMemorySaver

from value_fabric.layer4.engine.executor import OrchestrationController
from value_fabric.layer4.engine.state_manager import StateManager
from value_fabric.layer4.models.agent_state import BaseAgentState, WorkflowStatus

TEST_WORKFLOW_TYPE = "roi_calculator"


class MockCheckpointSaver(InMemorySaver):
    """Mock checkpoint saver extending InMemorySaver for testing.

    InMemorySaver provides full BaseCheckpointSaver implementation
    with in-memory storage - perfect for testing without Postgres.
    """

    @property
    def checkpoints(self) -> dict[str, Any]:
        """Expose underlying storage for test assertions."""
        return getattr(self, 'storage', {})

    @property
    def saved_threads(self) -> set:
        """Expose saved thread IDs for test assertions."""
        return set(self.checkpoints.keys())


@pytest.fixture
def mock_checkpoint_saver() -> MockCheckpointSaver:
    """Provide mock checkpoint saver."""
    return MockCheckpointSaver()


@pytest.fixture
def state_manager() -> StateManager:
    """Provide fresh StateManager instance."""
    return StateManager()


@pytest_asyncio.fixture
async def orchestrator_with_checkpoint(
    mock_tool_registry: Mock,
    mock_checkpoint_saver: MockCheckpointSaver
) -> OrchestrationController:
    """Provide OrchestrationController with checkpointing enabled."""
    state_manager = StateManager()
    controller = OrchestrationController(
        tool_registry=mock_tool_registry,
        state_manager=state_manager,
        checkpoint_saver=mock_checkpoint_saver
    )
    try:
        await controller.start()
        yield controller
    finally:
        await controller.stop()


@pytest.fixture
def controller_with_running_state(
    mock_tool_registry: Mock,
    mock_checkpoint_saver: MockCheckpointSaver,
    state_manager: StateManager
) -> tuple[OrchestrationController, str, BaseAgentState]:
    """Provide controller with pre-existing running workflow state.

    Returns:
        Tuple of (controller, workflow_id, existing_state)
    """
    workflow_id = "test-resume-wf"
    existing_state = BaseAgentState(tenant_id="test-tenant", 
        workflow_id=workflow_id,
        workflow_type=TEST_WORKFLOW_TYPE,
        status=WorkflowStatus.RUNNING,
        current_node="middle",
        input_data={"test": "data"},
        output_data={"start": {"status": "completed"}},
        errors=[]
    )

    controller = OrchestrationController(
        tool_registry=mock_tool_registry,
        state_manager=state_manager,
        checkpoint_saver=mock_checkpoint_saver
    )
    controller._workflow_metadata[workflow_id] = {
        "workflow_type": TEST_WORKFLOW_TYPE,
        "started_at": datetime.now(UTC).isoformat()
    }

    return controller, workflow_id, existing_state


@pytest.fixture
def controller_with_paused_state(
    mock_tool_registry: Mock,
    mock_checkpoint_saver: MockCheckpointSaver,
    state_manager: StateManager
) -> tuple[OrchestrationController, str, BaseAgentState]:
    """Provide controller with pre-existing paused workflow state.

    Returns:
        Tuple of (controller, workflow_id, initial_state)
    """
    workflow_id = "lifecycle-wf"
    initial_state = BaseAgentState(tenant_id="test-tenant", 
        workflow_id=workflow_id,
        workflow_type=TEST_WORKFLOW_TYPE,
        status=WorkflowStatus.PAUSED,
        current_node="middle",
        input_data={"test": "lifecycle"},
        output_data={"start": {"status": "completed"}},
        errors=[]
    )

    controller = OrchestrationController(
        tool_registry=mock_tool_registry,
        state_manager=state_manager,
        checkpoint_saver=mock_checkpoint_saver
    )
    controller._workflow_metadata[workflow_id] = {
        "workflow_type": TEST_WORKFLOW_TYPE,
        "started_at": datetime.now(UTC).isoformat()
    }

    return controller, workflow_id, initial_state


@pytest.fixture
def completed_workflow_state() -> BaseAgentState:
    """Provide a completed workflow state fixture."""
    return BaseAgentState(tenant_id="test-tenant", 
        workflow_id="completed-wf",
        workflow_type=TEST_WORKFLOW_TYPE,
        status=WorkflowStatus.COMPLETED,
        input_data={},
        output_data={},
        errors=[]
    )
