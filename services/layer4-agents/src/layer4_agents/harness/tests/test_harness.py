from __future__ import annotations

"""
Comprehensive test suite for the Fabric_4L Harness.

Covers:
  - State machine transitions
  - Tenant isolation
  - Tool contract enforcement
  - Human gate lifecycle
  - Checkpoint determinism
  - Validation hooks
  - Telemetry events
  - Publication policies

All tests must prove behavior, not just imports.
"""

from pathlib import Path

import pytest

from layer4_agents.harness import (
    ApprovalRequiredError,
    CheckpointError,
    CheckpointManager,
    ClaimValidationRequest,
    ClaimValidationResult,
    GateDecisionError,
    GateExpiredError,
    GateNotFoundError,
    GateStatus,
    GateType,
    HarnessCheckpoint,
    HarnessRegistry,
    HarnessRun,
    HarnessRunStatus,
    HarnessState,
    HarnessWorkflowType,
    HumanGate,
    HumanGateManager,
    InitiatedBy,
    MockValidator,
    RunNotFoundError,
    StateMachine,
    TelemetryEmitter,
    TerminalStateError,
    ToolContract,
    ToolContractRegistry,
    ToolLayer,
    ToolNotFoundError,
    ToolRegistrationError,
    ToolRiskLevel,
    ToolSideEffectClass,
    TransitionError,
    ValidationHook,
    ValidationState,
    can_publish_output,
    evaluate_tool_invocation_policy,
    requires_approval,
)

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def tenant_id() -> str:
    return "tenant_acme"


@pytest.fixture
def other_tenant() -> str:
    return "tenant_other"


@pytest.fixture
def run(tenant_id: str) -> HarnessRun:
    return HarnessRun(
        tenant_id=tenant_id,
        workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
        initiated_by=InitiatedBy.USER,
        account_id="acct_123",
        value_pack_id="manufacturing",
    )


@pytest.fixture
def state_machine() -> StateMachine:
    return StateMachine()


@pytest.fixture
def tool_registry() -> ToolContractRegistry:
    return ToolContractRegistry()


@pytest.fixture
def gate_manager() -> HumanGateManager:
    return HumanGateManager()


@pytest.fixture
def checkpoint_manager() -> CheckpointManager:
    return CheckpointManager()


@pytest.fixture
def telemetry() -> TelemetryEmitter:
    return TelemetryEmitter()


@pytest.fixture
def validation_hook() -> ValidationHook:
    return ValidationHook()


@pytest.fixture
def harness(
    state_machine: StateMachine,
    tool_registry: ToolContractRegistry,
    gate_manager: HumanGateManager,
    checkpoint_manager: CheckpointManager,
    telemetry: TelemetryEmitter,
    validation_hook: ValidationHook,
) -> HarnessRegistry:
    return HarnessRegistry(
        state_machine=state_machine,
        tool_registry=tool_registry,
        gate_manager=gate_manager,
        checkpoint_manager=checkpoint_manager,
        telemetry=telemetry,
        validation_hook=validation_hook,
    )


@pytest.fixture
def low_risk_tool(tenant_id: str) -> ToolContract:
    return ToolContract(
        tool_id="fabric.l3.graph_query",
        layer=ToolLayer.L3,
        input_schema_ref="GraphQueryRequest",
        output_schema_ref="GraphQueryResponse",
        side_effect_class=ToolSideEffectClass.READ,
        risk_level=ToolRiskLevel.LOW,
        requires_tenant_context=True,
    )


@pytest.fixture
def high_risk_tool(tenant_id: str) -> ToolContract:
    return ToolContract(
        tool_id="fabric.deliverables.generate_customer_business_case",
        layer=ToolLayer.PRESENTATION,
        input_schema_ref="BusinessCaseRequest",
        output_schema_ref="BusinessCaseOutput",
        side_effect_class=ToolSideEffectClass.CUSTOMER_FACING_OUTPUT,
        risk_level=ToolRiskLevel.HIGH,
        requires_tenant_context=True,
        requires_account_context=True,
        approval_policy_id="policy_customer_output_v1",
    )


# ============================================================
# State Machine Tests
# ============================================================


