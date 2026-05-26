"""Tests for coreference resolver, tier policy, and LLM client."""
from __future__ import annotations

import pytest

from layer2_extraction.coreference import CoreferenceResolver
from layer2_extraction.api.tier_policy import (
    AccessTier,
    ExtractionOperation,
    can_perform_operation,
    get_tier_for_route,
)
from layer2_extraction.shared.llm_client import LLMClient, LLMProvider
from layer2_extraction.models.ontology import Capability, RoleType, Persona
from layer2_extraction.models.relationships import Relationship, PredicateType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cap(id: str, name: str = "Cap Name") -> Capability:
    return Capability(id=id, name=name, description="A capability description", confidence=0.8)


def _persona(id: str, title: str = "Product Manager") -> Persona:
    return Persona(id=id, title=title, role_type=RoleType.CHAMPION, confidence=0.8)


def _rel(source_id: str, target_id: str, predicate: PredicateType) -> Relationship:
    return Relationship(
        source_id=source_id,
        target_id=target_id,
        canonical_predicate=predicate,
        confidence=0.9,
    )


# ===========================================================================
# CoreferenceResolver
# ===========================================================================

class TestCoreferenceResolver:
    def test_empty_entities_returns_empty(self):
        resolver = CoreferenceResolver()
        clusters = resolver.resolve_coreferences([], [])
        assert clusters == []

    def test_single_entity_forms_own_cluster(self):
        resolver = CoreferenceResolver()
        c = _cap("c1", name="Analytics")
        clusters = resolver.resolve_coreferences([c], [])
        assert len(clusters) == 1
        assert clusters[0].member_entity_ids == ["c1"]

    def test_distinct_names_form_separate_clusters(self):
        resolver = CoreferenceResolver()
        c1 = _cap("c1", name="Analytics")
        c2 = _cap("c2", name="Reporting")
        clusters = resolver.resolve_coreferences([c1, c2], [])
        assert len(clusters) == 2
        ids = {frozenset(cl.member_entity_ids) for cl in clusters}
        assert frozenset({"c1"}) in ids
        assert frozenset({"c2"}) in ids

    def test_same_name_merges_into_one_cluster(self):
        resolver = CoreferenceResolver()
        c1 = _cap("c1", name="Analytics")
        c2 = _cap("c2", name="Analytics")
        clusters = resolver.resolve_coreferences([c1, c2], [])
        assert len(clusters) == 1
        assert sorted(clusters[0].member_entity_ids) == ["c1", "c2"]

    def test_case_insensitive_name_match(self):
        resolver = CoreferenceResolver()
        c1 = _cap("c1", name="Analytics Engine")
        c2 = _cap("c2", name="analytics engine")
        clusters = resolver.resolve_coreferences([c1, c2], [])
        assert len(clusters) == 1

    def test_semantically_equivalent_relationship_merges(self):
        resolver = CoreferenceResolver()
        c1 = _cap("c1", name="Analytics")
        c2 = _cap("c2", name="Reporting")
        rel = _rel("c1", "c2", PredicateType.SEMANTICALLY_EQUIVALENT)
        clusters = resolver.resolve_coreferences([c1, c2], [rel])
        assert len(clusters) == 1
        assert sorted(clusters[0].member_entity_ids) == ["c1", "c2"]

    def test_non_equivalent_relationship_does_not_merge(self):
        resolver = CoreferenceResolver()
        c1 = _cap("c1", name="Analytics")
        c2 = _cap("c2", name="Reporting")
        rel = _rel("c1", "c2", PredicateType.ENABLES)
        clusters = resolver.resolve_coreferences([c1, c2], [rel])
        assert len(clusters) == 2

    def test_normalize_collapses_whitespace(self):
        assert CoreferenceResolver._normalize("  Hello   World  ") == "hello world"

    def test_transitive_merge_via_relationships(self):
        resolver = CoreferenceResolver()
        c1 = _cap("c1", name="A")
        c2 = _cap("c2", name="B")
        c3 = _cap("c3", name="C")
        # c1-c2 equivalent, c2-c3 equivalent → all three in one cluster
        rels = [
            _rel("c1", "c2", PredicateType.SEMANTICALLY_EQUIVALENT),
            _rel("c2", "c3", PredicateType.SEMANTICALLY_EQUIVALENT),
        ]
        clusters = resolver.resolve_coreferences([c1, c2, c3], rels)
        assert len(clusters) == 1
        assert sorted(clusters[0].member_entity_ids) == ["c1", "c2", "c3"]

    def test_relationship_with_unknown_ids_ignored(self):
        resolver = CoreferenceResolver()
        c1 = _cap("c1", name="Analytics")
        # Relationship referencing an entity not in the list — should not raise
        rel = _rel("c1", "nonexistent-id", PredicateType.SEMANTICALLY_EQUIVALENT)
        clusters = resolver.resolve_coreferences([c1], [rel])
        assert len(clusters) == 1

    def test_mixed_entity_types(self):
        resolver = CoreferenceResolver()
        c = _cap("c1", name="Analytics")
        p = _persona("p1", title="Product Manager")
        clusters = resolver.resolve_coreferences([c, p], [])
        assert len(clusters) == 2


