"""Unit tests for scripts/ci/ban_str_e.py regex behavior."""
from pathlib import Path
import pytest

# Import the script under test by path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ci"))
from ban_str_e import check_file


class TestCheckFile:
    """Validate that check_file catches unsafe str(e) but allows safe identifiers."""

    @pytest.mark.parametrize("code", [
        'logger.error(str(e))',
        'detail = str(err)',
        'msg = str(exc)',
        'error = str(error)',
        'text = str(exception)',
        'logger.error(str(E))',
        'detail = str(ERR)',
        'msg = str(Exc)',
        'error = str(Error)',
        'text = str(Exception)',
    ])
    def test_detects_exception_variable_str(self, tmp_path, code):
        f = tmp_path / "sample.py"
        f.write_text(code)
        issues = check_file(f)
        assert len(issues) == 1, f"Expected 1 issue for {code!r}, got {issues}"

    @pytest.mark.parametrize("code", [
        'result = str(extract)',
        'result = str(execute)',
        'result = str(exit_code)',
        'result = str(external_id)',
        'result = str(errors_list)',
        'result = str(exceptions)',
        'result = str(error_message)',
        'value = str(42)',
        'value = str("hello")',
        'value = repr(e)',
        'value = getattr(e, "name", str(e))',
        '# str(e) in comment is okay',
    ])
    def test_allows_safe_identifiers(self, tmp_path, code):
        f = tmp_path / "sample.py"
        f.write_text(code)
        issues = check_file(f)
        assert len(issues) == 0, f"Expected 0 issues for {code!r}, got {issues}"