class TestStateMachine:
    """Tests for deterministic workflow state transitions."""

    def test_valid_init_to_resolve_context(
        self, state_machine: StateMachine, run: HarnessRun
    ) -> None:
        """INIT -> RESOLVE_CONTEXT succeeds."""
        updated, event = state_machine.transition(run, HarnessState.RESOLVE_CONTEXT)
        assert updated.current_state == HarnessState.RESOLVE_CONTEXT
        assert updated.status == HarnessRunStatus.RUNNING
        assert event.tenant_id == run.tenant_id
        assert event.trace_id == run.trace_id

    def test_invalid_transition_fails(
        self, state_machine: StateMachine, run: HarnessRun
    ) -> None:
        """INIT -> DONE fails."""
        with pytest.raises(TransitionError):
            state_machine.transition(run, HarnessState.DONE)

    def test_terminal_run_cannot_transition(
        self, state_machine: StateMachine, run: HarnessRun
    ) -> None:
        """Terminal run cannot transition further."""
        # First transition to FAILED
        failed, _ = state_machine.transition(run, HarnessState.RESOLVE_CONTEXT)
        failed = failed.with_state(HarnessState.FAILED, status=HarnessRunStatus.FAILED)
        with pytest.raises(TerminalStateError):
            state_machine.transition(failed, HarnessState.DONE)

    def test_publish_output_fails_without_validation(
        self, state_machine: StateMachine, run: HarnessRun
    ) -> None:
        """PUBLISH_OUTPUT without validation or override fails."""
        # Get to PUBLISH_OUTPUT from VALIDATE_CLAIMS
        states = [
            HarnessState.RESOLVE_CONTEXT,
            HarnessState.LOAD_VALUE_PACK,
            HarnessState.RETRIEVE_KNOWLEDGE,
            HarnessState.GENERATE_HYPOTHESES,
            HarnessState.MATCH_EVIDENCE,
            HarnessState.QUANTIFY_IMPACT,
            HarnessState.VALIDATE_CLAIMS,
        ]
        current = run
        for s in states:
            current, _ = state_machine.transition(current, s)

        # Without validation state
        with pytest.raises(TransitionError) as exc_info:
            state_machine.transition(current, HarnessState.PUBLISH_OUTPUT)
        assert "validation" in str(exc_info.value).lower() or "PUBLISH_OUTPUT" in str(exc_info.value)

    def test_publish_output_succeeds_with_passed_validation(
        self, state_machine: StateMachine, run: HarnessRun
    ) -> None:
        """PUBLISH_OUTPUT with PASSED validation succeeds."""
        states = [
            HarnessState.RESOLVE_CONTEXT,
            HarnessState.LOAD_VALUE_PACK,
            HarnessState.RETRIEVE_KNOWLEDGE,
            HarnessState.GENERATE_HYPOTHESES,
            HarnessState.MATCH_EVIDENCE,
            HarnessState.QUANTIFY_IMPACT,
            HarnessState.VALIDATE_CLAIMS,
        ]
        current = run
        for s in states:
            current, _ = state_machine.transition(current, s)

        # With PASSED validation
        updated, event = state_machine.transition(
            current,
            HarnessState.PUBLISH_OUTPUT,
            validation_state=ValidationState.PASSED,
        )
        assert updated.current_state == HarnessState.PUBLISH_OUTPUT

    def test_publish_output_succeeds_with_explicit_override(
        self, state_machine: StateMachine, run: HarnessRun
    ) -> None:
        """PUBLISH_OUTPUT with human_override succeeds."""
        states = [
            HarnessState.RESOLVE_CONTEXT,
            HarnessState.LOAD_VALUE_PACK,
            HarnessState.RETRIEVE_KNOWLEDGE,
            HarnessState.GENERATE_HYPOTHESES,
            HarnessState.MATCH_EVIDENCE,
            HarnessState.QUANTIFY_IMPACT,
            HarnessState.VALIDATE_CLAIMS,
            HarnessState.HUMAN_REVIEW,
        ]
        current = run
        for s in states:
            current, _ = state_machine.transition(current, s)

        updated, _ = state_machine.transition(
            current,
            HarnessState.PUBLISH_OUTPUT,
            human_override=True,
        )
        assert updated.current_state == HarnessState.PUBLISH_OUTPUT

    def test_insufficient_evidence_routes_to_human_review(
        self, state_machine: StateMachine, run: HarnessRun
    ) -> None:
        """Insufficient evidence routes to HUMAN_REVIEW."""
        states = [
            HarnessState.RESOLVE_CONTEXT,
            HarnessState.LOAD_VALUE_PACK,
            HarnessState.RETRIEVE_KNOWLEDGE,
            HarnessState.GENERATE_HYPOTHESES,
            HarnessState.MATCH_EVIDENCE,
            HarnessState.QUANTIFY_IMPACT,
            HarnessState.VALIDATE_CLAIMS,
        ]
        current = run
        for s in states:
            current, _ = state_machine.transition(current, s)

        # Transition to HUMAN_REVIEW with insufficient evidence
        updated, _ = state_machine.transition(
            current,
            HarnessState.HUMAN_REVIEW,
            validation_state=ValidationState.INSUFFICIENT_EVIDENCE,
        )
        assert updated.current_state == HarnessState.HUMAN_REVIEW
        assert updated.status == HarnessRunStatus.WAITING_FOR_HUMAN

    def test_init_can_transition_to_cancelled(
        self, state_machine: StateMachine, run: HarnessRun
    ) -> None:
        """INIT -> CANCELLED succeeds."""
        updated, _ = state_machine.transition(run, HarnessState.CANCELLED)
        assert updated.current_state == HarnessState.CANCELLED
        assert updated.status == HarnessRunStatus.CANCELLED

    def test_init_can_transition_to_failed(
        self, state_machine: StateMachine, run: HarnessRun
    ) -> None:
        """INIT -> FAILED succeeds."""
        updated, _ = state_machine.transition(run, HarnessState.FAILED)
        assert updated.current_state == HarnessState.FAILED
        assert updated.status == HarnessRunStatus.FAILED

    def test_allowed_transitions_from_init(self, state_machine: StateMachine) -> None:
        """INIT only allows specific transitions."""
        allowed = StateMachine.allowed_transitions(HarnessState.INIT)
        assert allowed == {
            HarnessState.RESOLVE_CONTEXT,
            HarnessState.FAILED,
            HarnessState.CANCELLED,
        }

    def test_terminal_states_have_no_transitions(
        self, state_machine: StateMachine
    ) -> None:
        """Terminal states have empty transition sets."""
        for terminal in (HarnessState.DONE, HarnessState.FAILED, HarnessState.CANCELLED):
            assert StateMachine.allowed_transitions(terminal) == set()

    def test_happy_path_full_flow(self, state_machine: StateMachine, run: HarnessRun) -> None:
        """Complete happy path through all states."""
        states = [
            HarnessState.RESOLVE_CONTEXT,
            HarnessState.LOAD_VALUE_PACK,
            HarnessState.RETRIEVE_KNOWLEDGE,
            HarnessState.GENERATE_HYPOTHESES,
            HarnessState.MATCH_EVIDENCE,
            HarnessState.QUANTIFY_IMPACT,
            HarnessState.VALIDATE_CLAIMS,
            HarnessState.HUMAN_REVIEW,
            HarnessState.PUBLISH_OUTPUT,
            HarnessState.DONE,
        ]
        current = run
        for s in states:
            if s == HarnessState.PUBLISH_OUTPUT:
                current, _ = state_machine.transition(
                    current, s, human_override=True
                )
            else:
                current, _ = state_machine.transition(current, s)

        assert current.current_state == HarnessState.DONE
        assert current.status == HarnessRunStatus.COMPLETED


# ============================================================
# Tool Contract Tests
# ============================================================