# ===========================================================================
# AccessTier / can_perform_operation / get_tier_for_route
# ===========================================================================

class TestTierPolicy:
    # -- standard tier --
    def test_standard_can_view_job_status(self):
        assert can_perform_operation(AccessTier.STANDARD, ExtractionOperation.VIEW_JOB_STATUS)

    def test_standard_can_view_results(self):
        assert can_perform_operation(AccessTier.STANDARD, ExtractionOperation.VIEW_RESULTS)

    def test_standard_can_stream_logs(self):
        assert can_perform_operation(AccessTier.STANDARD, ExtractionOperation.STREAM_LOGS)

    def test_standard_cannot_create_job(self):
        assert not can_perform_operation(AccessTier.STANDARD, ExtractionOperation.CREATE_JOB)

    def test_standard_cannot_admin_retry_all(self):
        assert not can_perform_operation(AccessTier.STANDARD, ExtractionOperation.ADMIN_RETRY_ALL)

    # -- advanced tier --
    def test_advanced_can_create_job(self):
        assert can_perform_operation(AccessTier.ADVANCED, ExtractionOperation.CREATE_JOB)

    def test_advanced_can_cancel_job(self):
        assert can_perform_operation(AccessTier.ADVANCED, ExtractionOperation.CANCEL_JOB)

    def test_advanced_can_trigger_retry(self):
        assert can_perform_operation(AccessTier.ADVANCED, ExtractionOperation.TRIGGER_RETRY)

    def test_advanced_cannot_admin_retry_all(self):
        assert not can_perform_operation(AccessTier.ADVANCED, ExtractionOperation.ADMIN_RETRY_ALL)

    # -- admin tier --
    def test_admin_can_do_everything(self):
        for op in ExtractionOperation:
            assert can_perform_operation(AccessTier.ADMIN, op), f"Admin should be able to {op}"

    # -- string inputs --
    def test_string_tier_and_operation(self):
        assert can_perform_operation("standard", "view_job_status")
        assert not can_perform_operation("standard", "create_job")

    # -- invalid inputs fail closed --
    def test_invalid_tier_returns_false(self):
        assert not can_perform_operation("superuser", ExtractionOperation.VIEW_JOB_STATUS)

    def test_invalid_operation_returns_false(self):
        assert not can_perform_operation(AccessTier.ADMIN, "fly_to_moon")

    def test_both_invalid_returns_false(self):
        assert not can_perform_operation("ghost", "teleport")

    # -- route tier resolution --
    def test_known_route_returns_correct_tier(self):
        assert get_tier_for_route("/extraction") == AccessTier.ADVANCED
        assert get_tier_for_route("/admin/retry-all") == AccessTier.ADMIN
        assert get_tier_for_route("/jobs/status") == AccessTier.STANDARD

    def test_unknown_route_defaults_to_standard(self):
        assert get_tier_for_route("/unknown/route") == AccessTier.STANDARD


# ===========================================================================
# LLMClient
# ===========================================================================

