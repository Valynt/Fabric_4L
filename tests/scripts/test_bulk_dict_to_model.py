"""Tests for bulk_dict_to_model script - regression tests for code review fixes."""

import ast
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
from scripts.ci.bulk_dict_to_model import (
    TYPED_DICT_IMPORT_LINE,
    TYPED_DICT_MODULE,
    _build_models,
    _infer_type,
)


class TestInferType:
    """Test type inference from AST nodes."""

    def test_infer_string_constant(self):
        """Test string constant inference."""
        node = ast.Constant(value="hello")
        assert _infer_type(node) == "str"

    def test_infer_int_constant(self):
        """Test int constant inference."""
        node = ast.Constant(value=42)
        assert _infer_type(node) == "int"

    def test_infer_none_as_any(self):
        """Test None is inferred as Any."""
        node = ast.Constant(value=None)
        assert _infer_type(node) == "Any"

    def test_infer_bool_constant(self):
        """Test bool constant inference."""
        node = ast.Constant(value=True)
        assert _infer_type(node) == "bool"

    def test_infer_float_constant(self):
        """Test float constant inference."""
        node = ast.Constant(value=3.14)
        assert _infer_type(node) == "float"

    def test_infer_list_as_list_any(self):
        """Test list is inferred as list[Any]."""
        node = ast.List(elts=[], ctx=ast.Load())
        assert _infer_type(node) == "list[Any]"


class TestBuildModelsKeyRequiredLogic:
    """Regression test: Issue #4 - key required status logic error."""

    def test_key_present_in_all_returns_is_required(self):
        """A key present in all returns should be required without None default."""
        source = '''
def my_func():
    if condition:
        return {"status": "ok", "data": 123}
    else:
        return {"status": "error", "data": None}
'''
        tree = ast.parse(source)
        from scripts.ci.bulk_dict_to_model import _gather_returns
        grouped = _gather_returns(tree, source)
        
        models = _build_models(grouped)
        func_name = "my_func"
        
        assert func_name in models, "Function should be in generated models"
        model_text, _ = models[func_name]
        # "status" is present in both returns with str type - should be required
        assert "status: str" in model_text, f"status should be required str. Got:\n{model_text}"
        # Should NOT have None default since present in all returns
        assert "status: str = None" not in model_text, "Required field should not have None default"

    def test_key_missing_in_some_returns_is_optional(self):
        """A key missing from some returns should be marked as Optional with default."""
        source = '''
def my_func():
    if condition:
        return {"status": "ok", "data": 123}  # has "data"
    else:
        return {"status": "error"}  # missing "data"
'''
        tree = ast.parse(source)
        from scripts.ci.bulk_dict_to_model import _gather_returns
        grouped = _gather_returns(tree, source)
        
        models = _build_models(grouped)
        func_name = "my_func"
        
        assert func_name in models, "Function should be in generated models"
        model_text, _ = models[func_name]
        # "data" should be optional since missing from one return
        assert "data: " in model_text, f"data field should exist. Got:\n{model_text}"
        # Should have None default since not present in all returns
        assert "data: int | None = None" in model_text or "data: Any | None = None" in model_text, \
            f"Optional field should have | None = None. Got:\n{model_text}"


class TestTypedDictImportConstant:
    """Test import configuration constants."""

    def test_import_line_is_correct(self):
        """Verify import line constant is correct."""
        expected = f"from {TYPED_DICT_MODULE} import TypedDictModel"
        assert expected == TYPED_DICT_IMPORT_LINE

    def test_import_line_in_generated_code(self):
        """Verify generated code uses the import constant."""
        source = "def foo():\n    return {'key': 'value'}\n"
        tree = ast.parse(source)
        from scripts.ci.bulk_dict_to_model import _apply_changes, _gather_returns
        grouped = _gather_returns(tree, source)
        
        assert grouped, "Should have detected return statements"
        models = _build_models(grouped)
        all_models_text = "\n".join(mt for mt, _ in models.values())
        all_replacements = []
        for _func_name, (_mt, reps) in models.items():
            all_replacements.extend(reps)
        
        result = _apply_changes(source, all_models_text, all_replacements)
        assert TYPED_DICT_IMPORT_LINE in result, f"Import line not found in generated code:\n{result}"


class TestAtomicWrite:
    """Test atomic file write functionality."""

    def test_backup_created_before_write(self, tmp_path):
        """Test backup is created when requested."""
        from scripts.ci.bulk_dict_to_model import _write_file_atomic
        
        test_file = tmp_path / "test.py"
        original_content = "original content"
        test_file.write_text(original_content)
        
        new_content = "new content"
        _write_file_atomic(test_file, new_content, create_backup=True)
        
        # Check backup was created
        backup_file = test_file.with_suffix(test_file.suffix + ".bak")
        assert backup_file.exists()
        assert backup_file.read_text() == original_content
        assert test_file.read_text() == new_content

    def test_no_backup_when_disabled(self, tmp_path):
        """Test backup is not created when disabled."""
        from scripts.ci.bulk_dict_to_model import _write_file_atomic
        
        test_file = tmp_path / "test.py"
        test_file.write_text("original")
        
        _write_file_atomic(test_file, "new", create_backup=False)
        
        backup_file = test_file.with_suffix(test_file.suffix + ".bak")
        assert not backup_file.exists()