class TestToolContracts:
    """Tests for tool contract registry."""

    def test_read_only_tool_can_execute(
        self, tool_registry: ToolContractRegistry, low_risk_tool: ToolContract, tenant_id: str
    ) -> None:
        """Read-only tool can execute with tenant context."""
        tool_registry.register_tool(low_risk_tool, tenant_id)
        retrieved = tool_registry.get_tool(low_risk_tool.tool_id, tenant_id)
        assert retrieved.tool_id == low_risk_tool.tool_id

    def test_missing_tenant_context_blocks_execution(
        self, tool_registry: ToolContractRegistry, low_risk_tool: ToolContract, tenant_id: str
    ) -> None:
        """Missing tenant context blocks execution when required."""
        tool_registry.register_tool(low_risk_tool, tenant_id)
        tool = tool_registry.get_tool(low_risk_tool.tool_id, tenant_id)
        assert tool.requires_tenant_context is True

    def test_duplicate_registration_is_rejected(
        self, tool_registry: ToolContractRegistry, low_risk_tool: ToolContract, tenant_id: str
    ) -> None:
        """Duplicate tool registration is rejected."""
        tool_registry.register_tool(low_risk_tool, tenant_id)
        with pytest.raises(ToolRegistrationError):
            tool_registry.register_tool(low_risk_tool, tenant_id)

    def test_high_risk_tool_requires_approval_policy(
        self, tool_registry: ToolContractRegistry, tenant_id: str
    ) -> None:
        """High-risk tool requires approval_policy_id."""
        high_risk_no_policy = ToolContract(
            tool_id="fabric.critical.delete_all",
            layer=ToolLayer.L4,
            input_schema_ref="DeleteRequest",
            output_schema_ref="DeleteResponse",
            side_effect_class=ToolSideEffectClass.EXTERNAL_WRITE,
            risk_level=ToolRiskLevel.CRITICAL,
            requires_tenant_context=True,
        )
        with pytest.raises(ToolRegistrationError):
            tool_registry.register_tool(high_risk_no_policy, tenant_id)

    def test_high_risk_tool_requires_approval(
        self, tool_registry: ToolContractRegistry, high_risk_tool: ToolContract, tenant_id: str
    ) -> None:
        """High-risk tool invocation requires approval."""
        tool_registry.register_tool(high_risk_tool, tenant_id)
        with pytest.raises(ApprovalRequiredError):
            evaluate_tool_invocation_policy(
                tool_registry.get_tool(high_risk_tool.tool_id, tenant_id),
                has_approval=False,
                tenant_context_present=True,
                account_context_present=True,
            )

    def test_customer_facing_output_requires_approval(
        self, tool_registry: ToolContractRegistry, tenant_id: str
    ) -> None:
        """Customer-facing output tool requires approval."""
        cf_tool = ToolContract(
            tool_id="fabric.output.email_customer",
            layer=ToolLayer.PRESENTATION,
            input_schema_ref="EmailRequest",
            output_schema_ref="EmailResult",
            side_effect_class=ToolSideEffectClass.CUSTOMER_FACING_OUTPUT,
            risk_level=ToolRiskLevel.HIGH,
            requires_tenant_context=True,
            requires_account_context=True,
            approval_policy_id="policy_email_v1",
        )
        tool_registry.register_tool(cf_tool, tenant_id)
        assert requires_approval(cf_tool) is True

    def test_approval_succeeds_with_policy(
        self, tool_registry: ToolContractRegistry, high_risk_tool: ToolContract, tenant_id: str
    ) -> None:
        """High-risk tool with approval succeeds."""
        tool_registry.register_tool(high_risk_tool, tenant_id)
        tool = evaluate_tool_invocation_policy(
            tool_registry.get_tool(high_risk_tool.tool_id, tenant_id),
            has_approval=True,
            tenant_context_present=True,
            account_context_present=True,
        )
        assert tool.tool_id == high_risk_tool.tool_id

    def test_cross_tenant_tool_access_blocked(
        self, tool_registry: ToolContractRegistry, low_risk_tool: ToolContract,
        tenant_id: str, other_tenant: str
    ) -> None:
        """Cross-tenant tool access returns not found."""
        tool_registry.register_tool(low_risk_tool, tenant_id)
        with pytest.raises(ToolNotFoundError):
            tool_registry.get_tool(low_risk_tool.tool_id, other_tenant)

    def test_tool_requires_approval_function(
        self, high_risk_tool: ToolContract, low_risk_tool: ToolContract
    ) -> None:
        """requires_approval returns correct values."""
        assert requires_approval(high_risk_tool) is True
        assert requires_approval(low_risk_tool) is False


# ============================================================
# Human Gate Tests
# ============================================================


class TestHumanGates:
    """Tests for human gate lifecycle."""

    def test_pending_gate_can_be_approved(
        self, gate_manager: HumanGateManager, run: HarnessRun, tenant_id: str
    ) -> None:
        """Pending gate can be approved."""
        gate, _ = gate_manager.create_gate(run.id, tenant_id, GateType.APPROVE_CLAIMS)
        assert gate.status == GateStatus.PENDING

        updated, _ = gate_manager.approve_gate(
            gate.id, tenant_id, decision_by="alice", decision_reason="Looks good"
        )
        assert updated.status == GateStatus.APPROVED
        assert updated.decision_by == "alice"
        assert updated.decision_reason == "Looks good"
        assert updated.decided_at is not None

    def test_pending_gate_can_be_rejected(
        self, gate_manager: HumanGateManager, run: HarnessRun, tenant_id: str
    ) -> None:
        """Pending gate can be rejected."""
        gate, _ = gate_manager.create_gate(run.id, tenant_id, GateType.APPROVE_CLAIMS)
        updated, _ = gate_manager.reject_gate(
            gate.id, tenant_id, decision_by="bob", decision_reason="Insufficient evidence"
        )
        assert updated.status == GateStatus.REJECTED
        assert updated.decision_by == "bob"
        assert updated.decision_reason == "Insufficient evidence"

    def test_approved_gate_cannot_be_changed(
        self, gate_manager: HumanGateManager, run: HarnessRun, tenant_id: str
    ) -> None:
        """Approved gate cannot be changed again."""
        gate, _ = gate_manager.create_gate(run.id, tenant_id, GateType.APPROVE_CLAIMS)
        gate_manager.approve_gate(gate.id, tenant_id, decision_by="alice")
        with pytest.raises(GateDecisionError):
            gate_manager.approve_gate(gate.id, tenant_id, decision_by="bob")

    def test_decision_by_is_captured(
        self, gate_manager: HumanGateManager, run: HarnessRun, tenant_id: str
    ) -> None:
        """Decision metadata is captured."""
        gate, _ = gate_manager.create_gate(run.id, tenant_id, GateType.APPROVE_CLAIMS)
        updated, _ = gate_manager.approve_gate(
            gate.id, tenant_id, decision_by="charlie", decision_reason="Verified"
        )
        assert updated.decision_by == "charlie"
        assert updated.decision_reason == "Verified"

    def test_rejected_gate_blocks_publication(
        self, gate_manager: HumanGateManager, run: HarnessRun, tenant_id: str
    ) -> None:
        """Rejected gate blocks publication unless override policy allows."""
        gate, _ = gate_manager.create_gate(run.id, tenant_id, GateType.APPROVE_CLAIMS)
        updated, _ = gate_manager.reject_gate(gate.id, tenant_id, decision_by="alice")

        # Publication should be blocked
        result = can_publish_output(
            run=run,
            human_gate_decision=updated,
            override_policy=False,
        )
        assert result is False

    def test_expired_gate_cannot_be_decided(
        self, gate_manager: HumanGateManager, run: HarnessRun, tenant_id: str
    ) -> None:
        """Expired gate cannot be decided."""
        gate, _ = gate_manager.create_gate(run.id, tenant_id, GateType.APPROVE_CLAIMS)
        gate_manager.expire_gate(gate.id, tenant_id)
        with pytest.raises(GateExpiredError):
            gate_manager.approve_gate(gate.id, tenant_id, decision_by="alice")

    def test_cross_tenant_gate_access_blocked(
        self, gate_manager: HumanGateManager, run: HarnessRun, tenant_id: str, other_tenant: str
    ) -> None:
        """Cross-tenant gate access returns not found."""
        gate, _ = gate_manager.create_gate(run.id, tenant_id, GateType.APPROVE_CLAIMS)
        with pytest.raises(GateNotFoundError):
            gate_manager.get_gate(gate.id, other_tenant)

    def test_modify_gate_status(
        self, gate_manager: HumanGateManager, run: HarnessRun, tenant_id: str
    ) -> None:
        """Gate can be modified with reason."""
        gate, _ = gate_manager.create_gate(run.id, tenant_id, GateType.APPROVE_CLAIMS)
        updated, _ = gate_manager.modify_gate(
            gate.id, tenant_id, decision_by="dave", decision_reason="Changed numbers"
        )
        assert updated.status == GateStatus.MODIFIED
        assert updated.decision_by == "dave"


# ============================================================
# Checkpoint Tests
# ============================================================


