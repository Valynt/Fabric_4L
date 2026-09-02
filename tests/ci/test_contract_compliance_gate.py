from __future__ import annotations

import importlib

from scripts.ci.contract_compliance_gate import _detect_touched_specs


def test_billing_service_changes_include_retained_contract_subset() -> None:
    specs = _detect_touched_specs([
        "services/layer4-agents/src/layer4_agents/services/billing_service.py",
    ])

    assert "layer4-agents.json" in specs
    assert "layer7-billing.json" in specs


def test_unrelated_layer4_routes_do_not_trigger_billing_contract() -> None:
    specs = _detect_touched_specs([
        "services/layer4-agents/src/layer4_agents/api/routes/analysis.py",
    ])

    assert "layer4-agents.json" in specs
    assert "layer7-billing.json" not in specs


def test_billing_url_uses_layer4_url_when_unset(monkeypatch) -> None:
    monkeypatch.delenv("BILLING_API_URL", raising=False)
    monkeypatch.setenv("LAYER4_API_URL", "http://layer4.example:8004")

    import tests.integration.critical_flows as critical_flows

    importlib.reload(critical_flows)

    assert critical_flows.SERVICE_URLS["billing"] == "http://layer4.example:8004"
