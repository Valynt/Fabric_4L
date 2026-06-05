from __future__ import annotations

from scripts.ci.check_l3_contract_drift import check_drift, main


def test_check_drift_flags_removed_path() -> None:
    snapshot = {"paths": {"/v1/legacy": {"get": {"responses": {"200": {}}}}}}
    current = {"paths": {}}

    assert check_drift(snapshot, current) == ["REMOVED PATH: /v1/legacy"]


def test_check_drift_flags_removed_response_code() -> None:
    snapshot = {"paths": {"/v1/items": {"get": {"responses": {"200": {}, "401": {}}}}}}
    current = {"paths": {"/v1/items": {"get": {"responses": {"200": {}}}}}}

    assert check_drift(snapshot, current) == ["REMOVED RESPONSE CODE: GET /v1/items \u2192 401"]


def test_strict_flag_is_supported(tmp_path, monkeypatch, capsys) -> None:
    contract = tmp_path / "contract.json"
    contract.write_text('{"paths": {}}', encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "check_l3_contract_drift.py",
            "--strict",
            "--snapshot",
            str(contract),
            "--current",
            str(contract),
        ],
    )

    assert main() == 0
    assert "No breaking drift detected" in capsys.readouterr().out
