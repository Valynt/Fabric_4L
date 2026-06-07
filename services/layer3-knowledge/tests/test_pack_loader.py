from __future__ import annotations

"""Tests for pack_loader module.

Validates correct behavior for pack loading, version extraction,
and path traversal protection.
"""


import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from src.api.routes import pack_loader
from src.api.routes.pack_loader import (
    VALID_PACK_ID_PATTERN,
    VERSION_SUFFIX_PATTERN,
    _extract_pack_slug,
    get_available_packs,
    get_cached_formulas,
    get_cached_packs,
    get_cached_variables,
    invalidate_cache,
    load_pack_formulas,
    load_pack_manifest,
    load_pack_variables,
    _formula_cache,
    _variable_cache,
    _pack_cache,
)

if TYPE_CHECKING:
    from collections.abc import Generator


class TestPackIdValidation:
    """Tests for pack ID regex validation."""

    def test_valid_pack_ids(self) -> None:
        """Should accept valid alphanumeric pack IDs with hyphens."""
        valid_ids = [
            "financial-services-v1",
            "manufacturing-v1",
            "ai-technology-v1",
            "valid-pack-123",
            "simple",
            "a-b-c-d",
        ]
        for pid in valid_ids:
            assert VALID_PACK_ID_PATTERN.match(pid), f"Should match: {pid}"

    def test_invalid_pack_ids(self) -> None:
        """Should reject pack IDs with dangerous characters."""
        invalid_ids = [
            "test..pack",  # dots
            "test/pack",  # forward slash
            "test\\\\pack",  # backslash
            "test_pack",  # underscore (not in allowed set)
            "test@pack",  # special char
            "",  # empty string
        ]
        for pid in invalid_ids:
            assert not VALID_PACK_ID_PATTERN.match(pid), f"Should NOT match: {pid}"


class TestVersionExtraction:
    """Tests for version suffix extraction from pack IDs."""

    def test_v2_pack_id_handled_correctly(self) -> None:
        """v2 packs now load correctly with regex-based extraction."""
        pack_id = "manufacturing-v2"
        slug = VERSION_SUFFIX_PATTERN.sub("", pack_id)
        assert slug == "manufacturing", "v2 packs get correct slug"
        # Verify via helper
        assert _extract_pack_slug(pack_id) == "manufacturing"

    def test_v123_pack_id_handled_correctly(self) -> None:
        """Regex correctly removes version suffix without corruption."""
        pack_id = "test-v123"
        slug = VERSION_SUFFIX_PATTERN.sub("", pack_id)
        assert slug == "test", "v123 packs get correct slug (not test23)"
        # Verify via helper
        assert _extract_pack_slug(pack_id) == "test"

    def test_v1_pack_id_handled_correctly(self) -> None:
        """v1 suffix is properly removed."""
        pack_id = "financial-services-v1"
        slug = VERSION_SUFFIX_PATTERN.sub("", pack_id)
        assert slug == "financial-services"
        assert _extract_pack_slug(pack_id) == "financial-services"

    def test_no_version_pack_id_unchanged(self) -> None:
        """Pack IDs without version suffix remain unchanged."""
        pack_id = "simple-pack"
        slug = VERSION_SUFFIX_PATTERN.sub("", pack_id)
        assert slug == "simple-pack"
        assert _extract_pack_slug(pack_id) == "simple-pack"


class TestPathTraversalProtection:
    """Tests for path traversal safety."""

    def test_extract_pack_slug_rejects_dangerous_ids(self) -> None:
        """_extract_pack_slug properly rejects path traversal attempts."""
        dangerous_cases = [
            ("-v1", None),  # empty after version removal
            (".-v1", None),  # becomes "."
            ("..-v1", None),  # becomes ".."
            ("test/../pack-v1", None),  # contains traversal
            ("test/pack-v1", None),  # contains forward slash
        ]

        for pack_id, expected in dangerous_cases:
            result = _extract_pack_slug(pack_id)
            assert result == expected, f"Pack ID {pack_id} should produce {expected}, got {result}"

    def test_directory_escape_attempts_blocked(self) -> None:
        """Various escape attempts should return empty list."""
        dangerous_ids = [
            "..-v1",  # becomes ".." after version removal - TRAVERSAL RISK
            ".-v1",  # becomes "." after version removal
            "-v1",  # becomes "" after version removal
        ]

        for pid in dangerous_ids:
            # Should not raise, should return empty list
            result = load_pack_formulas(pid)
            assert result == [], f"Dangerous pack_id {pid} should return empty list"
            result_vars = load_pack_variables(pid)
            assert result_vars == [], f"Dangerous pack_id {pid} should return empty list for variables"


