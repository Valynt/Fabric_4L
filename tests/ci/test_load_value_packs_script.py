from pathlib import Path

import pytest
import scripts.load_value_packs as loader


def test_load_pack_to_api_dry_run_success(tmp_path: Path) -> None:
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (pack_dir / "formulas.json").write_text(
        '{"formulas": [{"formula_id": "f1", "name": "N", "description": "D", "formula_type": "roi", "expression": {"string": "a+b", "variables": ["v1"]}, "required_variables": [{"name": "v1"}], "version": "1.0", "status": "active"}]}'
    )
    (pack_dir / "variables.json").write_text(
        '{"variables": [{"variable_name": "v1", "display_name": "Var 1"}]}'
    )

    result = loader.load_pack_to_api("test-pack-v1", pack_dir, "http://example", dry_run=True)

    assert result["status"] == "dry_run"
    assert result["formulas"] == 1
    assert result["variables"] == 1


def test_load_pack_to_api_live_write_mode_is_blocked(tmp_path: Path) -> None:
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (pack_dir / "formulas.json").write_text(
        '{"formulas": [{"formula_id": "f1", "name": "N", "description": "D", "formula_type": "roi", "expression": {"string": "a+b"}, "version": "1.0", "status": "active"}]}'
    )

    result = loader.load_pack_to_api("test-pack-v1", pack_dir, "http://example", dry_run=False)

    assert result["status"] == "error"
    assert "Live API loading is disabled" in result["errors"][0]


def test_load_pack_to_api_invalid_formula_payload_returns_error(tmp_path: Path) -> None:
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (pack_dir / "formulas.json").write_text('{"formulas": [{"name": "N"}]}')

    result = loader.load_pack_to_api("test-pack-v1", pack_dir, "http://example", dry_run=True)

    assert result["status"] == "error"
    assert "missing required fields" in result["errors"][0]


def test_load_pack_to_api_invalid_top_level_payload_returns_error(tmp_path: Path) -> None:
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (pack_dir / "variables.json").write_text('{"not_variables": []}')

    result = loader.load_pack_to_api("test-pack-v1", pack_dir, "http://example", dry_run=True)

    assert result["status"] == "error"
    assert result["errors"] == ["Invalid variables payload: expected variables.variables list"]


def test_main_requires_non_prod_flag(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("sys.argv", ["load_value_packs.py", "--all"])

    with pytest.raises(SystemExit) as exc:
        loader.main()

    assert exc.value.code == 2
    out = capsys.readouterr().out
    assert "non-production-only" in out


def test_main_blocks_ci_execution(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr("sys.argv", ["load_value_packs.py", "--all", "--non-prod"])

    with pytest.raises(SystemExit) as exc:
        loader.main()

    assert exc.value.code == 2
    out = capsys.readouterr().out
    assert "blocked in CI" in out