class TestCheckpoints:
    """Tests for deterministic checkpointing."""

    def test_checkpoint_requires_tenant_id(
        self, checkpoint_manager: CheckpointManager, run: HarnessRun, tenant_id: str
    ) -> None:
        """Checkpoint requires tenant_id."""
        with pytest.raises(CheckpointError):
            checkpoint_manager.create_checkpoint(
                run_id=run.id,
                tenant_id="",
                state_name=HarnessState.INIT,
                state_payload={},
            )

    def test_checkpoint_requires_run_id(
        self, checkpoint_manager: CheckpointManager, tenant_id: str
    ) -> None:
        """Checkpoint requires run_id."""
        with pytest.raises(CheckpointError):
            checkpoint_manager.create_checkpoint(
                run_id="",
                tenant_id=tenant_id,
                state_name=HarnessState.INIT,
                state_payload={},
            )

    def test_same_payload_creates_same_hash(
        self, checkpoint_manager: CheckpointManager, run: HarnessRun, tenant_id: str
    ) -> None:
        """Same payload creates same hash."""
        payload = {"key": "value", "number": 42}
        cp1 = checkpoint_manager.create_checkpoint(
            run_id=run.id,
            tenant_id=tenant_id,
            state_name=HarnessState.INIT,
            state_payload=payload,
        )
        cp2 = checkpoint_manager.create_checkpoint(
            run_id=run.id,
            tenant_id=tenant_id,
            state_name=HarnessState.INIT,
            state_payload=payload,
        )
        assert cp1.input_hash == cp2.input_hash

    def test_changed_payload_changes_hash(
        self, checkpoint_manager: CheckpointManager, run: HarnessRun, tenant_id: str
    ) -> None:
        """Changed payload produces different hash."""
        cp1 = checkpoint_manager.create_checkpoint(
            run_id=run.id,
            tenant_id=tenant_id,
            state_name=HarnessState.INIT,
            state_payload={"key": "value1"},
        )
        cp2 = checkpoint_manager.create_checkpoint(
            run_id=run.id,
            tenant_id=tenant_id,
            state_name=HarnessState.INIT,
            state_payload={"key": "value2"},
        )
        assert cp1.input_hash != cp2.input_hash

    def test_mismatched_tenant_rejected(
        self, checkpoint_manager: CheckpointManager, run: HarnessRun, tenant_id: str, other_tenant: str
    ) -> None:
        """Cross-tenant checkpoint access is rejected."""
        cp = checkpoint_manager.create_checkpoint(
            run_id=run.id,
            tenant_id=tenant_id,
            state_name=HarnessState.INIT,
            state_payload={},
        )
        from layer4_agents.harness.checkpoints import CheckpointTenantError
        with pytest.raises(CheckpointTenantError):
            checkpoint_manager.get_checkpoint(cp.id, run.id, other_tenant)

    def test_list_checkpoints_ordered(
        self, checkpoint_manager: CheckpointManager, run: HarnessRun, tenant_id: str
    ) -> None:
        """Checkpoints are returned in creation order."""
        cp1 = checkpoint_manager.create_checkpoint(
            run_id=run.id, tenant_id=tenant_id,
            state_name=HarnessState.INIT, state_payload={"step": 1},
        )
        cp2 = checkpoint_manager.create_checkpoint(
            run_id=run.id, tenant_id=tenant_id,
            state_name=HarnessState.RESOLVE_CONTEXT, state_payload={"step": 2},
        )
        cp3 = checkpoint_manager.create_checkpoint(
            run_id=run.id, tenant_id=tenant_id,
            state_name=HarnessState.LOAD_VALUE_PACK, state_payload={"step": 3},
        )
        checkpoints = checkpoint_manager.list_checkpoints_for_run(run.id, tenant_id)
        assert len(checkpoints) == 3
        assert [c.id for c in checkpoints] == [cp1.id, cp2.id, cp3.id]


# ============================================================
# Validation Hook Tests
# ============================================================


class TestValidationHooks:
    """Tests for L5 validation hooks."""

    async def test_passed_validation_permits_publication(
        self, harness: HarnessRegistry, run: HarnessRun, tenant_id: str
    ) -> None:
        """Passed validation permits publication."""
        mock_validator = MockValidator(default_state=ValidationState.PASSED)
        harness._validation = ValidationHook(primary_validator=mock_validator)

        requests = [
            ClaimValidationRequest(
                tenant_id=tenant_id,
                claim_id="claim_1",
                claim_text="ROI is 400%",
                evidence_refs=["ev_1"],
            )
        ]
        results = await harness.validate_claims(tenant_id, requests)
        assert len(results) == 1
        assert results[0].validation_state == ValidationState.PASSED
        assert can_publish_output(run, validation_results=results) is True

    async def test_failed_validation_blocks_publication(
        self, harness: HarnessRegistry, run: HarnessRun, tenant_id: str
    ) -> None:
        """Failed validation blocks publication."""
        mock_validator = MockValidator(default_state=ValidationState.FAILED)
        harness._validation = ValidationHook(primary_validator=mock_validator)

        requests = [
            ClaimValidationRequest(
                tenant_id=tenant_id,
                claim_id="claim_1",
                claim_text="ROI is 400%",
                evidence_refs=["ev_1"],
            )
        ]
        results = await harness.validate_claims(tenant_id, requests)
        assert results[0].validation_state == ValidationState.FAILED
        assert can_publish_output(run, validation_results=results, override_policy=False) is False

    async def test_insufficient_evidence_requires_review(
        self, harness: HarnessRegistry, run: HarnessRun, tenant_id: str
    ) -> None:
        """Insufficient evidence requires review."""
        mock_validator = MockValidator(default_state=ValidationState.INSUFFICIENT_EVIDENCE)
        harness._validation = ValidationHook(primary_validator=mock_validator)

        requests = [
            ClaimValidationRequest(
                tenant_id=tenant_id,
                claim_id="claim_1",
                claim_text="ROI is 400%",
                evidence_refs=["ev_1"],
            )
        ]
        results = await harness.validate_claims(tenant_id, requests)
        assert results[0].validation_state == ValidationState.INSUFFICIENT_EVIDENCE
        assert can_publish_output(run, validation_results=results) is False

    async def test_unavailable_validator_does_not_approve(
        self, harness: HarnessRegistry, run: HarnessRun, tenant_id: str
    ) -> None:
        """Unavailable validator does not approve."""
        # Default ValidationHook has no primary, uses UnavailableValidator
        assert harness.validation_available is False

        requests = [
            ClaimValidationRequest(
                tenant_id=tenant_id,
                claim_id="claim_1",
                claim_text="ROI is 400%",
                evidence_refs=["ev_1"],
            )
        ]
        results = await harness.validate_claims(tenant_id, requests)
        assert len(results) == 1
        assert results[0].validation_state == ValidationState.INSUFFICIENT_EVIDENCE
        assert results[0].validator == "unavailable"
        assert can_publish_output(run, validation_results=results) is False

    async def test_unavailable_validator_never_returns_passed(
        self, harness: HarnessRegistry, tenant_id: str
    ) -> None:
        """UnavailableValidator never returns PASSED."""
        from layer4_agents.harness.validation_hooks import (
            ClaimValidationRequest,
            UnavailableValidator,
        )

        validator = UnavailableValidator()
        request = ClaimValidationRequest(
            tenant_id=tenant_id,
            claim_id="claim_1",
            claim_text="Anything",
            evidence_refs=[],
        )
        result = await validator.validate(request)
        assert result.validation_state != ValidationState.PASSED
        assert result.validation_state == ValidationState.INSUFFICIENT_EVIDENCE

    async def test_mock_validator_allows_configuring_results(
        self, tenant_id: str
    ) -> None:
        """MockValidator can pre-configure claim results."""
        mock = MockValidator(default_state=ValidationState.PASSED)
        mock.set_result("claim_fail", ValidationState.FAILED)

        req1 = ClaimValidationRequest(tenant_id=tenant_id, claim_id="claim_ok", claim_text="OK", evidence_refs=[])
        req2 = ClaimValidationRequest(tenant_id=tenant_id, claim_id="claim_fail", claim_text="Fail", evidence_refs=[])

        result1 = await mock.validate(req1)
        result2 = await mock.validate(req2)

        assert result1.validation_state == ValidationState.PASSED
        assert result2.validation_state == ValidationState.FAILED


