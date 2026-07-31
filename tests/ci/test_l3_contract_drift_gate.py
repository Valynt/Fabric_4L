from __future__ import annotations

import json
from pathlib import Path

import pytest
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


def test_check_drift_allows_registered_layer3_path_renames() -> None:
    snapshot = {"paths": {"/graph": {"get": {"responses": {"200": {}}}}}}
    current = {"paths": {"/v1/graph": {"get": {"responses": {"200": {}}}}}}

    assert check_drift(snapshot, current) == []


def test_check_drift_allows_registered_layer3_error_response_standardization() -> None:
    snapshot = {"paths": {"/v1/variables": {"get": {"responses": {"200": {}, "401": {}}}}}}
    current = {"paths": {"/v1/variables": {"get": {"responses": {"200": {}}}}}}

    assert check_drift(snapshot, current) == []


@pytest.mark.parametrize(
    "path",
    ["/v1/schema/status", "/v1/schema/init", "/v1/schema/statistics"],
)
def test_check_drift_rejects_removed_schema_routes_without_verified_alias(path: str) -> None:
    snapshot = {"paths": {path: {"get": {"responses": {"200": {}}}}}}

    assert check_drift(snapshot, {"paths": {}}) == [f"REMOVED PATH: {path}"]


def test_layer3_current_contract_exposes_legacy_schema_routes() -> None:
    contract = json.loads(
        Path("contracts/openapi/layer3-knowledge.json").read_text(encoding="utf-8")
    )

    assert "get" in contract["paths"]["/v1/schema/status"]
    assert "post" in contract["paths"]["/v1/schema/init"]
    assert "get" in contract["paths"]["/v1/schema/statistics"]
