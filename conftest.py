"""Root conftest.py for Fabric 4L monorepo.

Ensures sys.path is set up before pytest imports any test modules.
Only adds the shared package path. Layer test directories are expected
to add their own src paths in their local conftest.py files.

Also enforces mandatory test dependencies at collection time so that
missing packages produce an immediate, actionable error rather than
silently skipping tests.
"""

import importlib.util
import os
os.environ["ENVIRONMENT"] = "development"
os.environ["ALLOW_DEV_AUTH_BYPASS"] = "I_UNDERSTAND_RISK"
os.environ["LAYER1_API_URL"] = "http://layer1:8001"
os.environ["LAYER2_API_URL"] = "http://layer2:8002"
os.environ["LAYER3_API_URL"] = "http://layer3:8003"
os.environ["LAYER5_API_URL"] = "http://layer5:8005"
os.environ["LAYER6_API_URL"] = "http://layer6:8006"
os.environ["ALLOW_INSECURE_SERVICE_HTTP_IN_DEVELOPMENT"] = "true"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/fabric"
os.environ["JWT_SECRET"] = "dummy_jwt_secret_for_tests_must_be_32_chars"
os.environ["API_KEY_HMAC_SECRET"] = "dummy_api_key_secret_for_tests_must_be_32_chars"
os.environ["SERVICE_AUTH_SECRET"] = "dummy_service_auth_secret_for_tests_32_chars"

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.resolve()

# Shared package (canonical location)
_SHARED_SRC = _REPO_ROOT / "packages" / "shared" / "src"
if _SHARED_SRC.exists() and str(_SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(_SHARED_SRC))

# Non-ambiguous top-level service package roots needed by repository-level
# contract tests.  Do not add every service ``src`` root here because several
# services contain a top-level package named ``src``; those remain service-local
# through their own conftest.py files.
_LAYER2_SRC = _REPO_ROOT / "services" / "layer2-extraction" / "src"
if _LAYER2_SRC.exists() and str(_LAYER2_SRC) not in sys.path:
    sys.path.insert(0, str(_LAYER2_SRC))

# Layer 3 src root is required so that intra-package bare imports inside
# services/layer3-knowledge/src (e.g. ``from api.dependencies import ...``)
# resolve correctly when tests import via the value_fabric.layer3 shim.
# Added to sys.path (not as a src.* namespace entry) to avoid the namespace
# collision documented below.
_LAYER3_SRC = _REPO_ROOT / "services" / "layer3-knowledge" / "src"
if _LAYER3_SRC.exists() and str(_LAYER3_SRC) not in sys.path:
    sys.path.insert(0, str(_LAYER3_SRC))


def _install_legacy_src_namespace() -> None:
    """Expose legacy ``src.*`` imports deterministically for repo collection.

    Historical Layer 3 and Layer 4 tests import modules through a top-level
    ``src`` package.  Both services contain overlapping parents such as
    ``src.api.routes``; importing one service's real ``__init__`` can therefore
    hide the other service or run unrelated side effects during collection.  The
    production test profile installs lightweight namespace packages for those
    parents and points them at the real module directories.
    """
    import types

    def namespace(name: str, paths: list[Path]) -> None:
        module = sys.modules.get(name)
        if module is None or not hasattr(module, "__path__"):
            module = types.ModuleType(name)
            module.__file__ = str(_REPO_ROOT / "<legacy-src-namespace>")
            module.__package__ = name
            module.__path__ = []
            sys.modules[name] = module
        for path in paths:
            if path.exists():
                value = str(path)
                if value not in module.__path__:
                    module.__path__.append(value)

    layer4 = _REPO_ROOT / "services" / "layer4-agents" / "src"
    layer3 = _REPO_ROOT / "services" / "layer3-knowledge" / "src"
    namespace("src", [layer4, layer3])
    namespace("src.api", [layer4 / "api", layer3 / "api"])
    namespace("src.api.routes", [layer4 / "api" / "routes", layer3 / "api" / "routes"])
    namespace("src.services", [layer4 / "services"])
    namespace("src.engine", [layer4 / "engine"])
    namespace("src.tools", [layer4 / "tools"])
    namespace("src.workflows", [layer4 / "workflows"])


_install_legacy_src_namespace()

# Import core Layer 4 dependency modules after the legacy namespace is installed.
# Several legacy tests add collection-time mocks only when these names are absent;
# pre-importing the real modules prevents those mocks from poisoning later FastAPI
# route collection under the repository-level production profile.
try:
    import importlib

    for module_name in ("src.database", "src.models", "src.models.account", "src.models.billing"):
        importlib.import_module(module_name)