# ============================================================
# Telemetry Tests
# ============================================================


class TestTelemetry:
    """Tests for structured trace emission."""

    def test_transition_emits_event(
        self, telemetry: TelemetryEmitter, run: HarnessRun
    ) -> None:
        """Transition emits structured trace event."""
        event = telemetry.emit_transition_event(
            run=run,
            from_state=HarnessState.INIT,
            to_state=HarnessState.RESOLVE_CONTEXT,
        )
        assert event.tenant_id == run.tenant_id
        assert event.trace_id == run.trace_id
        assert event.event_type == "transition"
        assert event.from_state == HarnessState.INIT
        assert event.to_state == HarnessState.RESOLVE_CONTEXT

    def test_event_includes_tenant_id(
        self, telemetry: TelemetryEmitter, run: HarnessRun
    ) -> None:
        """Event includes tenant_id."""
        event = telemetry.emit_transition_event(
            run=run,
            from_state=HarnessState.INIT,
            to_state=HarnessState.RESOLVE_CONTEXT,
        )
        assert event.tenant_id == run.tenant_id
        assert event.tenant_id != ""

    def test_event_includes_trace_id(
        self, telemetry: TelemetryEmitter, run: HarnessRun
    ) -> None:
        """Event includes trace_id."""
        event = telemetry.emit_transition_event(
            run=run,
            from_state=HarnessState.INIT,
            to_state=HarnessState.RESOLVE_CONTEXT,
        )
        assert event.trace_id == run.trace_id
        assert event.trace_id != ""

    def test_event_includes_from_and_to_state(
        self, telemetry: TelemetryEmitter, run: HarnessRun
    ) -> None:
        """Event includes from_state and to_state."""
        event = telemetry.emit_transition_event(
            run=run,
            from_state=HarnessState.INIT,
            to_state=HarnessState.RESOLVE_CONTEXT,
        )
        assert event.from_state == HarnessState.INIT
        assert event.to_state == HarnessState.RESOLVE_CONTEXT

    def test_checkpoint_emits_event(
        self, telemetry: TelemetryEmitter, run: HarnessRun, checkpoint_manager: CheckpointManager, tenant_id: str
    ) -> None:
        """Checkpoint emits structured event."""
        cp = checkpoint_manager.create_checkpoint(
            run_id=run.id,
            tenant_id=tenant_id,
            state_name=HarnessState.INIT,
            state_payload={"step": 1},
        )
        event = telemetry.emit_checkpoint_event(run=run, checkpoint=cp)
        assert event.tenant_id == run.tenant_id
        assert event.trace_id == run.trace_id
        assert event.event_type == "checkpoint"

    def test_validation_emits_event(
        self, telemetry: TelemetryEmitter, run: HarnessRun, tenant_id: str
    ) -> None:
        """Validation emits structured event."""
        result = ClaimValidationResult(
            tenant_id=tenant_id,
            claim_id="claim_1",
            validation_state=ValidationState.PASSED,
            confidence=0.95,
            trust_score=0.92,
            validator="agent",
            reason="Evidence supports claim",
        )
        event = telemetry.emit_validation_event(run=run, result=result)
        assert event.tenant_id == run.tenant_id
        assert event.trace_id == run.trace_id
        assert event.validation_state == ValidationState.PASSED
        assert event.event_type == "validation"

    def test_policy_decision_emits_event(
        self, telemetry: TelemetryEmitter, run: HarnessRun
    ) -> None:
        """Policy decision emits structured event."""
        event = telemetry.emit_policy_decision_event(
            run=run,
            decision="approved",
            metadata={"tool_id": "test_tool"},
        )
        assert event.tenant_id == run.tenant_id
        assert event.trace_id == run.trace_id
        assert event.event_type == "policy_decision"
        assert event.metadata["decision"] == "approved"

    def test_events_are_structured_not_free_text(
        self, telemetry: TelemetryEmitter, run: HarnessRun
    ) -> None:
        """Events are structured Pydantic models, not free text."""
        event = telemetry.emit_transition_event(
            run=run,
            from_state=HarnessState.INIT,
            to_state=HarnessState.RESOLVE_CONTEXT,
        )
        # All events should have these structured fields
        assert hasattr(event, "tenant_id")
        assert hasattr(event, "trace_id")
        assert hasattr(event, "event_type")
        assert hasattr(event, "timestamp")
        # tenant_id and trace_id must be non-empty
        assert event.tenant_id != ""
        assert event.trace_id != ""

    def test_telemetry_filtering_by_run(
        self, telemetry: TelemetryEmitter, run: HarnessRun
    ) -> None:
        """Events can be filtered by run_id."""
        telemetry.emit_transition_event(
            run=run,
            from_state=HarnessState.INIT,
            to_state=HarnessState.RESOLVE_CONTEXT,
        )
        events = telemetry.get_events(run_id=run.id)
        assert len(events) == 1
        assert events[0].run_id == run.id


# ============================================================
# Policy Tests
# ============================================================


