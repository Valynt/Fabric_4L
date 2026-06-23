"""Tests for API versioning registration validation and startup behavior."""

from unittest.mock import AsyncMock

import pytest

from src.api import main as main_module
from src.api import versioning as versioning_module
from src.api.versioning import VersionCompatibility
from value_fabric.shared.models.typed_dict import TypedDictModel


class incompatible_handlerResult(TypedDictModel):
    pass

class async_handlerResult(TypedDictModel):
    migrated: bool | None = None
    migrated_sync: bool | None = None


def test_register_migration_handler_accepts_valid_callable() -> None:
    compatibility = VersionCompatibility(current_version="v1")

    def valid_handler(data: dict) -> dict:
        return data

    compatibility.register_migration_handler("v1", "v2", valid_handler)

    assert "v1->v2" in compatibility.migration_handlers
    assert compatibility.migration_handlers["v1->v2"][0] is valid_handler


def test_register_migration_handler_accepts_migration_handler_keyword_alias() -> None:
    compatibility = VersionCompatibility(current_version="v1")

    def valid_handler(data: dict) -> dict:
        return data

    compatibility.register_migration_handler("v1", "v2", migration_handler=valid_handler)

    assert "v1->v2" in compatibility.migration_handlers
    assert compatibility.migration_handlers["v1->v2"][0] is valid_handler


def test_register_migration_handler_rejects_non_callable() -> None:
    compatibility = VersionCompatibility(current_version="v1")

    with pytest.raises(TypeError, match="must implement Callable"):
        compatibility.register_migration_handler("v1", "v2", "not-callable")  # type: ignore[arg-type]


def test_register_migration_handler_rejects_incompatible_signature() -> None:
    compatibility = VersionCompatibility(current_version="v1")

    def incompatible_handler(data: dict, extra: dict) -> dict:
        return incompatible_handlerResult.model_validate({**data, **extra})

    with pytest.raises(TypeError, match="callable signature"):
        compatibility.register_migration_handler("v1", "v2", incompatible_handler)


@pytest.fixture
def _patch_lifespan_deps(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent lifespan from loading heavy optional dependencies during unit tests."""
    monkeypatch.setattr(
        "src.retrieval.vector_store.Neo4jVectorStore._get_embedding_model",
        lambda self: None,
    )


@pytest.mark.asyncio
async def test_startup_fails_with_descriptive_error_for_bad_migration_handler(
    monkeypatch: pytest.MonkeyPatch,
    _patch_lifespan_deps: None,
) -> None:
    monkeypatch.setattr(main_module, "init_app_state", AsyncMock(return_value=None))
    monkeypatch.setattr(main_module, "close_app_state", AsyncMock(return_value=None))
    monkeypatch.setattr(versioning_module, "migrate_v1_to_v2_search_request", "not-callable")

    with pytest.raises(TypeError, match="got str"):
        async with main_module.lifespan(main_module.app):
            pass


@pytest.mark.asyncio
async def test_startup_registers_versioning_handlers_successfully(
    monkeypatch: pytest.MonkeyPatch,
    _patch_lifespan_deps: None,
) -> None:
    monkeypatch.setattr(main_module, "init_app_state", AsyncMock(return_value=None))
    monkeypatch.setattr(main_module, "close_app_state", AsyncMock(return_value=None))

    async with main_module.lifespan(main_module.app):
        assert hasattr(main_module.app.state, "version_compatibility")
        compatibility = main_module.app.state.version_compatibility
        assert "v1->v2" in compatibility.migration_handlers
        assert len(compatibility.migration_handlers["v1->v2"]) >= 2


@pytest.mark.asyncio
async def test_migrate_request_data_async_supports_async_handler() -> None:
    compatibility = VersionCompatibility(current_version="v1")

    async def async_handler(data: dict) -> dict:
        return async_handlerResult.model_validate({**data, "migrated": True})

    compatibility.register_migration_handler("v1", "v2", async_handler)

    result = await compatibility.migrate_request_data_async({"k": "v"}, "v1", "v2")

    assert result["k"] == "v"
    assert result["migrated"] is True


@pytest.mark.asyncio
async def test_migrate_request_data_supports_async_handler_from_sync_context() -> None:
    compatibility = VersionCompatibility(current_version="v1")

    async def async_handler(data: dict) -> dict:
        return async_handlerResult.model_validate({**data, "migrated_sync": True})

    compatibility.register_migration_handler("v1", "v2", async_handler)

    result = await compatibility.migrate_request_data({"k": "v"}, "v1", "v2")

    assert result["k"] == "v"
    assert result["migrated_sync"] is True

