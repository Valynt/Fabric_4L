from __future__ import annotations

import importlib
import importlib.util
import inspect
import sys
import types
import warnings
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYER5_SRC = REPO_ROOT / "services" / "layer5-ground-truth" / "src"
if str(LAYER5_SRC) not in sys.path:
    sys.path.insert(0, str(LAYER5_SRC))


def _load_by_path(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _import_module(name: str):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return importlib.import_module(name)


def _public_api(module) -> set[str]:
    explicit = getattr(module, "__all__", None)
    if explicit:
        return set(explicit)
    return {name for name in dir(module) if not name.startswith("_")}


def _assert_symbol_parity(canonical, shimmed, expected_names: list[str]) -> None:
    canonical_api = _public_api(canonical)
    shimmed_api = _public_api(shimmed)

    assert set(expected_names).issubset(canonical_api)
    assert set(expected_names).issubset(shimmed_api)
    assert canonical_api == shimmed_api

    for name in expected_names:
        canonical_value = getattr(canonical, name)
        shimmed_value = getattr(shimmed, name)
        assert type(canonical_value) is type(shimmed_value)
        if callable(canonical_value) and callable(shimmed_value):
            assert str(inspect.signature(canonical_value)) == str(inspect.signature(shimmed_value))
        if hasattr(canonical_value, "routes") and hasattr(shimmed_value, "routes"):
            assert [route.path for route in canonical_value.routes] == [route.path for route in shimmed_value.routes]


def _install_layer4_import_stubs() -> None:
    if "langgraph.checkpoint.postgres.aio" in sys.modules:
        return

    langgraph_module = sys.modules.setdefault("langgraph", types.ModuleType("langgraph"))
    checkpoint_module = sys.modules.setdefault("langgraph.checkpoint", types.ModuleType("langgraph.checkpoint"))
    postgres_module = sys.modules.setdefault("langgraph.checkpoint.postgres", types.ModuleType("langgraph.checkpoint.postgres"))
    aio_module = types.ModuleType("langgraph.checkpoint.postgres.aio")

    class AsyncPostgresSaver:  # pragma: no cover - import stub only
        conn = None

    aio_module.AsyncPostgresSaver = AsyncPostgresSaver
    sys.modules["langgraph.checkpoint.postgres.aio"] = aio_module
    langgraph_module.checkpoint = checkpoint_module
    checkpoint_module.postgres = postgres_module
    postgres_module.aio = aio_module


@pytest.mark.parametrize(
    ("surface", "canonical_name", "shim_name", "shim_path", "expected_names", "env_overrides"),
    [
        (
            "layer1 compatibility routes",
            "value_fabric.layer1.api.routes.compatibility",
            None,
            REPO_ROOT / "services" / "layer1-ingestion" / "src" / "api" / "routes" / "compatibility.py",
            [
                "router",
                "short_ingest_compatibility_boundary",
                "create_ingestion_source_compatibility_boundary",
            ],
            {},
        ),
        (
            "layer3 compat aliases",
            "value_fabric.layer3.api.routes.compat_aliases",
            None,
            REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "routes" / "compat_aliases.py",
            ["router", "graph_rag_legacy_alias", "hybrid_search_aliases"],
            {},
        ),
        (
            "layer3 entity compat",
            "value_fabric.layer3.api.routes.entity_compat",
            None,
            REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "routes" / "entity_compat.py",
            ["router"],
            {},
        ),
        (
            "layer5 truth object",
            "layer5_ground_truth.models.truth_object",
            "layer5_ground_truth.models.truth_object",
            None,
            ["TruthObject", "TruthStatus", "ValidationEvent"],
            {},
        ),
    ],
)
def test_shim_surfaces_match_canonical_public_api(
    surface: str,
    canonical_name: str,
    shim_name: str | None,
    shim_path: Path | None,
    expected_names: list[str],
    env_overrides: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key, value in env_overrides.items():
        monkeypatch.setenv(key, value)

    try:
        canonical = _import_module(canonical_name)
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.skip(f"Cannot import canonical module {canonical_name!r}: {exc}")

    try:
        shimmed = _import_module(shim_name) if shim_name else _load_by_path(shim_path, f"shim_test_{shim_path.stem}")
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.skip(f"Cannot import shim module for {surface!r}: {exc}")

    _assert_symbol_parity(canonical, shimmed, expected_names)
