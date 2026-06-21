"""Repository-level pytest bootstrap kept out of root conftest.py."""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import types
import warnings
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_TEST_ENV = {
    "ENVIRONMENT": "development",
    "LAYER1_API_URL": "http://layer1:8001",
    "LAYER2_API_URL": "http://layer2:8002",
    "LAYER3_API_URL": "http://layer3:8003",
    "LAYER5_API_URL": "http://layer5:8005",
    "LAYER6_API_URL": "http://layer6:8006",
    "ALLOW_INSECURE_SERVICE_HTTP_IN_DEVELOPMENT": "true",
    "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@localhost:5432/fabric",
    "JWT_SECRET": "dummy_jwt_secret_for_tests_must_be_32_chars",
    "API_KEY_HMAC_SECRET": "dummy_api_key_secret_for_tests_must_be_32_chars",
    "SERVICE_AUTH_SECRET": "dummy_service_auth_secret_for_tests_32_chars",
}

_FAIL_CLOSED_TEST_DEFAULTS = {
    "DATABASE_URL_SYNC": "postgresql+psycopg://postgres:postgres@localhost:5432/fabric",
    "NEO4J_URI": "bolt://localhost:7687",
    "NEO4J_PASSWORD": "neo4j-test-password-123",
    "LAYER3_API_KEY": "layer3-test-api-key-0123456789",
    "LAYER5_API_KEY": "layer5-test-api-key-0123456789",
}

_SERVICE_SRC_PATHS = (
    "packages/shared/src",
    "services/layer2-extraction/src",
    "services/layer3-knowledge/src",
    "services/layer1-ingestion/src",
    "services/layer5-ground-truth/src",
    "services/layer6-benchmarks/src",
    "services/layer7-billing/src",
)


def bootstrap_root_pytest() -> None:
    """Install root test env, import paths, and legacy source namespaces."""
    _install_test_environment()
    _install_service_paths()
    _install_legacy_src_namespace()
    _preimport_layer4_compat_modules()


def _install_test_environment() -> None:
    for key, value in _TEST_ENV.items():
        os.environ[key] = value
    for key, value in _FAIL_CLOSED_TEST_DEFAULTS.items():
        os.environ.setdefault(key, value)


def _install_service_paths() -> None:
    for rel_path in _SERVICE_SRC_PATHS:
        _prepend_existing_path(REPO_ROOT / rel_path)


def _prepend_existing_path(path: Path) -> None:
    path_str = str(path)
    if path.exists() and path_str not in sys.path:
        sys.path.insert(0, path_str)


def _ensure_namespace(name: str, paths: list[Path]) -> None:
    module = sys.modules.get(name)
    if module is None or not hasattr(module, "__path__"):
        module = types.ModuleType(name)
        module.__file__ = str(REPO_ROOT / "<legacy-src-namespace>")
        module.__package__ = name
        module.__path__ = []
        sys.modules[name] = module
    for path in paths:
        if path.exists():
            value = str(path)
            if value not in module.__path__:
                module.__path__.append(value)


def _install_legacy_src_namespace() -> None:
    layer4 = REPO_ROOT / "services" / "layer4-agents" / "src"
    layer3 = REPO_ROOT / "services" / "layer3-knowledge" / "src"
    _ensure_namespace("src", [layer4, layer3])
    _ensure_namespace("src.api", [layer4 / "api", layer3 / "api"])
    _ensure_namespace("src.api.routes", [layer4 / "api" / "routes", layer3 / "api" / "routes"])
    _ensure_namespace("src.services", [layer4 / "services", layer3 / "services"])
    _ensure_namespace("src.engine", [layer4 / "engine"])
    _ensure_namespace("src.tools", [layer4 / "tools"])
    _ensure_namespace("src.workflows", [layer4 / "workflows"])
    _ensure_namespace("src.api.websocket", [layer4 / "api" / "websocket"])
    _bind_leaf_package("src.config", layer3 / "config")


def _bind_leaf_package(module_name: str, package_dir: Path) -> None:
    init_file = package_dir / "__init__.py"
    existing = sys.modules.get(module_name)
    if existing is not None and str(package_dir) in (getattr(existing, "__file__", "") or ""):
        return
    if not init_file.exists():
        return
    spec = importlib.util.spec_from_file_location(
        module_name,
        init_file,
        submodule_search_locations=[str(package_dir)],
    )
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)


def _preimport_layer4_compat_modules() -> None:
    try:
        for module_name in ("src.database", "src.models", "src.models.account", "src.models.billing"):
            importlib.import_module(module_name)
    except Exception as exc:
        warnings.warn(
            "Root pytest bootstrap could not pre-import Layer 4 compatibility modules; "
            "collection will continue and surface import errors from the affected tests. "
            f"Original error: {exc!r}",
            RuntimeWarning,
            stacklevel=2,
        )
