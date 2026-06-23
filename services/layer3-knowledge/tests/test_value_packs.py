"""Tests for Value Packs API routes.

Tests cover:
- Formula execution in execute_pack
- Update pack semantics after refactoring
- Fork pack semantics after refactoring
- UUID validation
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from value_fabric.shared.error_handling.exceptions import ValidationError

from src.api.routes.value_packs import (
    PackExecuteRequest,
    PackForkRequest,
    PackUpdateRequest,
    _build_fork_params,
    _build_update_params,
    _execute_fork,
    _get_original_pack,
    _get_pack_formulas,
    _merge_variables,
    _update_pack_relationships,
    _update_relationships,
    _validate_pack_id,
    execute_pack,
)


class TestValidatePackId:
    """Tests for pack ID validation helper (UUIDs and slug-style IDs)."""

    def test_valid_uuid(self):
        """Should not raise for valid UUID."""
        valid_id = str(uuid.uuid4())
        # Should not raise
        _validate_pack_id(valid_id)

    def test_valid_slug_id(self):
        """Should not raise for valid slug-style pack ID."""
        valid_slug = "manufacturing-v1"
        # Should not raise
        _validate_pack_id(valid_slug)

    def test_invalid_pack_id(self):
        """Should raise HTTPException 400 for invalid pack ID."""
        with pytest.raises(ValidationError) as exc_info:
            _validate_pack_id("not@valid#id")
        assert "Invalid pack_id format" in str(exc_info.value)

    def test_empty_pack_id(self):
        """Should raise HTTPException for empty string."""
        with pytest.raises(ValidationError) as exc_info:
            _validate_pack_id("")
        assert "pack_id is required" in str(exc_info.value)


class TestMergeVariables:
    """Tests for variable merging in formula execution."""

    def test_merge_with_defaults(self):
        """Should merge user values with formula defaults."""
        formula_defaults = [
            {"name": "a", "default_value": 10.0},
            {"name": "b", "default_value": 20.0},
        ]
        user_vars = {"a": 15.0}

        result = _merge_variables(formula_defaults, user_vars)

        assert result["a"] == 15.0  # User value overrides default
        assert result["b"] == 20.0  # Default preserved

    def test_merge_all_user_values(self):
        """Should use all user values when provided."""
        formula_defaults = [
            {"name": "x", "default_value": 1.0},
        ]
        user_vars = {"x": 100.0}

        result = _merge_variables(formula_defaults, user_vars)

        assert result["x"] == 100.0

    def test_merge_missing_defaults(self):
        """Should handle missing default values gracefully."""
        formula_defaults = [
            {"name": "a"},  # No default_value key
            {"name": "b", "default_value": None},
        ]
        user_vars = {}

        result = _merge_variables(formula_defaults, user_vars)

        # Should be empty since no valid defaults and no user values
        assert result == {}

    def test_merge_invalid_user_value(self):
        """Should keep default when user value is invalid."""
        formula_defaults = [
            {"name": "a", "default_value": 10.0},
        ]
        user_vars = {"a": "not-a-number"}

        result = _merge_variables(formula_defaults, user_vars)

        # Invalid user value skipped, default kept
        assert result["a"] == 10.0


class TestBuildUpdateParams:
    """Tests for update params builder."""

    def test_build_with_all_fields(self):
        """Should build params for all updateable fields."""
        request = PackUpdateRequest(
            name="New Name",
            description="New Desc",
            industry="Tech",
            segment="Enterprise",
            status="published",
        )
        pack_id = str(uuid.uuid4())

        set_clauses, params = _build_update_params(request, pack_id)

        assert "vp.name = $name" in set_clauses
        assert "vp.description = $description" in set_clauses
        assert "vp.industry = $industry" in set_clauses
        assert "vp.segment = $segment" in set_clauses
        assert "vp.status = $status" in set_clauses
        assert params["name"] == "New Name"
        assert params["pack_id"] == pack_id
        assert "updated_at" in params

    def test_build_partial_update(self):
        """Should only include provided fields."""
        request = PackUpdateRequest(name="Only Name")
        pack_id = str(uuid.uuid4())

        set_clauses, params = _build_update_params(request, pack_id)

        assert "vp.name = $name" in set_clauses
        assert "vp.description = $description" not in set_clauses
        assert "name" in params
        assert "description" not in params

    def test_always_includes_updated_at(self):
        """Should always include updatedAt timestamp."""
        request = PackUpdateRequest()
        pack_id = str(uuid.uuid4())

        set_clauses, params = _build_update_params(request, pack_id)

        assert "vp.updatedAt = $updated_at" in set_clauses
        assert "updated_at" in params


class TestBuildForkParams:
    """Tests for fork params builder."""

    def test_build_fork_params(self):
        """Should build correct fork parameters."""
        orig = {
            "id": str(uuid.uuid4()),
            "name": "Original Pack",
            "description": "Original Desc",
            "industry": "Tech",
            "segment": "SMB",
            "version": "1.2.3",
        }
        request = PackForkRequest(workspace_id="ws_123", user_id="user_456")
        new_pack_id = str(uuid.uuid4())

        params = _build_fork_params(orig, request, new_pack_id)

        assert params["old_pack_id"] == orig["id"]
        assert params["new_pack_id"] == new_pack_id
        assert params["name"] == "Original Pack (Fork)"
        assert params["description"] == "Original Desc"
        assert params["industry"] == "Tech"
        assert params["segment"] == "SMB"
        assert params["status"] == "draft"
        assert params["workspace_id"] == "ws_123"
        assert params["created_by"] == "user_456"
        assert "created_at" in params
        # Version should be incremented
        assert params["version"] == "1.2.4"

    def test_build_fork_with_custom_name(self):
        """Should use custom name when provided."""
        orig = {
            "id": str(uuid.uuid4()),
            "name": "Original",
            "version": "1.0.0",
        }
        request = PackForkRequest(
            workspace_id="ws_123", name="Custom Fork Name"
        )
        new_pack_id = str(uuid.uuid4())

        params = _build_fork_params(orig, request, new_pack_id)

        assert params["name"] == "Custom Fork Name"

    def test_build_fork_default_version(self):
        """Should use default version when original has none."""
        orig = {"id": str(uuid.uuid4()), "name": "Original"}
        request = PackForkRequest(workspace_id="ws_123")
        new_pack_id = str(uuid.uuid4())

        params = _build_fork_params(orig, request, new_pack_id)

        # Should increment from default "1.0.0" to "1.0.1"
        assert params["version"] == "1.0.1"


class TestGetPackFormulas:
    """Tests for getting pack formulas from Neo4j."""

    @pytest.mark.asyncio
    async def test_get_pack_formulas_success(self, monkeypatch):
        """Should return list of formula dicts."""
        mock_driver = MagicMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        observed = {}

        async def fake_run_validated_query(session, query, params, *, tenant_id=None, **kwargs):
            observed.update(
                {"session": session, "params": params, "tenant_id": tenant_id, "kwargs": kwargs}
            )
            return mock_result

        mock_driver.session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_result.data.return_value = [
            {
                "formula_id": "roi_basic",
                "expression": "(a - b) / c * 100",
                "variables": [{"name": "a"}, {"name": "b"}],
                "name": "ROI Formula",
            }
        ]
        monkeypatch.setattr("src.api.routes.value_packs.run_validated_query", fake_run_validated_query)

        result = await _get_pack_formulas(mock_driver, "pack_123", "tenant-secure")

        assert len(result) == 1
        assert result[0]["formula_id"] == "roi_basic"
        assert result[0]["expression"] == "(a - b) / c * 100"
        assert observed["tenant_id"] == "tenant-secure"
        assert observed["params"] == {"pack_id": "pack_123", "tenant_id": "tenant-secure"}
        assert observed["kwargs"] == {
            "require_explicit_tenant_id": True,
            "query_name": "value_packs.get_pack_formulas",
        }

    @pytest.mark.asyncio
    async def test_get_pack_formulas_empty(self, monkeypatch):
        """Should return empty list when pack has no formulas."""
        mock_driver = MagicMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        mock_driver.session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_result.data.return_value = []
        monkeypatch.setattr(
            "src.api.routes.value_packs.run_validated_query",
            AsyncMock(return_value=mock_result),
        )

        result = await _get_pack_formulas(mock_driver, "pack_123", "tenant-secure")

        assert result == []


class TestFormulaEvaluation:
    """Tests for formula evaluation in execute_pack."""

    def test_merge_variables_with_defaults(self):
        """Should merge user values with formula defaults."""
        formula_defaults = [
            {"name": "a", "default_value": 5.0},
            {"name": "b", "default_value": 10.0},
        ]
        user_vars = {"a": 15.0}

        result = _merge_variables(formula_defaults, user_vars)

        assert result["a"] == 15.0  # User value overrides default
        assert result["b"] == 10.0  # Default preserved

    def test_merge_variables_invalid_user_value(self):
        """Should keep default when user value is invalid."""
        formula_defaults = [
            {"name": "a", "default_value": 10.0},
        ]
        user_vars = {"a": "not-a-number"}

        result = _merge_variables(formula_defaults, user_vars)

        # Invalid user value skipped, default kept
        assert result["a"] == 10.0


class TestExecutePackErrorHandling:
    """Tests for execute_pack error handling."""

    @pytest.mark.asyncio
    async def test_execute_pack_no_formulas_raises_400(self):
        """Should raise 400 when pack has no formulas."""
        pack_id = str(uuid.uuid4())

        with patch(
            "src.api.routes.value_packs._get_pack_formulas",
            return_value=[],
        ), patch(
            "src.api.routes.value_packs._tenant_id_from_api_key",
            return_value="tenant-secure",
        ):
            # Create a minimal mock driver
            mock_driver = MagicMock()

            request = PackExecuteRequest(workspace_id="ws_123", variables={})

            with pytest.raises(ValidationError) as exc_info:
                await execute_pack(pack_id, request, mock_driver)

            assert "no formulas" in str(exc_info.value).lower()


class TestUpdatePackSemantics:
    """Tests that update_pack refactoring preserves semantics."""

    @pytest.mark.asyncio
    async def test_update_pack_helper_functions_exist(self):
        """Verify helper functions are properly defined."""
        # These functions should exist and be importable
        assert callable(_build_update_params)
        assert callable(_update_pack_relationships)
        assert callable(_update_relationships)

    def test_build_update_params_structure(self):
        """Should create correct SET clauses structure."""
        request = PackUpdateRequest(
            name="New Name",
            industry="Tech",
        )
        pack_id = str(uuid.uuid4())

        set_clauses, params = _build_update_params(request, pack_id)

        # Always includes updatedAt
        assert any("updatedAt" in clause for clause in set_clauses)
        assert "updated_at" in params

        # Includes provided fields
        assert any("name" in clause for clause in set_clauses)
        assert any("industry" in clause for clause in set_clauses)

        # Doesn't include unset fields
        assert not any("description" in clause for clause in set_clauses)
        assert not any("segment" in clause for clause in set_clauses)


class TestForkPackSemantics:
    """Tests that fork_pack refactoring preserves semantics."""

    @pytest.mark.asyncio
    async def test_fork_pack_helper_functions_exist(self):
        """Verify helper functions are properly defined."""
        # These functions should exist and be importable
        assert callable(_get_original_pack)
        assert callable(_build_fork_params)
        assert callable(_execute_fork)

    def test_build_fork_params_structure(self):
        """Should create correct fork parameters."""
        orig = {
            "id": str(uuid.uuid4()),
            "name": "Original Pack",
            "description": "Original Desc",
            "industry": "Tech",
            "version": "1.2.3",
        }
        request = PackForkRequest(workspace_id="ws_123", user_id="user_456")
        new_pack_id = str(uuid.uuid4())

        params = _build_fork_params(orig, request, new_pack_id)

        # Key fields should be present
        assert params["old_pack_id"] == orig["id"]
        assert params["new_pack_id"] == new_pack_id
        assert params["name"] == "Original Pack (Fork)"
        assert params["workspace_id"] == "ws_123"
        assert params["created_by"] == "user_456"
        assert params["status"] == "draft"

        # Version should be incremented
        assert params["version"] == "1.2.4"