class TestLLMClient:
    def test_openai_provider_enum(self):
        client = LLMClient(provider=LLMProvider.OPENAI, api_key="test-key")
        assert client.provider == LLMProvider.OPENAI

    def test_openai_provider_string(self):
        client = LLMClient(provider="openai", api_key="test-key")
        assert client.provider == LLMProvider.OPENAI

    def test_anthropic_provider_string(self):
        client = LLMClient(provider="anthropic", api_key="test-key")
        assert client.provider == LLMProvider.ANTHROPIC

    def test_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="not a valid LLMProvider"):
            LLMClient(provider="invalid_provider", api_key="test-key")

    def test_openai_missing_key_raises(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="OpenAI API key required"):
            LLMClient(provider=LLMProvider.OPENAI, api_key=None)

    def test_anthropic_missing_key_raises(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ValueError, match="Anthropic API key required"):
            LLMClient(provider=LLMProvider.ANTHROPIC, api_key=None)

    def test_openai_key_from_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        client = LLMClient(provider=LLMProvider.OPENAI)
        assert client._api_key == "env-key"

    def test_anthropic_key_from_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-anthropic-key")
        client = LLMClient(provider=LLMProvider.ANTHROPIC)
        assert client._api_key == "env-anthropic-key"

    @pytest.mark.asyncio
    async def test_complete_openai_calls_client(self, monkeypatch: pytest.MonkeyPatch):
        from unittest.mock import AsyncMock, MagicMock

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello from OpenAI"

        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        client = LLMClient(provider=LLMProvider.OPENAI, api_key="test-key")
        client._client = mock_openai_client

        result = await client.complete([{"role": "user", "content": "Hi"}])
        assert result == "Hello from OpenAI"

    @pytest.mark.asyncio
    async def test_complete_anthropic_calls_client(self, monkeypatch: pytest.MonkeyPatch):
        from unittest.mock import AsyncMock, MagicMock

        mock_content = MagicMock()
        mock_content.text = "Hello from Anthropic"

        mock_response = MagicMock()
        mock_response.content = [mock_content]

        mock_anthropic_client = AsyncMock()
        mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

        client = LLMClient(provider=LLMProvider.ANTHROPIC, api_key="test-key")
        client._client = mock_anthropic_client

        result = await client.complete([{"role": "user", "content": "Hi"}])
        assert result == "Hello from Anthropic"

    @pytest.mark.asyncio
    async def test_complete_anthropic_none_client_raises(self, monkeypatch: pytest.MonkeyPatch):
        """When anthropic package is unavailable, _get_client returns None → ValueError."""
        import builtins
        real_import = builtins.__import__

        def _block_anthropic(name, *args, **kwargs):
            if name == "anthropic":
                raise ImportError("anthropic not installed")
            return real_import(name, *args, **kwargs)

        client = LLMClient(provider=LLMProvider.ANTHROPIC, api_key="test-key")
        client._client = None  # force re-init path

        monkeypatch.setattr(builtins, "__import__", _block_anthropic)
        with pytest.raises((ValueError, RuntimeError)):
            await client.complete([{"role": "user", "content": "Hi"}])

    @pytest.mark.asyncio
    async def test_complete_openai_empty_content_returns_empty_string(self):
        from unittest.mock import AsyncMock, MagicMock

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None

        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        client = LLMClient(provider=LLMProvider.OPENAI, api_key="test-key")
        client._client = mock_openai_client

        result = await client.complete([{"role": "user", "content": "Hi"}])
        assert result == ""

    @pytest.mark.asyncio
    async def test_complete_anthropic_empty_content_returns_empty_string(self):
        from unittest.mock import AsyncMock, MagicMock

        mock_response = MagicMock()
        mock_response.content = []

        mock_anthropic_client = AsyncMock()
        mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

        client = LLMClient(provider=LLMProvider.ANTHROPIC, api_key="test-key")
        client._client = mock_anthropic_client

        result = await client.complete([{"role": "user", "content": "Hi"}])
        assert result == ""


    @pytest.mark.asyncio
    async def test_complete_openai_tracks_usage_metrics_and_safe_logs(self, caplog):
        from unittest.mock import AsyncMock, MagicMock
        from layer2_extraction.metrics.prometheus_metrics import initialize_metrics

        initialize_metrics()
        caplog.set_level("INFO")

        mock_response = MagicMock()
        mock_response.model = "gpt-4o"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello from OpenAI"

        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        client = LLMClient(provider=LLMProvider.OPENAI, api_key="sk-super-secret", cost_tracking_enabled=True, job_id="job-1", tenant_id="tenant-1", prompt_version="pv-1")
        client._client = mock_openai_client

        result = await client.complete([{"role": "user", "content": "Hi"}], call_type="entity_extraction")
        assert result == "Hello from OpenAI"

        records = client.get_cost_records()
        assert len(records) == 1
        assert records[0].prompt_tokens == 100
        assert records[0].completion_tokens == 50
        assert records[0].total_tokens == 150
        assert records[0].tenant_id == "tenant-1"
        assert records[0].job_id == "job-1"
        assert records[0].prompt_version == "pv-1"

        log_text = "\n".join(r.getMessage() for r in caplog.records)
        assert "sk-super-secret" not in log_text
        assert "Hi" not in log_text

    @pytest.mark.asyncio
    async def test_complete_anthropic_tracks_usage(self):
        from unittest.mock import AsyncMock, MagicMock

        mock_content = MagicMock()
        mock_content.text = "Hello from Anthropic"
        mock_response = MagicMock()
        mock_response.model = "claude-3-5-sonnet"
        mock_response.usage.input_tokens = 30
        mock_response.usage.output_tokens = 20
        mock_response.content = [mock_content]

        mock_anthropic_client = AsyncMock()
        mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

        client = LLMClient(provider=LLMProvider.ANTHROPIC, api_key="test-key", cost_tracking_enabled=True, job_id="job-2", tenant_id="tenant-2")
        client._client = mock_anthropic_client

        result = await client.complete([{"role": "user", "content": "Hi"}], prompt_version="pv-2")
        assert result == "Hello from Anthropic"
        records = client.get_cost_records()
        assert len(records) == 1
        assert records[0].prompt_tokens == 30
        assert records[0].completion_tokens == 20
        assert records[0].total_tokens == 50
        assert records[0].prompt_version == "pv-2"
