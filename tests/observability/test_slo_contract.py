from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT = REPO_ROOT / "monitoring" / "slo" / "slos.contract.json"


def _colon_names(document: str, key: str) -> set[str]:
    names: set[str] = set()
    prefix = f"{key}:"
    for line in document.splitlines():
        stripped = line.strip().lstrip("- ").strip()
        if stripped.startswith(prefix):
            names.add(stripped.split(":", 1)[1].strip())
    return names


def _contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_slo_contract_has_six_unique_ids() -> None:
    slos = _contract()["slos"]
    assert len(slos) == 6
    ids = [slo["id"] for slo in slos]
    assert len(ids) == len(set(ids))


def test_slo_contract_primary_and_burn_records_exist_in_recording_rules() -> None:
    payload = _contract()
    recording_rules = (REPO_ROOT / payload["recording_rules"]).read_text(encoding="utf-8")
    records = _colon_names(recording_rules, "record")
    assert records, "recording-rules.yml must declare record: names"
    for slo in payload["slos"]:
        assert slo["primary_record"] in records, slo["id"]
        assert slo["burn_rate_record"] in records, slo["id"]


def test_slo_contract_alerts_exist_in_alerting_rules() -> None:
    payload = _contract()
    alerting_rules = (REPO_ROOT / payload["alerting_rules"]).read_text(encoding="utf-8")
    alerts = _colon_names(alerting_rules, "alert")
    for slo in payload["slos"]:
        assert slo["alert"] in alerts, slo["id"]
    for alert_name in payload["burn_rate_alerts"]:
        assert alert_name in alerts, alert_name


def test_slo_contract_dashboard_metrics_exist_in_grafana_dashboards() -> None:
    payload = _contract()
    dashboard_blobs: list[str] = []
    for rel in payload["dashboards"]:
        path = REPO_ROOT / rel
        assert path.is_file(), rel
        dashboard_blobs.append(path.read_text(encoding="utf-8"))
    joined = "\n".join(dashboard_blobs)
    for metric in payload["dashboard_metrics"]:
        assert metric in joined, metric
