"""Gate enforcement service for review/approval and export gating."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from app.core.database import db

GateType = Literal["evidence", "formula", "benchmark", "approval", "pii"]
GateStatus = Literal["open", "closed", "waived"]


class GateResult:
    def __init__(
        self, gate_type: GateType, status: GateStatus, reason: str | None = None
    ):
        self.gate_type = gate_type
        self.status = status
        self.reason = reason

    def passed(self) -> bool:
        return self.status in ("closed", "waived")


def check_gates(account_id: str, tenant_id: str) -> list[GateResult]:
    """Evaluate all export/CRM-push gates for an account."""
    results: list[GateResult] = []

    # Evidence gate: at least one evidence item linked
    evidence = db.evidence.list(
        tenant_id=tenant_id,
        filter_fn=lambda e: e.account_id == account_id,
    )
    if evidence:
        results.append(GateResult("evidence", "closed"))
    else:
        results.append(
            GateResult("evidence", "open", "No evidence items linked to this account")
        )

    # Formula gate: at least one formula selected on a driver lever
    drivers = db.drivers.list(
        tenant_id=tenant_id,
        filter_fn=lambda d: d.account_id == account_id,
    )
    has_formula = any(lever.formula_id for driver in drivers for lever in driver.levers)
    if has_formula:
        results.append(GateResult("formula", "closed"))
    else:
        results.append(
            GateResult("formula", "open", "No formulas assigned to value drivers")
        )

    # Benchmark gate: at least one benchmark applied
    roi_calcs = db.roi_calculations.list(
        tenant_id=tenant_id,
        filter_fn=lambda r: r.account_id == account_id,
    )
    has_benchmark = any(calc.calculation_trace for calc in roi_calcs)
    if has_benchmark:
        results.append(GateResult("benchmark", "closed"))
    else:
        results.append(
            GateResult("benchmark", "open", "No benchmark comparison in calculations")
        )

    # Approval gate: at least one approved review request for the account's business case
    reviews = db.review_requests.list(
        tenant_id=tenant_id,
        filter_fn=lambda r: r.account_id == account_id and r.status == "approved",
    )
    if reviews:
        results.append(GateResult("approval", "closed"))
    else:
        results.append(
            GateResult(
                "approval", "open", "Business case has not been approved by a reviewer"
            )
        )

    return results


def get_gate_summary(account_id: str, tenant_id: str) -> dict:
    """Return a serializable gate summary for the frontend."""
    gates = check_gates(account_id, tenant_id)
    return {
        "account_id": account_id,
        "all_passed": all(g.passed() for g in gates),
        "gates": [
            {
                "type": g.gate_type,
                "status": g.status,
                "reason": g.reason,
            }
            for g in gates
        ],
        "checked_at": datetime.now(UTC).isoformat(),
    }
