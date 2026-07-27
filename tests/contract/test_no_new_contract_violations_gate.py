from pathlib import Path

from scripts.ci.enforce_no_new_contract_violations import scan_file


def test_scan_file_detects_patterns(tmp_path: Path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text("raise Exception('x')\njson.loads(payload)\n")

    found = scan_file(sample, ["raise Exception", "json.loads(", "navigate("])

    assert "raise Exception" in found
    assert "json.loads(" in found
    assert "navigate(" not in found


def test_scan_file_handles_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.py"
    assert scan_file(missing, ["json.loads("]) == []