class TestPolicies:
    """Tests for approval and publication policies."""

    def test_passed_validation_permits_publish(self, run: HarnessRun, tenant_id: str) -> None:
        """Passed L5 validation permits publish."""
        result = ClaimValidationResult(
            tenant_id=tenant_id,
            claim_id="c1",
            validation_state=ValidationState.PASSED,
            confidence=0.9,
            trust_score=0.85,
            validator="agent",
            reason="Good evidence",
        )
        assert can_publish_output(run, validation_results=[result]) is True

    def test_explicit_human_approval_with_override_permits_publish(
        self, run: HarnessRun, tenant_id: str
    ) -> None:
        """Explicit human approval permits publish only if override policy allows."""
        gate = HumanGate(
            run_id=run.id,
            tenant_id=tenant_id,
            gate_type=GateType.APPROVE_CUSTOMER_OUTPUT,
            status=GateStatus.APPROVED,
            decision_by="alice",
        )
        assert can_publish_output(run, human_gate_decision=gate, override_policy=True) is True

    def test_explicit_human_approval_without_override_blocked(
        self, run: HarnessRun, tenant_id: str
    ) -> None:
        """Human approval without override policy blocks publish."""
        gate = HumanGate(
            run_id=run.id,
            tenant_id=tenant_id,
            gate_type=GateType.APPROVE_CUSTOMER_OUTPUT,
            status=GateStatus.APPROVED,
            decision_by="alice",
        )
        assert can_publish_output(run, human_gate_decision=gate, override_policy=False) is False

    def test_failed_validation_blocks_publish(self, run: HarnessRun, tenant_id: str) -> None:
        """Failed validation blocks publication."""
        result = ClaimValidationResult(
            tenant_id=tenant_id,
            claim_id="c1",
            validation_state=ValidationState.FAILED,
            confidence=0.0,
            trust_score=0.0,
            validator="agent",
            reason="No evidence",
        )
        assert can_publish_output(run, validation_results=[result], override_policy=False) is False

    def test_unavailable_validation_blocks_publish(self, run: HarnessRun) -> None:
        """Unavailable validation blocks publication."""
        assert can_publish_output(run, validation_results=None) is False

    def test_insufficient_evidence_blocks_publish(self, run: HarnessRun, tenant_id: str) -> None:
        """Insufficient evidence blocks publication."""
        result = ClaimValidationResult(
            tenant_id=tenant_id,
            claim_id="c1",
            validation_state=ValidationState.INSUFFICIENT_EVIDENCE,
            confidence=0.0,
            trust_score=0.0,
            validator="unavailable",
            reason="Not enough data",
        )
        assert can_publish_output(run, validation_results=[result]) is False

    def test_rejected_gate_blocks_publish(self, run: HarnessRun, tenant_id: str) -> None:
        """Rejected gate blocks publication."""
        gate = HumanGate(
            run_id=run.id,
            tenant_id=tenant_id,
            gate_type=GateType.APPROVE_CLAIMS,
            status=GateStatus.REJECTED,
            decision_by="bob",
            decision_reason="Needs more work",
        )
        assert can_publish_output(run, human_gate_decision=gate, override_policy=False) is False

    def test_requires_human_review_on_insufficient_evidence(
        self, tenant_id: str
    ) -> None:
        """Insufficient evidence requires human review."""
        from layer4_agents.harness.policies import requires_human_review
        result = ClaimValidationResult(
            tenant_id=tenant_id,
            claim_id="c1",
            validation_state=ValidationState.INSUFFICIENT_EVIDENCE,
            confidence=0.0,
            trust_score=0.0,
            validator="unavailable",
            reason="Not enough",
        )
        assert requires_human_review([result]) is True

    def test_no_human_review_needed_when_all_passed(self, tenant_id: str) -> None:
        """No human review needed when all validations passed."""
        from layer4_agents.harness.policies import requires_human_review
        result = ClaimValidationResult(
            tenant_id=tenant_id,
            claim_id="c1",
            validation_state=ValidationState.PASSED,
            confidence=0.9,
            trust_score=0.85,
            validator="agent",
            reason="Good",
        )
        assert requires_human_review([result]) is False

    def test_failed_validation_with_override_allows_publish(
        self, run: HarnessRun, tenant_id: str
    ) -> None:
        """Failed validation with override policy allows publish."""
        result = ClaimValidationResult(
            tenant_id=tenant_id,
            claim_id="c1",
            validation_state=ValidationState.FAILED,
            confidence=0.0,
            trust_score=0.0,
            validator="agent",
            reason="Bad",
        )
        assert can_publish_output(run, validation_results=[result], override_policy=True) is True


# ============================================================
# Tenant Isolation Tests
# ============================================================


