from __future__ import annotations

from scripts.ci.contract_compliance_gate import _detect_touched_specs


def test_billing_service_changes_include_retained_contract_subset() -> None:
    specs = _detect_touched_specs([
        "services/layer4-agents/src/layer4_agents/services/billing_service.py",
    ])

    assert "layer4-agents.json" in specs
    assert "layer7-billing.json" in specs
