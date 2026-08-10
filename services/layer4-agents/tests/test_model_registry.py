from __future__ import annotations

"""Unit tests for the Model Registry service and evaluation gate."""


import os
import sys
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from layer4_agents.registry.eval_gate import _DEFAULT_PROMOTION_THRESHOLD, check_eval_gate
from layer4_agents.registry.models import ModelPromotionLog, ModelVersion
from layer4_agents.registry.service import ModelRegistryService, PromotionError, resolve_llm_model


class FakeResult:
    """Helper to mock SQLAlchemy query results."""

    def __init__(self, scalar: Any = None) -> None:
        self._scalar = scalar

    def scalar_one_or_none(self) -> Any:
        return self._scalar

    def scalars(self) -> Any:
        class _All:
            def __init__(self, items: list) -> None:
                self._items = items
            def all(self) -> list:
                return self._items
        return _All(self._scalar if isinstance(self._scalar, list) else [])


@pytest.fixture
def tenant_id() -> UUID:
    return uuid4()


@pytest.fixture
def db() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_emit_audit_event(monkeypatch):
    """Mock emit_audit_event to accept any arguments."""
    from unittest.mock import MagicMock
    mock = MagicMock()
    monkeypatch.setattr("layer4_agents.registry.service.emit_audit_event", mock)
    return mock


class TestModelRegistryCRUD:
    """Tests for model registration and listing."""

    @pytest.mark.asyncio
    async def test_register_model(self, db: AsyncMock, tenant_id: UUID, mock_emit_audit_event) -> None:
        model = await ModelRegistryService.register_model(
            db=db,
            tenant_id=tenant_id,
            provider="openai",
            model_name="gpt-4o",
            model_version="2024-05",
            eval_score=0.92,
        )
        assert model.provider == "openai"
        assert model.model_name == "gpt-4o"
        assert model.stage == "dev"
        db.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_list_models(self, db: AsyncMock, tenant_id: UUID) -> None:
        mv = ModelVersion(
            tenant_id=tenant_id,
            provider="openai",
            model_name="gpt-4o",
            model_version="v1",
            stage="production",
        )
        db.execute.return_value = FakeResult([mv])
        results = await ModelRegistryService.list_models(db, tenant_id)
        assert len(results) == 1
        assert results[0].stage == "production"

    @pytest.mark.asyncio
    async def test_get_active_production_model(self, db: AsyncMock, tenant_id: UUID) -> None:
        mv = ModelVersion(
            tenant_id=tenant_id,
            provider="openai",
            model_name="gpt-4o",
            model_version="v1",
            stage="production",
        )
        db.execute.return_value = FakeResult(mv)
        result = await ModelRegistryService.get_active_production_model(
            db, tenant_id, "openai"
        )
        assert result is not None
        assert result.stage == "production"

    @pytest.mark.asyncio
    async def test_get_active_production_model_none(self, db: AsyncMock, tenant_id: UUID) -> None:
        db.execute.return_value = FakeResult(None)
        result = await ModelRegistryService.get_active_production_model(
            db, tenant_id, "openai"
        )
        assert result is None


class TestModelPromotion:
    """Tests for promotion gates and audit trail."""

    @pytest.mark.asyncio
    async def test_dev_to_staging_allowed(self, db: AsyncMock, tenant_id: UUID, mock_emit_audit_event) -> None:
        mv = ModelVersion(
            id=uuid4(),
            tenant_id=tenant_id,
            provider="openai",
            model_name="gpt-4o",
            model_version="v1",
            stage="dev",
        )
        db.execute.side_effect = [FakeResult(mv), FakeResult(None)]
        result = await ModelRegistryService.promote_model(
            db, mv.id, "staging", reason="dev complete"
        )
        assert result.stage == "staging"

    @pytest.mark.asyncio
    async def test_staging_to_production_requires_eval(self, db: AsyncMock, tenant_id: UUID, mock_emit_audit_event) -> None:
        mv = ModelVersion(
            id=uuid4(),
            tenant_id=tenant_id,
            provider="openai",
            model_name="gpt-4o",
            model_version="v1",
            stage="staging",
            eval_score=0.80,
        )
        # Mock tenant for threshold lookup
        from layer4_agents.tenants.models.tenant import Tenant
        tenant = Tenant(id=tenant_id, name="Test", slug="test", settings={}, status="active")

        # promote_model does 1 execute, then check_eval_gate does 2 executes
        db.execute.side_effect = [FakeResult(mv), FakeResult(mv), FakeResult(tenant)]
        with pytest.raises(PromotionError) as exc_info:
            await ModelRegistryService.promote_model(db, mv.id, "production")
        assert "gate failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_staging_to_production_passes_with_high_score(
        self, db: AsyncMock, tenant_id: UUID, mock_emit_audit_event
    ) -> None:
        mv = ModelVersion(
            id=uuid4(),
            tenant_id=tenant_id,
            provider="openai",
            model_name="gpt-4o",
            model_version="v1",
            stage="staging",
            eval_score=0.95,
        )
        from layer4_agents.tenants.models.tenant import Tenant
        tenant = Tenant(id=tenant_id, name="Test", slug="test", settings={}, status="active")

        # promote_model: 1 execute + check_eval_gate (2 executes) first call
        # + check_eval_gate (2 executes) second call in eval_gate_passed expression
        db.execute.side_effect = [
            FakeResult(mv), FakeResult(mv), FakeResult(tenant),
            FakeResult(mv), FakeResult(tenant),
        ]
        result = await ModelRegistryService.promote_model(db, mv.id, "production")
        assert result.stage == "production"

    @pytest.mark.asyncio
    async def test_production_to_deprecated_allowed(self, db: AsyncMock, tenant_id: UUID, mock_emit_audit_event) -> None:
        mv = ModelVersion(
            id=uuid4(),
            tenant_id=tenant_id,
            provider="openai",
            model_name="gpt-4o",
            model_version="v1",
            stage="production",
        )
        db.execute.side_effect = [FakeResult(mv), FakeResult(None)]
        result = await ModelRegistryService.promote_model(
            db, mv.id, "deprecated", reason="old version"
        )
        assert result.stage == "deprecated"

    @pytest.mark.asyncio
    async def test_promotion_history_recorded(self, db: AsyncMock, tenant_id: UUID, mock_emit_audit_event) -> None:
        mv = ModelVersion(
            id=uuid4(),
            tenant_id=tenant_id,
            provider="openai",
            model_name="gpt-4o",
            model_version="v1",
            stage="dev",
        )
        db.execute.side_effect = [FakeResult(mv), FakeResult(None)]
        await ModelRegistryService.promote_model(db, mv.id, "staging")
        # db.add should be called with a ModelPromotionLog
        added = db.add.call_args[0][0]
        assert isinstance(added, ModelPromotionLog)
        assert added.from_stage == "dev"
        assert added.to_stage == "staging"