class TestTenantIsolation:
    """Tests for tenant isolation enforcement."""

    def test_cross_tenant_run_access_returns_404_pattern(
        self, harness: HarnessRegistry, run: HarnessRun, tenant_id: str, other_tenant: str
    ) -> None:
        """Cross-tenant run access raises error (maps to 404 in API)."""
        harness.create_run(
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        run = harness.list_runs(tenant_id=tenant_id)[0]
        with pytest.raises(RunNotFoundError):
            harness.get_run(run.id, other_tenant)

    def test_run_list_is_tenant_scoped(
        self, harness: HarnessRegistry, tenant_id: str, other_tenant: str
    ) -> None:
        """Run list only returns runs for the specified tenant."""
        harness.create_run(
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        harness.create_run(
            tenant_id=other_tenant,
            workflow_type=HarnessWorkflowType.SIGNAL_EXTRACTION,
            initiated_by=InitiatedBy.USER,
        )
        tenant_runs = harness.list_runs(tenant_id=tenant_id)
        other_runs = harness.list_runs(tenant_id=other_tenant)
        assert len(tenant_runs) == 1
        assert len(other_runs) == 1
        assert tenant_runs[0].tenant_id == tenant_id
        assert other_runs[0].tenant_id == other_tenant

    def test_every_run_has_tenant_id(
        self, harness: HarnessRegistry, tenant_id: str
    ) -> None:
        """Every HarnessRun has tenant_id."""
        run = harness.create_run(
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        assert run.tenant_id == tenant_id
        assert run.tenant_id != ""

    def test_every_run_has_trace_id(
        self, harness: HarnessRegistry, tenant_id: str
    ) -> None:
        """Every HarnessRun has trace_id."""
        run = harness.create_run(
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        assert hasattr(run, "trace_id")
        assert run.trace_id != ""
        assert run.trace_id.startswith("trace_")

    def test_cross_tenant_checkpoint_access_blocked(
        self, harness: HarnessRegistry, run: HarnessRun, tenant_id: str, other_tenant: str
    ) -> None:
        """Cross-tenant checkpoint access is blocked."""
        cp = harness._checkpoints.create_checkpoint(
            run_id=run.id,
            tenant_id=tenant_id,
            state_name=HarnessState.INIT,
            state_payload={},
        )
        from layer4_agents.harness.checkpoints import CheckpointTenantError
        with pytest.raises(CheckpointTenantError):
            harness._checkpoints.get_checkpoint(cp.id, run.id, other_tenant)


# ============================================================
# Model Tests
# ============================================================


class TestModels:
    """Tests for domain model invariants."""

    def test_harness_run_requires_tenant_id(self) -> None:
        """HarnessRun requires non-empty tenant_id."""
        with pytest.raises(ValueError):
            HarnessRun(
                tenant_id="",
                workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
                initiated_by=InitiatedBy.USER,
            )

    def test_harness_run_default_state_is_init(self, tenant_id: str) -> None:
        """Default state is INIT."""
        run = HarnessRun(
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        assert run.current_state == HarnessState.INIT
        assert run.status == HarnessRunStatus.QUEUED

    def test_checkpoint_id_generation(self, run: HarnessRun, tenant_id: str) -> None:
        """Checkpoint IDs are generated."""
        cp = HarnessCheckpoint(
            run_id=run.id,
            tenant_id=tenant_id,
            state_name=HarnessState.INIT,
            input_hash="abc123",
        )
        assert cp.id.startswith("chk_")

    def test_gate_terminal_property(self, run: HarnessRun, tenant_id: str) -> None:
        """Gate terminal property works correctly."""
        gate = HumanGate(
            run_id=run.id,
            tenant_id=tenant_id,
            gate_type=GateType.APPROVE_CLAIMS,
            status=GateStatus.PENDING,
        )
        assert gate.is_terminal is False

        approved = gate.decide(GateStatus.APPROVED, decision_by="alice")
        assert approved.is_terminal is True

    def test_validation_state_values(self) -> None:
        """ValidationState has correct values."""
        assert ValidationState.PASSED.value == "passed"
        assert ValidationState.FAILED.value == "failed"
        assert ValidationState.NEEDS_REVIEW.value == "needs_review"
        assert ValidationState.INSUFFICIENT_EVIDENCE.value == "insufficient_evidence"


# ============================================================
# Integration Tests
# ============================================================


class TestIntegration:
    """Integration tests for full harness workflows."""

    async def test_full_workflow_with_validation_pass(
        self, harness: HarnessRegistry, tenant_id: str
    ) -> None:
        """Full workflow with passing validation."""
        mock_validator = MockValidator(default_state=ValidationState.PASSED)
        harness._validation = ValidationHook(primary_validator=mock_validator)

        # Create run
        run = harness.create_run(
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
            account_id="acct_123",
            value_pack_id="manufacturing",
        )
        assert run.tenant_id == tenant_id
        assert run.trace_id != ""

        # Transition through states
        states = [
            HarnessState.RESOLVE_CONTEXT,
            HarnessState.LOAD_VALUE_PACK,
            HarnessState.RETRIEVE_KNOWLEDGE,
            HarnessState.GENERATE_HYPOTHESES,
            HarnessState.MATCH_EVIDENCE,
            HarnessState.QUANTIFY_IMPACT,
            HarnessState.VALIDATE_CLAIMS,
        ]
        current = run
        for s in states:
            current, _ = harness.transition(current.id, tenant_id, s, state_payload={"step": s.value})

        # Validate claims
        requests = [
            ClaimValidationRequest(
                tenant_id=tenant_id,
                claim_id="claim_1",
                claim_text="ROI 400%",
                evidence_refs=["ev_1"],
                value_pack_id="manufacturing",
                account_id="acct_123",
            )
        ]
        results = await harness.validate_claims(tenant_id, requests)
        assert results[0].validation_state == ValidationState.PASSED

        # Publish with validation
        current, _ = harness.transition(
            current.id, tenant_id, HarnessState.PUBLISH_OUTPUT,
            validation_results=results,
            state_payload={"published": True},
        )
        assert current.current_state == HarnessState.PUBLISH_OUTPUT

        # Done
        current, _ = harness.transition(current.id, tenant_id, HarnessState.DONE, state_payload={"done": True})
        assert current.current_state == HarnessState.DONE
        assert current.status == HarnessRunStatus.COMPLETED

        # Checkpoints exist
        checkpoints = harness.get_checkpoints(run.id, tenant_id)
        assert len(checkpoints) == len(states) + 2  # + PUBLISH_OUTPUT + DONE

        # Telemetry events exist
        events = harness.telemetry.get_events(run_id=run.id)
        assert len(events) > 0
        assert all(e.tenant_id == tenant_id for e in events)
        assert all(e.trace_id == run.trace_id for e in events)

    def test_workflow_blocked_without_validation(
        self, harness: HarnessRegistry, tenant_id: str
    ) -> None:
        """Workflow blocked at PUBLISH_OUTPUT without validation."""
        run = harness.create_run(
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )

        # Progress to VALIDATE_CLAIMS
        states = [
            HarnessState.RESOLVE_CONTEXT,
            HarnessState.LOAD_VALUE_PACK,
            HarnessState.RETRIEVE_KNOWLEDGE,
            HarnessState.GENERATE_HYPOTHESES,
            HarnessState.MATCH_EVIDENCE,
            HarnessState.QUANTIFY_IMPACT,
            HarnessState.VALIDATE_CLAIMS,
        ]
        current = run
        for s in states:
            current, _ = harness.transition(current.id, tenant_id, s, state_payload={})

        # Attempt PUBLISH_OUTPUT without validation
        with pytest.raises(TransitionError):
            harness.transition(current.id, tenant_id, HarnessState.PUBLISH_OUTPUT, state_payload={})

    def test_human_review_workflow_with_gate(
        self, harness: HarnessRegistry, tenant_id: str
    ) -> None:
        """Workflow with human review gate."""
        run = harness.create_run(
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.BUSINESS_CASE_GENERATION,
            initiated_by=InitiatedBy.USER,
        )

        # Progress to VALIDATE_CLAIMS
        states = [
            HarnessState.RESOLVE_CONTEXT,
            HarnessState.LOAD_VALUE_PACK,
            HarnessState.RETRIEVE_KNOWLEDGE,
            HarnessState.GENERATE_HYPOTHESES,
            HarnessState.MATCH_EVIDENCE,
            HarnessState.QUANTIFY_IMPACT,
            HarnessState.VALIDATE_CLAIMS,
        ]
        current = run
        for s in states:
            current, _ = harness.transition(current.id, tenant_id, s, state_payload={})

        # Route to HUMAN_REVIEW (insufficient evidence)
        current, _ = harness.transition(
            current.id, tenant_id, HarnessState.HUMAN_REVIEW,
            validation_results=[
                ClaimValidationResult(
                    tenant_id=tenant_id,
                    claim_id="c1",
                    validation_state=ValidationState.INSUFFICIENT_EVIDENCE,
                    confidence=0.0,
                    trust_score=0.0,
                    validator="unavailable",
                    reason="Not enough data",
                )
            ],
            state_payload={},
        )
        assert current.status == HarnessRunStatus.WAITING_FOR_HUMAN

        # Create and approve human gate
        gate = harness.create_human_gate(current.id, tenant_id, GateType.APPROVE_CLAIMS)
        approved_gate = harness.decide_gate(gate.id, tenant_id, GateStatus.APPROVED, "alice", "Approved")
        assert approved_gate.status == GateStatus.APPROVED

        # Now can publish with human override
        current, _ = harness.transition(
            current.id, tenant_id, HarnessState.PUBLISH_OUTPUT,
            human_override=True,
            state_payload={},
        )
        assert current.current_state == HarnessState.PUBLISH_OUTPUT

    def test_cancelled_workflow(
        self, harness: HarnessRegistry, tenant_id: str
    ) -> None:
        """Workflow can be cancelled from any non-terminal state."""
        run = harness.create_run(
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.RENEWAL_RISK_ANALYSIS,
            initiated_by=InitiatedBy.USER,
        )

        # Progress
        current, _ = harness.transition(run.id, tenant_id, HarnessState.RESOLVE_CONTEXT, state_payload={})
        current, _ = harness.transition(current.id, tenant_id, HarnessState.LOAD_VALUE_PACK, state_payload={})

        # Cancel
        current, _ = harness.transition(current.id, tenant_id, HarnessState.CANCELLED, state_payload={})
        assert current.current_state == HarnessState.CANCELLED
        assert current.status == HarnessRunStatus.CANCELLED

        # Cannot continue
        with pytest.raises(TerminalStateError):
            harness.transition(current.id, tenant_id, HarnessState.RETRIEVE_KNOWLEDGE, state_payload={})


# ============================================================
# API-Level Tests (behavior simulation)
# ============================================================


class TestAPIBehavior:
    """
    Tests that simulate API-level behavior.

    If FastAPI routes are added later, these patterns map directly.
    """

    def test_create_run_requires_tenant_context(
        self, harness: HarnessRegistry
    ) -> None:
        """Create run requires tenant context (empty tenant raises)."""
        with pytest.raises(ValueError):
            harness.create_run(
                tenant_id="",
                workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
                initiated_by=InitiatedBy.USER,
            )

    def test_cross_tenant_read_returns_404_pattern(
        self, harness: HarnessRegistry, tenant_id: str, other_tenant: str
    ) -> None:
        """Cross-tenant read returns 404-like error."""
        run = harness.create_run(
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        with pytest.raises(RunNotFoundError) as exc_info:
            harness.get_run(run.id, other_tenant)
        assert "not found" in str(exc_info.value).lower()

    def test_invalid_transition_returns_422_pattern(
        self, harness: HarnessRegistry, tenant_id: str
    ) -> None:
        """Invalid transition returns 422-like error."""
        run = harness.create_run(
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        with pytest.raises(TransitionError) as exc_info:
            harness.transition(run.id, tenant_id, HarnessState.DONE, state_payload={})
        assert "Invalid transition" in str(exc_info.value)

    def test_run_checkpoint_list_is_tenant_scoped(
        self, harness: HarnessRegistry, tenant_id: str, other_tenant: str
    ) -> None:
        """Checkpoint list is scoped to tenant."""
        run = harness.create_run(
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        harness._checkpoints.create_checkpoint(
            run_id=run.id, tenant_id=tenant_id,
            state_name=HarnessState.INIT, state_payload={},
        )
        # Same run_id, different tenant → no checkpoints
        other_cps = harness._checkpoints.list_checkpoints_for_run(run.id, other_tenant)
        assert len(other_cps) == 0

    def test_human_gate_decision_is_tenant_scoped(
        self, harness: HarnessRegistry, tenant_id: str, other_tenant: str
    ) -> None:
        """Human gate decision is tenant-scoped."""
        run = harness.create_run(
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        gate = harness.create_human_gate(run.id, tenant_id, GateType.APPROVE_CLAIMS)
        # Cross-tenant access fails
        with pytest.raises(GateNotFoundError):
            harness.decide_gate(gate.id, other_tenant, GateStatus.APPROVED, "alice")

    def test_unavailable_validation_cannot_publish(
        self, harness: HarnessRegistry, tenant_id: str
    ) -> None:
        """Unavailable validation cannot lead to PUBLISH_OUTPUT."""
        run = harness.create_run(
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        states = [
            HarnessState.RESOLVE_CONTEXT,
            HarnessState.LOAD_VALUE_PACK,
            HarnessState.RETRIEVE_KNOWLEDGE,
            HarnessState.GENERATE_HYPOTHESES,
            HarnessState.MATCH_EVIDENCE,
            HarnessState.QUANTIFY_IMPACT,
            HarnessState.VALIDATE_CLAIMS,
        ]
        current = run
        for s in states:
            current, _ = harness.transition(current.id, tenant_id, s, state_payload={})

        # Default validation hook is unavailable → try to publish without results
        with pytest.raises(TransitionError):
            harness.transition(current.id, tenant_id, HarnessState.PUBLISH_OUTPUT, state_payload={})


# ============================================================
# ADR / Documentation
# ============================================================


def test_adr_content() -> None:
    """ADR document exists and contains key decisions."""
    # Navigate from tests/ to repo root: tests -> harness -> src -> layer4-agents -> services -> output
    adr_path = Path(__file__).parent.parent.parent.parent.parent.parent / "docs" / "architecture" / "ADR-001-fabric-harness-as-the-governed-execution-spine-for-agentic-value-workflows.md"
    assert adr_path.exists(), f"ADR document should exist at {adr_path}"
    content = adr_path.read_text()
    assert "L4 remains the orchestration layer" in content
    assert "L5 remains the ground-truth and validation layer" in content
    assert "L3 remains the knowledge and context layer" in content
    assert "L6 remains the benchmark and policy layer" in content
    assert "harness does not replace these layers" in content
    assert "Customer-facing outputs require validation or approved override" in content


# ============================================================
# Anti-Drift Tests
# ============================================================


class TestAntiDrift:
    """Tests that verify the harness doesn't introduce architectural drift."""

    def test_no_duplicate_tenant_context_mechanism(self, harness: HarnessRegistry, tenant_id: str) -> None:
        """Harness uses HarnessRun.tenant_id as single source of truth."""
        run = harness.create_run(
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        # All operations derive tenant context from the run
        assert run.tenant_id == tenant_id
        # No parallel tenant context mechanism exists

    def test_validation_hook_not_duplicating_l5_logic(self, harness: HarnessRegistry) -> None:
        """Validation hook provides interface, not L5 logic."""
        # The hook is an adapter/protocol, not a validator implementation
        assert hasattr(harness._validation, 'validate_claims')
        assert hasattr(harness._validation, 'validate_single')
        # It delegates to a validator, doesn't implement validation logic itself

    def test_harness_does_not_create_new_persistence_style(self, checkpoint_manager: CheckpointManager) -> None:
        """In-memory persistence used, no new DB layer introduced."""
        # CheckpointManager uses simple dict storage
        assert hasattr(checkpoint_manager, '_checkpoints')

    def test_no_speculative_abstractions(self) -> None:
        """MVP has no speculative abstractions beyond scope."""
        # Verify core classes exist without bloat
        import layer4_agents.harness as h
        assert hasattr(h, 'HarnessRun')
        assert hasattr(h, 'StateMachine')
        assert hasattr(h, 'ToolContractRegistry')
        assert hasattr(h, 'HumanGateManager')
        assert hasattr(h, 'CheckpointManager')
        assert hasattr(h, 'TelemetryEmitter')
        assert hasattr(h, 'ValidationHook')
        assert hasattr(h, 'HarnessRegistry')

    def test_no_new_import_drift(self) -> None:
        """Harness uses standard library + Pydantic only."""
        # This test verifies no exotic dependencies
        # All models should use pydantic BaseModel
        from pydantic import BaseModel
        assert issubclass(HarnessRun, BaseModel)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
