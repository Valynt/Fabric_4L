"""
Approval and publication policies for the Fabric_4L Harness.

Rules:
  - High-risk tools require approval before invocation.
  - Customer-facing outputs require validation or approved override.
  - Failed validation blocks publication.
  - Unavailable validation blocks publication and routes to review.
  - Insufficient evidence blocks publication and routes to review.
"""

from __future__ import annotations

from .models import (
    ActionClass,
    ClaimValidationResult,
    GateStatus,
    HarnessRun,
    HumanGate,
    ToolContract,
    ToolRiskLevel,
    ToolSideEffectClass,
    ValidationState,
    ValidationSummary,
)
from ..policies import approval_actions


class ApprovalRequiredError(PermissionError):
    """Raised when a tool invocation requires approval that is not present."""

    pass


class PublicationBlockedError(PermissionError):
    """Raised when publication is blocked by policy."""

    pass


class PolicyViolationError(ValueError):
    """Raised when a policy is violated."""

    pass


def enforce_action_approval(
    *,
    run_id: str,
    action_class: ActionClass | str | None,
    gate: HumanGate | None,
) -> dict[str, str] | None:
    """Resolve and enforce action-level approval policy.

    Returns evidence payload when a policy applies; otherwise None.
    Fails closed when approval is required and a valid approved gate is missing.
    """
    policy = approval_actions.get_policy(action_class)
    if policy is None:
        return None
    if gate is None or gate.status != GateStatus.APPROVED:
        raise approval_actions.ApprovalRequiredError(
            action_class=policy.action_class,
            gate_type=policy.required_gate_type,
            run_id=run_id,
        )
    if gate.gate_type != policy.required_gate_type:
        raise approval_actions.ApprovalRequiredError(
            action_class=policy.action_class,
            gate_type=policy.required_gate_type,
            run_id=run_id,
            message=(
                f"Approval gate type mismatch for {policy.action_class.value}: "
                f"expected={policy.required_gate_type.value}, got={gate.gate_type.value}, run={run_id}"
            ),
        )
    return {
        "run_id": run_id,
        "gate_id": gate.id,
        "gate_type": gate.gate_type.value,
        "action_class": policy.action_class.value,
    }


def requires_approval(tool: ToolContract) -> bool:
    """
    Return True if the tool requires explicit approval before invocation.

    High-risk tools and customer-facing output tools always require approval.
    """
    if tool.risk_level in (ToolRiskLevel.HIGH, ToolRiskLevel.CRITICAL):
        return True
    if tool.side_effect_class == ToolSideEffectClass.CUSTOMER_FACING_OUTPUT:
        return True
    if tool.approval_policy_id is not None:
        return True
    return False


def evaluate_tool_invocation_policy(
    tool: ToolContract,
    has_approval: bool = False,
    tenant_context_present: bool = False,
    account_context_present: bool = False,
) -> ToolContract:
    """
    Evaluate whether a tool invocation is permitted.

    Returns:
        The ToolContract if invocation is permitted.

    Raises:
        ApprovalRequiredError: if approval is required but not present.
        PolicyViolationError: if required context is missing.
    """
    if tool.requires_tenant_context and not tenant_context_present:
        raise PolicyViolationError(
            f"Tool {tool.tool_id} requires tenant context but none provided"
        )

    if tool.requires_account_context and not account_context_present:
        raise PolicyViolationError(
            f"Tool {tool.tool_id} requires account context but none provided"
        )

    if requires_approval(tool) and not has_approval:
        raise ApprovalRequiredError(
            f"Tool {tool.tool_id} (risk={tool.risk_level.value}, "
            f"side_effects={tool.side_effect_class.value}) requires explicit approval"
        )

    return tool


def evaluate_transition_policy(
    run: HarnessRun,
    validation_results: list[ClaimValidationResult] | None = None,
    human_gate: HumanGate | None = None,
    override_policy_allowed: bool = False,
) -> None:
    """
    Evaluate whether a transition policy allows the current operation.

    Used before PUBLISH_OUTPUT transitions.
    """
    if human_gate is not None and human_gate.status == GateStatus.REJECTED:
        if not override_policy_allowed:
            raise PublicationBlockedError(
                f"Publication blocked: human gate {human_gate.id} was rejected"
            )

    if validation_results is not None:
        for vr in validation_results:
            if vr.validation_state == ValidationState.FAILED:
                if not override_policy_allowed:
                    raise PublicationBlockedError(
                        f"Publication blocked: claim {vr.claim_id} failed validation"
                    )


def can_publish_output(
    run: HarnessRun,
    validation_results: list[ClaimValidationResult] | None = None,
    human_gate_decision: HumanGate | None = None,
    override_policy: bool = False,
) -> bool:
    """
    Determine whether customer-facing output can be published.

    Rules (in order):
      1. If L5 validation passed for all claims → permit.
      2. If explicit human approval exists AND override policy allows → permit.
      3. If any validation failed → block (unless override).
      4. If validation unavailable → block.
      5. If insufficient evidence → block.

    Returns:
        True if publication is permitted.
    """
    # Case 1: All validations passed
    if validation_results is not None and all(
        vr.validation_state == ValidationState.PASSED for vr in validation_results
    ):
        return True

    # Case 2: Human override with policy
    if (
        human_gate_decision is not None
        and human_gate_decision.status == GateStatus.APPROVED
        and override_policy
    ):
        return True

    # Case 3: Any failed validation
    if validation_results is not None:
        for vr in validation_results:
            if vr.validation_state == ValidationState.FAILED:
                # Only allow if override policy is explicitly set
                return override_policy
            if vr.validation_state in (
                ValidationState.INSUFFICIENT_EVIDENCE,
                ValidationState.NEEDS_REVIEW,
            ):
                return False

    # Case 4: No validation results provided
    if validation_results is None or len(validation_results) == 0:
        # No validation at all → block
        return False

    return False


def requires_human_review(
    validation_results: list[ClaimValidationResult] | None,
) -> bool:
    """Return True if the validation results require human review before publishing."""
    if validation_results is None:
        return True  # No validation → needs review
    for vr in validation_results:
        if vr.validation_state in (
            ValidationState.NEEDS_REVIEW,
            ValidationState.INSUFFICIENT_EVIDENCE,
        ):
            return True
    return False


def aggregate_validation_results(
    results: list[ClaimValidationResult],
) -> ValidationSummary:
    """Aggregate per-claim validation results into a publish decision.

    Rules:
      - all passed → can_publish=True, requires_human_review=False
      - any failed → can_publish=False, requires_human_review=False
      - any needs_review or insufficient_evidence → can_publish=False, requires_human_review=True
      - empty results → can_publish=False, requires_human_review=True
    """
    if not results:
        return ValidationSummary(
            total=0,
            passed=0,
            failed=0,
            needs_review=0,
            insufficient_evidence=0,
            can_publish=False,
            requires_human_review=True,
        )

    counts: dict[ValidationState, int] = dict.fromkeys(ValidationState, 0)
    for vr in results:
        counts[vr.validation_state] += 1

    total = len(results)
    passed = counts[ValidationState.PASSED]
    failed = counts[ValidationState.FAILED]
    needs_review = counts[ValidationState.NEEDS_REVIEW]
    insufficient = counts[ValidationState.INSUFFICIENT_EVIDENCE]

    can_publish = (passed == total) and total > 0
    human_review = (needs_review > 0 or insufficient > 0) and not can_publish

    return ValidationSummary(
        total=total,
        passed=passed,
        failed=failed,
        needs_review=needs_review,
        insufficient_evidence=insufficient,
        can_publish=can_publish,
        requires_human_review=human_review,
    )