except Exception:
    # The mandatory profile still fails closed on real collection/import errors;
    # this guard only avoids making the root bootstrap itself unimportable before
    # pytest can render a useful diagnostic.
    pass


# ---------------------------------------------------------------------------
# Mandatory dependency enforcement
#
# These packages must be present for the mandatory test profile to run.
# They are listed in each service's [project.optional-dependencies.dev].
# A missing package here means the dev environment was not set up correctly.
#
# Optional/slow deps (playwright, pymupdf4llm) are NOT listed here — their
# test files use pytest.mark.skipif so they are collected but skipped cleanly.
# ---------------------------------------------------------------------------

# Maps import name → install instruction
_MANDATORY_DEPS: dict[str, str] = {
    # Layer 1 — HTTP mocking and async HTTP test clients
    "respx": "pip install 'respx>=0.21'  (layer1-ingestion[dev] or tests/requirements-test.txt)",
    "aiohttp": "pip install 'aiohttp>=3.9'  (tests/requirements-test.txt)",
    # Layer 1 — content extraction (already a production dep)
    "trafilatura": "pip install 'trafilatura>=1.6'  (layer1-ingestion dependency)",
    # Layer 1 — XXE-safe XML (already a production dep)
    "defusedxml": "pip install 'defusedxml>=0.7'  (layer1-ingestion dependency)",
    "pymupdf4llm": "pip install 'pymupdf4llm>=0.0.17'  (layer1-ingestion dependency)",
    "pytesseract": "pip install 'pytesseract>=0.3.13'  (layer1-ingestion dependency)",
    "selectolax": "pip install 'selectolax>=0.3'  (layer1-ingestion dependency)",
    # Layer 3 — graph and RDF collection-time dependencies
    "rdflib": "pip install 'rdflib>=7.0'  (layer3-knowledge dependency)",
    "neo4j": "pip install 'neo4j>=5.15'  (layer3-knowledge dependency)",
    # Layer 4 — PostgreSQL driver for testcontainers integration tests
    "psycopg": "pip install 'psycopg[binary]>=3.1'  (layer4-agents[dev])",
    # Layer 4 — pydantic email validation
    "email_validator": "pip install 'email-validator>=2.1'  (layer4-agents[dev])",
    # Shared identity — JWT library (already a production dep in layer4)
    "jose": "pip install 'python-jose[cryptography]>=3.3'  (layer4-agents dependency)",
    "jsonschema": "pip install 'jsonschema>=4.23'  (tests/requirements-test.txt)",
}


def pytest_configure(config) -> None:
    """Fail fast when mandatory test dependencies are missing.

    Runs before collection so the error is immediate and unambiguous,
    rather than surfacing as a cryptic ImportError mid-collection.

    Automatically bypassed during --collect-only so test inventory works
    from a clean checkout.  Use --no-mandatory-dep-check for other
    lightweight collection scenarios.
    """
    if getattr(config.option, "no_mandatory_dep_check", False):
        return

    if getattr(config.option, "collectonly", False):
        return

    missing = [
        (name, hint)
        for name, hint in _MANDATORY_DEPS.items()
        if importlib.util.find_spec(name) is None
    ]

    if not missing:
        return

    lines = ["", "Mandatory test dependencies are missing.", ""]
    for name, hint in missing:
        lines.append(f"  \u2717 {name}")
        lines.append(f"    \u2192 {hint}")
    lines += [
        "",
        "Install all mandatory deps for the full mandatory profile:",
        "  pip install -r tests/requirements-test.txt",
        "",
        "To skip this check (e.g. for a dry-run collection audit):",
        "  pytest --no-mandatory-dep-check --collect-only",
        "",
    ]
    raise SystemExit("\n".join(lines))


def pytest_addoption(parser) -> None:
    """Add --no-mandatory-dep-check flag for lightweight collection runs."""
    parser.addoption(
        "--no-mandatory-dep-check",
        action="store_true",
        default=False,
        dest="no_mandatory_dep_check",
        help="Skip mandatory dependency enforcement (for --collect-only dry runs).",
    )


