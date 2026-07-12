"""Unit tests for scripts/ci/ban_str_e.py regex behavior."""
# Import the script under test by path
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ci"))
from ban_str_e import check_file


class TestCheckFile:
    """Validate that check_file catches unsafe str(e) but allows safe identifiers."""

    @pytest.mark.parametrize("code", [
        'detail = str(err)',
        'msg = str(exc)',
        'error = str(error)',
        'text = str(exception)',
        'detail = str(ERR)',
        'msg = str(Exc)',
        'error = str(Error)',
        'text = str(Exception)',
        'detail = repr(err)',
        'msg = repr(exc)',
        'error = repr(error)',
        'text = repr(exception)',
        'detail = repr(ERR)',
        'msg = repr(Exc)',
        'error = repr(Error)',
        'text = repr(Exception)',
    ])
    def test_detects_exception_variable_str_and_repr(self, tmp_path, code):
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
        'value = repr(extract)',
        'value = repr(execute)',
        'value = getattr(e, "name", str(e))',
        'value = getattr(e, "name", repr(e))',
        '# str(e) in comment is okay',
        '# repr(e) in comment is okay',
        'logger.error(str(e))',
        'logger.error(repr(e))',
        'error = str(exc)  # ban-str-e-allow: structured-log',
        'error = repr(exc)  # ban-str-e-allow: structured-log',
        'extra={"error": str(exc)}',
        'extra={"error": repr(exc)}',
    ])
    def test_allows_safe_identifiers(self, tmp_path, code):
        f = tmp_path / "sample.py"
        f.write_text(code)
        issues = check_file(f)
        assert len(issues) == 0, f"Expected 0 issues for {code!r}, got {issues}"