class TestEvalGate:
    """Tests for evaluation gate checker."""

    @pytest.mark.asyncio
    async def test_check_eval_gate_missing_model(self, db: AsyncMock) -> None:
        db.execute.return_value = FakeResult(None)
        passed = await check_eval_gate(db, uuid4(), min_score=0.85)
        assert passed is False

    @pytest.mark.asyncio
    async def test_check_eval_gate_uses_min_score(self, db: AsyncMock, tenant_id: UUID) -> None:
        mv = ModelVersion(
            id=uuid4(),
            tenant_id=tenant_id,
            provider="openai",
            model_name="gpt-4o",
            model_version="v1",
            eval_score=0.90,
        )
        db.execute.return_value = FakeResult(mv)
        passed = await check_eval_gate(db, mv.id, min_score=0.85)
        assert passed is True

    @pytest.mark.asyncio
    async def test_check_eval_gate_uses_tenant_threshold(
        self, db: AsyncMock, tenant_id: UUID
    ) -> None:
        mv = ModelVersion(
            id=uuid4(),
            tenant_id=tenant_id,
            provider="openai",
            model_name="gpt-4o",
            model_version="v1",
            eval_score=0.84,
        )
        from layer4_agents.tenants.models.tenant import Tenant
        tenant = Tenant(
            id=tenant_id,
            name="Test",
            slug="test",
            settings={"model_registry": {"promotion_threshold": 0.80}},
            status="active",
        )
        db.execute.side_effect = [FakeResult(mv), FakeResult(tenant)]
        passed = await check_eval_gate(db, mv.id)
        assert passed is True

    @pytest.mark.asyncio
    async def test_check_eval_gate_defaults_to_0_85(self, db: AsyncMock, tenant_id: UUID) -> None:
        mv = ModelVersion(
            id=uuid4(),
            tenant_id=tenant_id,
            provider="openai",
            model_name="gpt-4o",
            model_version="v1",
            eval_score=_DEFAULT_PROMOTION_THRESHOLD,
        )
        from layer4_agents.tenants.models.tenant import Tenant
        tenant = Tenant(id=tenant_id, name="Test", slug="test", settings={}, status="active")
        db.execute.side_effect = [FakeResult(mv), FakeResult(tenant)]
        passed = await check_eval_gate(db, mv.id)
        assert passed is True


class TestResolveLLMModel:
    """Tests for the LLM model resolution helper."""

    @pytest.mark.asyncio
    async def test_resolve_llm_model_uses_registry(self, db: AsyncMock, tenant_id: UUID) -> None:
        mv = ModelVersion(
            id=uuid4(),
            tenant_id=tenant_id,
            provider="openai",
            model_name="gpt-4-turbo",
            model_version="v1",
            stage="production",
        )
        db.execute.return_value = FakeResult(mv)
        result = await resolve_llm_model(db, tenant_id, "openai")
        assert result == "gpt-4-turbo"

    @pytest.mark.asyncio
    async def test_resolve_llm_model_fallback(self, db: AsyncMock, tenant_id: UUID) -> None:
        import os
        db.execute.return_value = FakeResult(None)
        result = await resolve_llm_model(db, tenant_id, "openai")
        assert result == os.getenv("LLM_MODEL", "gpt-4o")