def pytest_collection_modifyitems(config, items) -> None:
    """Automatically mark tests as mandatory based on their other markers.

    Tests marked with: unit, contract, security, or tenant_boundary
    are automatically considered mandatory unless they also have:
    - slow
    - requires_postgres
    - requires_redis
    - requires_neo4j
    - requires_openai
    - e2e
    - integration
    - performance

    This allows selecting mandatory tests with: pytest -m mandatory
    """
    mandatory_markers = {"unit", "contract", "security", "tenant_boundary"}
    exclusion_markers = {
        "slow", "requires_postgres", "requires_redis", "requires_neo4j",
        "requires_docker", "requires_openai", "e2e", "integration", "performance",
        "flaky", "quarantine"
    }

    for item in items:
        item_markers = {m.name for m in item.iter_markers()}

        # Skip if already has mandatory marker
        if "mandatory" in item_markers:
            continue

        # Skip if has any exclusion marker
        if item_markers & exclusion_markers:
            continue

        # Mark as mandatory if it has any mandatory marker
        if item_markers & mandatory_markers:
            item.add_marker("mandatory")


# ---------------------------------------------------------------------------
# Repository-level collection compatibility
#
# Some Layer 3 tests historically used ``from conftest import ...``.  During
# repository-level collection pytest resolves that import to this root module,
# not necessarily the service-local conftest.  Expose the helper interfaces here
# so collection is deterministic while those imports are normalized over time.
# ---------------------------------------------------------------------------

from typing import Any
from unittest.mock import AsyncMock


def create_mock_graphrag_response() -> AsyncMock:
    """Create a mock GraphRAG response matching the Layer 3 helper."""
    mock = AsyncMock()
    mock.query.return_value = {
        "entities": [{"id": "test_entity", "type": "Capability", "name": "Test"}],
        "relationships": [{"source": "test", "target": "entity", "type": "has"}],
        "context_graph": {"nodes": 1, "edges": 0},
        "confidence_score": 0.8,
        "sources": ["test_entity"],
        "processing_time_ms": 100.0,
    }
    return mock


def create_mock_search_response() -> AsyncMock:
    """Create a mock search response matching the Layer 3 helper."""
    mock = AsyncMock()
    mock.search.return_value = {
        "results": [
            {
                "entity_id": "test_entity",
                "entity_type": "Capability",
                "name": "Test Capability",
                "bm25_score": 0.7,
                "vector_score": 0.8,
                "graph_score": 0.6,
                "combined_score": 0.7,
                "metadata": {},
                "confidence": 0.75,
            }
        ],
        "total_results": 1,
        "search_type": "hybrid",
        "processing_time_ms": 50.0,
    }
    return mock


class TestUtils:
    """Layer 3 response-shape assertions used by legacy bare imports."""

    @staticmethod
    def assert_valid_health_response(response_data: dict[str, Any]) -> None:
        assert "status" in response_data
        assert "version" in response_data
        assert "timestamp" in response_data
        assert "uptime_seconds" in response_data
        assert "dependencies" in response_data
        assert "metrics" in response_data
        assert "neo4j" in response_data
        assert "schema_status" in response_data
        assert response_data["status"] in ["healthy", "unhealthy", "degraded"]
        assert isinstance(response_data["uptime_seconds"], (int, float))
        assert response_data["uptime_seconds"] >= 0

    @staticmethod
    def assert_valid_search_response(response_data: dict[str, Any]) -> None:
        assert "query" in response_data
        assert "results" in response_data
        assert "total_results" in response_data
        assert "search_type" in response_data
        assert isinstance(response_data["results"], list)
        assert isinstance(response_data["total_results"], int)
        assert response_data["total_results"] >= 0
        if response_data["results"]:
            result = response_data["results"][0]
            assert "entity_id" in result
            assert "entity_type" in result
            assert "name" in result
            assert "combined_score" in result
            assert "confidence" in result

    @staticmethod
    def assert_valid_graphrag_response(response_data: dict[str, Any]) -> None:
        assert "query" in response_data
        assert "entities" in response_data
        assert "relationships" in response_data
        assert "context_graph" in response_data
        assert "confidence_score" in response_data
        assert "sources" in response_data
        assert isinstance(response_data["entities"], list)
        assert isinstance(response_data["relationships"], list)
        assert isinstance(response_data["sources"], list)
        assert isinstance(response_data["confidence_score"], (int, float))
        assert 0 <= response_data["confidence_score"] <= 1

    @staticmethod
    def assert_valid_ingestion_response(response_data: dict[str, Any]) -> None:
        assert "status" in response_data
        assert "source_id" in response_data
        assert "entities_loaded" in response_data
        assert "relationships_loaded" in response_data
        assert "triples_processed" in response_data
        assert response_data["status"] in ["success", "partial", "failed"]
        assert isinstance(response_data["entities_loaded"], int)
        assert isinstance(response_data["relationships_loaded"], int)
        assert isinstance(response_data["triples_processed"], int)
        assert all(
            count >= 0
            for count in [
                response_data["entities_loaded"],
                response_data["relationships_loaded"],
                response_data["triples_processed"],
            ]
        )
