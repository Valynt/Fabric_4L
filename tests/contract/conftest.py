"""
Shared fixtures for contract tests.

Environment Variables:
    LAYER3_API_URL: Layer 3 Knowledge API base URL (default: http://localhost:8003)
    LAYER5_API_URL: Layer 5 Ground Truth API base URL (default: http://localhost:8005)
    CONTRACT_TEST_TIMEOUT: Request timeout in seconds (default: 10.0)
    CONTRACT_TEST_MODE: Set to 'mock' to use mocked fixtures (see conftest_mocked.py)

Note:
    For CI environments without running services, use conftest_mocked.py which provides
    respx-based mocked fixtures. Install test dependencies: pip install -r tests/requirements.txt
"""

import importlib.util
import os
import sys
import types
import urllib.error
import urllib.request
from collections.abc import Mapping
from importlib.machinery import ModuleSpec

import pytest
from httpx import AsyncClient


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Classify contract tests and keep schemathesis-sensitive subsets serial.

    Schemathesis-driven contract tests crash under pytest-xdist with
    ``AttributeError: 'WorkerController' object has no attribute 'workeroutput'``.
    Marking forces ``-n0`` semantics for these items even when callers pass
    ``-n auto``. See reports/TEST_COVERAGE_RUBRIC_AUDIT_2026-05-12.md §8 M0-3.
    """
    live_service_fixtures = {
        "layer1_client",
        "layer3_client",
        "layer4_client",
        "layer5_client",
        "l1_client",
        "l3_client",
        "l4_client",
        "l4_client_tenant_b",
        "l5_client",
    }
    runtime_contract_modules = {
        "test_l3_route_alias_parity.py",
        "test_layer_service_entrypoint_smoke.py",
        "test_probe_contract_shared.py",
        "test_system_route_contract.py",
        "test_journey_contracts.py",
    }

    for item in items:
        item.add_marker(pytest.mark.no_parallel)
        if item.path.name == "test_import_topology.py":
            item.add_marker(pytest.mark.contract_static_no_service)
        if (
            "runtime_contract" in item.keywords
            or item.path.name in runtime_contract_modules
            or live_service_fixtures.intersection(item.fixturenames)
        ):
            item.add_marker(pytest.mark.service_required)
        else:
            item.add_marker(pytest.mark.contract_static)


def _install_neo4j_import_shim() -> None:
    """Provide a minimal neo4j module shim for static contract collection.

    Some static contract tests import Layer 3 model modules, which transitively import
    ``value_fabric.layer3``. In lightweight CI jobs we intentionally avoid installing
    driver dependencies; this shim keeps import-time type references resolvable.
    """
    if importlib.util.find_spec("neo4j") is not None:
        return

    module = types.ModuleType("neo4j")
    module.__spec__ = ModuleSpec("neo4j", loader=None, is_package=True)
    module.AsyncDriver = object
    module.AsyncGraphDatabase = object
    module.GraphDatabase = object
    exceptions_module = types.ModuleType("neo4j.exceptions")
    exceptions_module.__spec__ = ModuleSpec("neo4j.exceptions", loader=None)
    for exc_name in (
        "ConfigurationError",
        "Neo4jError",
        "ServiceUnavailable",
        "TransientError",
        "ClientError",
        "DatabaseError",
    ):
        setattr(exceptions_module, exc_name, type(exc_name, (Exception,), {}))
    def _missing_exc(name: str):
        exc = type(name, (Exception,), {})
        setattr(exceptions_module, name, exc)
        return exc
    exceptions_module.__getattr__ = _missing_exc  # type: ignore[attr-defined]
    time_module = types.ModuleType("neo4j.time")
    time_module.__spec__ = ModuleSpec("neo4j.time", loader=None)
    time_module.Date = object
    time_module.DateTime = object
    module.exceptions = exceptions_module
    module.time = time_module
    sys.modules.setdefault("neo4j", module)
    sys.modules.setdefault("neo4j.exceptions", exceptions_module)
    sys.modules.setdefault("neo4j.time", time_module)


_install_neo4j_import_shim()


# Default API endpoints for local development
DEFAULT_LAYER3_URL = "http://localhost:8003"
DEFAULT_LAYER4_URL = "http://localhost:8004"
DEFAULT_LAYER5_URL = "http://localhost:8005"
DEFAULT_TIMEOUT = 10.0


def _get_env_url(env_var: str, default: str) -> str:
    """Get API URL from environment variable with fallback to default.

    Strips trailing slashes to ensure consistent URL construction.
    """
    url = os.getenv(env_var, default)
    return url.rstrip("/")

@pytest.fixture(autouse=True)
def _contract_service_gate(request: pytest.FixtureRequest):
    """Gate contract tests that require live services.

    Skips any test marked ``service_required`` when services are unavailable.
    ``contract_static`` tests do NOT require live services and are never gated
    here — they validate OpenAPI artifacts, schemas, and static topology.

    Note: mock mode bypasses the gate for ``service_required`` tests
    (which use live-service client fixtures).
    """
    if "contract_static_no_service" in request.keywords:
        return

    is_service_required = "service_required" in request.keywords

    if not is_service_required:
        return

    source = os.environ
    if source.get("CONTRACT_TEST_MODE", "").lower() == "mock":
        return

    _, missing_services, strict_mode = _evaluate_services_availability(source)
    if not missing_services:
        return

    if strict_mode:
        pytest.fail(
            "Contract test strict mode is enabled (CI/CONTRACT_TEST_ENFORCE/CONTRACT_TEST_STRICT) "
            f"and required services are unavailable. Missing: {missing_services}"
        )
    pytest.skip(
        "Required contract services are unavailable in local/non-strict mode. "
        f"Missing: {missing_services}"
    )

def _is_truthy(value: str | None) -> bool:
    """Return True when an environment flag is set to a truthy value."""
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_contract_test_strict_mode(env: Mapping[str, str] | None = None) -> bool:
    """Determine whether missing services should fail contract tests.

    Strict mode is enabled when any of these are true:
      - CONTRACT_TEST_ENFORCE is truthy (explicit CI contract)
      - CONTRACT_TEST_STRICT is truthy (backward-compatible alias)
      - CI is truthy
      - GITHUB_ACTIONS is truthy
    """
    source = env if env is not None else os.environ
    return any(
        _is_truthy(source.get(flag))
        for flag in ("CONTRACT_TEST_ENFORCE", "CONTRACT_TEST_STRICT", "CI", "GITHUB_ACTIONS")
    )


def _evaluate_services_availability(env: Mapping[str, str] | None = None) -> tuple[bool, list[str], bool]:
    """Check required service health endpoints and return evaluation result.

    Returns a tuple of:
      - mock_mode (whether live service checks should be bypassed)
      - missing_services (unhealthy/unreachable service health URLs)
      - strict_mode (whether missing services should fail closed)
    """
    source = env if env is not None else os.environ
    if source.get("CONTRACT_TEST_MODE", "").lower() == "mock":
        return True, [], _is_contract_test_strict_mode(source)
    urls_to_check = [
        f"{_get_env_url('LAYER3_API_URL', DEFAULT_LAYER3_URL)}/health",
        f"{_get_env_url('LAYER4_API_URL', DEFAULT_LAYER4_URL)}/health",
        f"{_get_env_url('LAYER5_API_URL', DEFAULT_LAYER5_URL)}/api/v1/health",
    ]

    missing_services = []
    for url in urls_to_check:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status != 200:
                    missing_services.append(url)
        except (urllib.error.URLError, ConnectionError):
            missing_services.append(url)

    return False, missing_services, _is_contract_test_strict_mode(source)


@pytest.fixture(scope="session", autouse=True)
def check_services_availability(request: pytest.FixtureRequest):
    """Check if required services are running, otherwise skip tests.
    Prevents massive traceback dumps when backend infrastructure is missing.
    """
    if request.session.items:
        # If the session contains no service-required tests, never skip here —
        # static contract tests (contract_static / contract_static_no_service)
        # validate OpenAPI artifacts and do not need live backends.
        has_service_required = any(
            "service_required" in item.keywords for item in request.session.items
        )
        if not has_service_required:
            return

    mock_mode, missing_services, strict_mode = _evaluate_services_availability()
    if mock_mode:
        return

    if missing_services:
        if strict_mode:
            pytest.fail(
                "Contract test strict mode is enabled (CI/CONTRACT_TEST_ENFORCE/CONTRACT_TEST_STRICT) "
                f"and required services are unavailable. Missing: {missing_services}"
            )
        pytest.skip(
            "Required contract services are unavailable in local/non-strict mode. "
            f"Missing: {missing_services}"
        )


def _skip_if_services_unavailable(service_urls: list[str]) -> None:
    """Skip the current test if any of the given service URLs are unreachable.

    Used by client fixtures to guard individual tests when the session-level
    skip did not fire (e.g. because env vars were mutated after session start).
    """
    for url in service_urls:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status != 200:
                    pytest.skip(f"Service unavailable: {url} returned HTTP {response.status}")
        except (urllib.error.URLError, ConnectionError, OSError):
            pytest.skip(f"Service unreachable: {url}")


@pytest.fixture
async def client() -> AsyncClient:
    """Create HTTP client for Layer 3 API contract tests.

    Uses LAYER3_API_URL environment variable, falls back to localhost:8003.
    Skips the test if the service is unreachable (guards against env var mutation
    after the session-level availability check has already run).
    """
    base_url = _get_env_url("LAYER3_API_URL", DEFAULT_LAYER3_URL)
    _skip_if_services_unavailable([f"{base_url}/health"])
    timeout = float(os.getenv("CONTRACT_TEST_TIMEOUT", DEFAULT_TIMEOUT))

    async with AsyncClient(base_url=base_url, timeout=timeout) as client:
        yield client


@pytest.fixture
async def layer4_client() -> AsyncClient:
    """Create HTTP client for Layer 4 Agents API tests.

    Uses LAYER4_API_URL environment variable, falls back to localhost:8004.
    Skips the test if the service is unreachable.
    """
    base_url = _get_env_url("LAYER4_API_URL", DEFAULT_LAYER4_URL)
    _skip_if_services_unavailable([f"{base_url}/health"])
    timeout = float(os.getenv("CONTRACT_TEST_TIMEOUT", DEFAULT_TIMEOUT))

    async with AsyncClient(base_url=base_url, timeout=timeout) as client:
        yield client


@pytest.fixture
async def layer5_client() -> AsyncClient:
    """Create HTTP client for Layer 5 Ground Truth API tests.

    Uses LAYER5_API_URL environment variable, falls back to localhost:8005.
    Skips the test if the service is unreachable.
    """
    base_url = _get_env_url("LAYER5_API_URL", DEFAULT_LAYER5_URL)
    _skip_if_services_unavailable([f"{base_url}/api/v1/health"])
    timeout = float(os.getenv("CONTRACT_TEST_TIMEOUT", DEFAULT_TIMEOUT))

    async with AsyncClient(base_url=base_url, timeout=timeout) as client:
        yield client