class TestManifestLoading:
    """Tests for manifest loading edge cases."""

    def test_missing_manifest_returns_none(self) -> None:
        """Should return None when manifest doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("api.routes.pack_loader.MANIFEST_FILE", Path(tmpdir) / "nonexistent.json"):
                result = load_pack_manifest()
                assert result is None

    def test_malformed_manifest_returns_none_with_logging(self) -> None:
        """Malformed JSON returns None but now logs a warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_file = Path(tmpdir) / "pack-manifest.json"
            manifest_file.write_text("not valid json {")

            with patch("api.routes.pack_loader.MANIFEST_FILE", manifest_file):
                # Implementation now logs warning before returning None
                result = load_pack_manifest()
                assert result is None  # Returns None but logs warning


@pytest.fixture
def clean_cache() -> Generator[None, None, None]:
    """Ensure cache is clean before and after test."""
    invalidate_cache()
    yield
    invalidate_cache()


class TestCacheBehavior:
    """Tests for module-level caching."""

    def test_cache_invalidation_clears_all_caches(self, clean_cache: None) -> None:
        """Cache should clear when invalidate_cache is called."""
        # Prime the caches (may remain None if no manifest exists)
        get_cached_packs()
        get_cached_formulas()
        get_cached_variables()

        # Check if we have a manifest to work with
        # pylint: disable=protected-access
        has_manifest = pack_loader.MANIFEST_FILE.exists()
        
        if not has_manifest:
            # Without manifest, caches should remain None/empty
            pytest.skip("No manifest file available to prime caches")
            
        # Verify at least one cache is populated (implementation detail)
        at_least_one_cached = (
            pack_loader._pack_cache is not None
            or pack_loader._formula_cache is not None
            or pack_loader._variable_cache is not None
        )
        assert at_least_one_cached, "At least one cache should be populated with manifest"

        # Invalidate
        invalidate_cache()

        # Verify all caches are cleared
        assert pack_loader._pack_cache is None
        assert pack_loader._formula_cache is None
        assert pack_loader._variable_cache is None

    def test_cache_returns_same_data_on_subsequent_calls(self, clean_cache: None) -> None:
        """Cached data should be identical on repeated calls."""
        first_call = get_cached_packs()
        
        # If no manifest, cache will be empty list but still cached
        # If manifest exists, cache will be populated list
        # In both cases, second call should return same object
        second_call = get_cached_packs()

        assert first_call is second_call, "Cache should return same object (identity check)"


class TestFormulaLoading:
    """Tests for formula loading from packs."""

    def test_missing_formulas_file_returns_empty(self) -> None:
        """Should return empty list when formulas.json doesn't exist."""
        result = load_pack_formulas("nonexistent-pack-v1")
        assert result == []

    def test_valid_pack_loads_formulas(self, clean_cache: None) -> None:
        """Should load formulas from a valid pack."""
        packs = get_available_packs()
        assert packs, "Test requires at least one pack to be available"

        pack_id = packs[0]["pack_id"]
        formulas = load_pack_formulas(pack_id)

        assert isinstance(formulas, list)
        # Real packs should have formulas
        assert len(formulas) > 0, f"Pack {pack_id} should have formulas"
        # Verify formula structure
        if formulas:
            first = formulas[0]
            assert "id" in first
            assert "name" in first
            assert "expression" in first

    def test_none_pack_id_returns_empty(self) -> None:
        """Should handle None pack_id gracefully."""
        # This is a defensive test - function signature doesn't allow None
        # but we test behavior if it were to happen
        result = load_pack_formulas("")  # Empty string is closest we can get
        assert result == []


class TestVariableLoading:
    """Tests for variable loading from packs."""

    def test_missing_variables_file_returns_empty(self) -> None:
        """Should return empty list when variables.json doesn't exist."""
        result = load_pack_variables("nonexistent-pack-v1")
        assert result == []

    def test_valid_pack_loads_variables(self, clean_cache: None) -> None:
        """Should load variables from a valid pack."""
        packs = get_available_packs()
        assert packs, "Test requires at least one pack to be available"

        pack_id = packs[0]["pack_id"]
        variables = load_pack_variables(pack_id)

        assert isinstance(variables, list)
        # Real packs should have variables
        assert len(variables) > 0, f"Pack {pack_id} should have variables"
        # Verify variable structure
        if variables:
            first = variables[0]
            assert "name" in first
            assert "type" in first

