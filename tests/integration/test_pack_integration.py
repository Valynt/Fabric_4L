"""Integration Tests for Value Pack Loading and API

Validates that packs load correctly and API endpoints work as expected.
"""

import json
from pathlib import Path
from typing import Any

import pytest

PACKS_DIR = Path(__file__).parent.parent.parent / "packs"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pack_manifest() -> dict[str, Any]:
    """Load and return the pack manifest."""
    manifest_path = PACKS_DIR / "pack-manifest.json"
    if not manifest_path.exists():
        pytest.skip(f"Manifest not found: {manifest_path}")
    
    try:
        with open(manifest_path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in manifest: {e}")


def get_pack_path(pack: dict[str, Any]) -> Path:
    """Get filesystem path for a pack from manifest entry."""
    pack_id = pack["pack_id"]
    base_id = pack_id.replace("-v1", "").replace("-v2", "").replace("-v3", "")
    return PACKS_DIR / base_id


class TestPackLoading:
    """Test pack loading from JSON files."""

    def test_all_packs_loadable(self, pack_manifest: dict[str, Any]) -> None:
        """All packs in manifest must be loadable."""
        required_files = [
            "formulas.json",
            "variables.json", 
            "ontology.json",
            "workflow_template.json",
            "README.md",
        ]
        
        for pack in pack_manifest.get("packs", []):
            pack_path = get_pack_path(pack)
            
            assert pack_path.exists(), f"Pack directory missing: {pack_path}"
            
            # Verify all required files exist
            for filename in required_files:
                file_path = pack_path / filename
                assert file_path.exists(), f"Required file missing: {file_path}"

    def test_pack_formulas_loadable(self, pack_manifest: dict[str, Any]) -> None:
        """All pack formulas must load without errors."""
        for pack in pack_manifest["packs"]:
            pack_path = get_pack_path(pack)
            formulas_file = pack_path / "formulas.json"
            
            if not formulas_file.exists():
                pytest.fail(f"Formulas file missing: {formulas_file}")
            
            try:
                with open(formulas_file, encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {formulas_file}: {e}")
            
            assert "formulas" in data, f"Missing 'formulas' key in {formulas_file}"
            actual_count = len(data.get("formulas", []))
            expected_count = pack.get("formula_count", 0)
            assert actual_count == expected_count, (
                f"Formula count mismatch in {pack['pack_id']}: "
                f"expected {expected_count}, got {actual_count}"
            )
            
            # Validate formula structure
            for formula in data["formulas"]:
                assert "formula_id" in formula, "Formula missing 'formula_id'"
                assert "expression" in formula, "Formula missing 'expression'"
                assert "string" in formula["expression"], "Expression missing 'string'"

    def test_pack_variables_loadable(self, pack_manifest: dict[str, Any]) -> None:
        """All pack variables must load without errors."""
        for pack in pack_manifest["packs"]:
            pack_path = get_pack_path(pack)
            variables_file = pack_path / "variables.json"
            
            if not variables_file.exists():
                pytest.fail(f"Variables file missing: {variables_file}")
            
            try:
                with open(variables_file, encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {variables_file}: {e}")
            
            assert "variables" in data, f"Missing 'variables' key in {variables_file}"
            actual_count = len(data.get("variables", []))
            expected_count = pack.get("variable_count", 0)
            assert actual_count == expected_count, (
                f"Variable count mismatch in {pack['pack_id']}: "
                f"expected {expected_count}, got {actual_count}"
            )


class TestPackConsistency:
    """Test consistency across pack files."""

    def test_pack_ids_consistent(self, pack_manifest: dict[str, Any]) -> None:
        """Pack IDs must match across all files in each pack."""
        json_files = [
            "formulas.json",
            "variables.json", 
            "ontology.json",
            "workflow_template.json",
        ]
        
        for pack in pack_manifest.get("packs", []):
            pack_id = pack.get("pack_id", "unknown")
            pack_path = get_pack_path(pack)
            
            # Check each JSON file has correct pack_id
            for filename in json_files:
                file_path = pack_path / filename
                if not file_path.exists():
                    continue  # Skip optional files
                    
                try:
                    with open(file_path, encoding="utf-8") as f:
                        data = json.load(f)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON in {file_path}: {e}")
                
                actual_pack_id = data.get("pack_id", "unknown")
                assert actual_pack_id == pack_id, (
                    f"{filename} has wrong pack_id: expected '{pack_id}', got '{actual_pack_id}' "
                    f"in pack '{pack.get('pack_id', 'unknown')}'"
                )

    def test_formula_variable_references_valid(self, pack_manifest: dict[str, Any]) -> None:
        """Formula variable references must point to existing variables."""
        for pack in pack_manifest.get("packs", []):
            pack_path = get_pack_path(pack)
            
            # Load variables
            variables_file = pack_path / "variables.json"
            if not variables_file.exists():
                continue
                
            try:
                with open(variables_file, encoding="utf-8") as f:
                    var_data = json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {variables_file}: {e}")
            
            valid_vars = {v["variable_name"] for v in var_data.get("variables", [])}
            
            # Check formulas
            formulas_file = pack_path / "formulas.json"
            if not formulas_file.exists():
                continue
                
            try:
                with open(formulas_file, encoding="utf-8") as f:
                    formula_data = json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {formulas_file}: {e}")
            
            for formula in formula_data.get("formulas", []):
                formula_id = formula.get("formula_id", "unknown")
                expr_vars = formula.get("expression", {}).get("variables", [])
                for var in expr_vars:
                    assert var in valid_vars, (
                        f"Invalid variable reference '{var}' in formula '{formula_id}' "
                        f"(pack: {pack.get('pack_id', 'unknown')})"
                    )


class TestManifestAccuracy:
    """Test manifest statistics are accurate."""

    def test_manifest_formula_counts(self, pack_manifest: dict[str, Any]) -> None:
        """Manifest formula counts must match actual files."""
        for pack in pack_manifest.get("packs", []):
            pack_path = get_pack_path(pack)
            formulas_file = pack_path / "formulas.json"
            
            if not formulas_file.exists():
                continue
                
            try:
                with open(formulas_file, encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {formulas_file}: {e}")
            
            actual_count = len(data.get("formulas", []))
            expected_count = pack.get("formula_count", 0)
            assert actual_count == expected_count, (
                f"Formula count mismatch in {pack['pack_id']}: "
                f"expected {expected_count}, got {actual_count}"
            )

    def test_manifest_variable_counts(self, pack_manifest: dict[str, Any]) -> None:
        """Manifest variable counts must match actual files."""
        for pack in pack_manifest.get("packs", []):
            pack_path = get_pack_path(pack)
            variables_file = pack_path / "variables.json"
            
            if not variables_file.exists():
                continue
                
            try:
                with open(variables_file, encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {variables_file}: {e}")
            
            actual_count = len(data.get("variables", []))
            expected_count = pack.get("variable_count", 0)
            assert actual_count == expected_count, (
                f"Variable count mismatch in {pack['pack_id']}: "
                f"expected {expected_count}, got {actual_count}"
            )

    def test_manifest_statistics(self, pack_manifest: dict[str, Any]) -> None:
        """Manifest total statistics must be correct."""
        stats = pack_manifest.get("statistics", {})
        packs = pack_manifest.get("packs", [])
        
        total_formulas = sum(p.get("formula_count", 0) for p in packs)
        total_variables = sum(p.get("variable_count", 0) for p in packs)
        total_entities = sum(p.get("entity_count", 0) for p in packs)
        
        # Skip if no statistics section in manifest
        if not stats:
            pytest.skip("No statistics section in manifest")
        
        assert stats.get("total_formulas") == total_formulas, "Total formulas mismatch"
        assert stats.get("total_variables") == total_variables, "Total variables mismatch"
        assert stats.get("total_entities") == total_entities, "Total entities mismatch"


class TestPackLoaderIntegration:
    """Test pack loader integration with Layer 3 API."""
    
    def test_pack_loader_imports(self):
        """Pack loader module must be importable and expose expected functions."""
        try:
            from api.routes.pack_loader import (
                get_available_packs,
                load_pack_formulas,
                load_pack_manifest,
                load_pack_variables,
            )
            # Verify all expected functions are callable
            assert callable(load_pack_formulas)
            assert callable(load_pack_variables)
            assert callable(get_available_packs)
            assert callable(load_pack_manifest)
        except ImportError:
            pytest.skip("Layer 3 API not available - pack_loader module not found")

    def test_pack_loader_formulas(self) -> None:
        """Pack loader must return correctly formatted formulas."""
        try:
            from api.routes.pack_loader import load_pack_formulas
        except ImportError:
            pytest.skip("Layer 3 API not available - pack_loader module not found")
        
        formulas = load_pack_formulas("financial-services-v1")
        assert len(formulas) > 0, "No formulas returned for financial-services-v1"
        
        # Check structure
        required_fields = ["id", "name", "expression", "variables", "pack_id"]
        for formula in formulas:
            for field in required_fields:
                assert field in formula, f"Formula missing required field: {field}"
            assert formula["pack_id"] == "financial-services-v1", "Pack ID mismatch in formula"
