"""Explicit action-level human approval policies for Layer 4 high-impact actions.

Maps the five required high-impact action classes to gate types and
enforcement rules. Replaces category-based gating with action-level coverage.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..harness.models import ActionClass, GateType


class ActionApprovalPolicy(BaseModel):
    """Policy for a single high-impact action class."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    action_class: ActionClass
    required_gate_type: GateType
    min_approver_role: str | None = Field(default=None)
    auto_expire_seconds: int | None = Field(default=86400, ge=0)
    requires_secondary_approval: bool = Field(default=False)
    description: str = Field(default="")


# Canonical policy registry: every required action class has an explicit policy.
ACTION_APPROVAL_POLICIES: dict[ActionClass, ActionApprovalPolicy] = {
    ActionClass.APPROVE_HYPOTHESES: ActionApprovalPolicy(
        action_class=ActionClass.APPROVE_HYPOTHESES,
        required_gate_type=GateType.APPROVE_CLAIMS,
        description="Approval required before hypotheses are promoted to claims",
    ),
    ActionClass.PUBLISH_BUSINESS_CASE: ActionApprovalPolicy(
        action_class=ActionClass.PUBLISH_BUSINESS_CASE,
        required_gate_type=GateType.APPROVE_CUSTOMER_OUTPUT,
        min_approver_role="content_admin",
        description="Approval required before a business case is published",
    ),
    ActionClass.APPLY_BENCHMARK_ASSUMPTIONS: ActionApprovalPolicy(
        action_class=ActionClass.APPLY_BENCHMARK_ASSUMPTIONS,
        required_gate_type=GateType.APPROVE_ASSUMPTIONS,
        description="Approval required before benchmark assumptions are applied to calculations",
    ),
    ActionClass.GENERATE_CUSTOMER_FACING_DELIVERABLE: ActionApprovalPolicy(
        action_class=ActionClass.GENERATE_CUSTOMER_FACING_DELIVERABLE,
        required_gate_type=GateType.APPROVE_CUSTOMER_OUTPUT,
        min_approver_role="content_admin",
        requires_secondary_approval=True,
        description="Approval required before generating any customer-facing output",
    ),
    ActionClass.CHANGE_ACCOUNT_VALUE_MODEL: ActionApprovalPolicy(
        action_class=ActionClass.CHANGE_ACCOUNT_VALUE_MODEL,
        required_gate_type=GateType.APPROVE_CLAIMS,
        min_approver_role="admin",
        description="Approval required before modifying an account's value model",
    ),
}


def get_policy(action_class: ActionClass | str | None) -> ActionApprovalPolicy | None:
    """Lookup the approval policy for an action class.

    Returns None when no action class is supplied.
    Fails closed for unknown/high-impact action identifiers.
    """
    if action_class is None:
        return None
    if isinstance(action_class, str):
        try:
            action_class = ActionClass(action_class)
        except ValueError:
            raise ApprovalRequiredError(
                action_class=ActionClass.GENERATE_CUSTOMER_FACING_DELIVERABLE,
                gate_type=GateType.APPROVE_CUSTOMER_OUTPUT,
                run_id="unknown",
                message=(
                    f"Unmapped high-impact action '{action_class}' is denied by default "
                    "until explicitly mapped to a gate policy"
                ),
            )
    policy = ACTION_APPROVAL_POLICIES.get(action_class)
    if policy is None:
        raise ApprovalRequiredError(
            action_class=action_class,
            gate_type=GateType.APPROVE_CUSTOMER_OUTPUT,
            run_id="unknown",
            message=(
                f"Action '{action_class.value}' is high-impact but has no policy mapping; denied by default"
            ),
        )
    return policy


def requires_approval(action_class: ActionClass | str | None) -> bool:
    """Check whether an action class requires human approval."""
    if action_class is None:
        return False
    try:
        return get_policy(action_class) is not None
    except ApprovalRequiredError:
        return True


class ApprovalRequiredError(ValueError):
    """Raised when a high-impact action is attempted without an approved gate."""

    def __init__(
        self,
        *,
        action_class: ActionClass,
        gate_type: GateType,
        run_id: str,
        message: str | None = None,
    ) -> None:
        self.action_class = action_class
        self.gate_type = gate_type
        self.run_id = run_id
        super().__init__(
            message
            or f"Approval required for {action_class.value} (gate={gate_type.value}, run={run_id})"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "APPROVAL_REQUIRED",
            "action_class": self.action_class.value,
            "gate_type": self.gate_type.value,
            "run_id": self.run_id,
        }
