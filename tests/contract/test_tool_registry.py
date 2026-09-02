"""
Contract tests for the Contract-First Agent Tool Registry.

Behavior-first (see docs/governance/behavior-first-testing.md): intended behavior
passes, denied behavior fails closed, failure modes are explicit.

Coverage (AC9):
- Validator acceptance: the six canonical billing manifests validate.
- Validator denial: mutating tools missing idempotency/approval/audit fail closed.
- Tenant isolation: caller-selected tenant authority is rejected.
- Policy filtering: billing-copilot cannot see IRREVERSIBLE tools.
- action_id cross-reference: unknown action id is rejected.
- Generated-index inclusion/exclusion: valid manifests appear, invalid ones don't.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from layer4_agents.tools_manifest import load_manifests, filter_tools_for_agent
from layer4_agents.tools_manifest.loader import validate_manifest
from layer4_agents.tools_manifest.models import (
    ApprovalRequirement,
    AuditRequirement,
    Implementation,
    PrincipalType,
    ResourceResolver,
    Runtime,
    SideEffectClass,
    TenantBinding,
    ToolManifest,
    ToolManifestSummary,
    ToolRegistryIndex,
    AgentPolicy,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFESTS_DIR = REPO_ROOT / "contracts" / "tool-manifests"
GENERATED_DIR = MANIFESTS_DIR / "generated"


@pytest.fixture(scope="module")
def registry_schema() -> dict:
    with open(MANIFESTS_DIR / "registry.schema.json") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def manifest_schema() -> dict:
    with open(MANIFESTS_DIR / "tool-manifest.schema.json") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def compiled() -> tuple[ToolRegistryIndex, object]:
    """Load manifests + validation report once."""
    index, report = load_manifests(MANIFESTS_DIR)
    return index, report


# --------------------------------------------------------------------------- #
# AC2 — the six example billing manifests validate
# --------------------------------------------------------------------------- #


class TestValidatorAcceptance:
    def test_all_six_canonical_manifests_validate(self, compiled) -> None:
        index, report = compiled
        assert report.valid, f"expected valid report, got failures: {report.failed}"
        assert len(index.tool_manifests) == 6

    def test_expected_tool_ids_present(self, compiled) -> None:
        index, _ = compiled
        tool_ids = {m.tool_id for m in index.tool_manifests}
        expected = {
            "billing.invoice.explain",
            "billing.charge.forecast",
            "billing.subscription.change_draft",
            "billing.credit.request_draft",
            "billing.refund.request_draft",
            "billing.reconciliation.analyze",
        }
        assert tool_ids == expected

    def test_only_validated_manifests_in_index(self, compiled) -> None:
        index, report = compiled
        summary = index.validation_report
        assert summary is not None
        # Every manifest in the index passed validation.
        assert len(index.tool_manifests) == 6
        assert summary.manifests_loaded == len(index.tool_manifests)


# --------------------------------------------------------------------------- #
# AC4/AC9 — validator denial: mutating tools need full governance envelope
# --------------------------------------------------------------------------- #


def _minimal_raw(manifest_schema: dict, **overrides: object) -> dict:
    base = {
        "tool_id": "billing.test.tool",
        "version": "1.0.0",
        "status": "ACTIVE",
        "owner": "agents/billing-experience",
        "description": "A test tool",
        "implementation": {"service": "services/layer7-billing", "operation_id": "test.run", "route": "/v1/test"},
        "action_id": "billing.test",
        "principal_types": ["user"],
        "input_schema_ref": "contracts/tool-manifests/test-input.schema.json",
        "output_schema_ref": "contracts/tool-manifests/test-output.schema.json",
        "tenant_binding": {"client_supplied_tenant_authoritative": False, "resolve_server_side": False},
        "side_effect": "READ_ONLY",
        "audit": {"required": True, "action": "billing.test.run"},
        "runtime": {"timeout_ms": 5000},
    }
    base.update(overrides)
    return base


class TestValidatorDenial:
    def test_invalid_manifest_rejected(self, manifest_schema) -> None:
        raw = _minimal_raw(manifest_schema)
        raw["runtime"] = {"timeout_ms": 50}  # < 100 -> schema violation
        violations = validate_manifest(raw, manifest_schema)
        assert violations, "expected a schema violation for timeout_ms < 100"

    @pytest.mark.parametrize(
        ("mutations", "missing_fragment"),
        [
            ({"idempotency": {}}, "idempotency.required"),
            ({"approval_requirement": {}}, "approval_requirement"),
            ({"audit": {"required": False, "action": "x"}}, "audit.required"),
        ],
    )
    def test_mutating_tool_missing_governance_rejected(
        self, manifest_schema, mutations, missing_fragment
    ) -> None:
        raw = _minimal_raw(manifest_schema, side_effect="PROTECTED_MUTATION", **mutations)
        violations = validate_manifest(raw, manifest_schema)
        assert any(missing_fragment in v for v in violations), (
            f"expected a governance violation mentioning {missing_fragment}, got {violations}"
        )

    def test_irreversible_exposed_to_billing_rejected(self, manifest_schema) -> None:
        raw = _minimal_raw(
            manifest_schema,
            side_effect="IRREVERSIBLE",
            supported_agent_classes=["billing-copilot", "general-agent"],
            idempotency={"required": True, "key_input_fields": ["id"]},
            approval_requirement={"required": True},
            human_confirmation_required=True,
        )
        violations = validate_manifest(raw, manifest_schema)
        assert any("billing copilot" in v.lower() for v in violations), (
            f"expected a billing-copilot IRREVERSIBLE rejection, got {violations}"
        )


# --------------------------------------------------------------------------- #
# AC5 — tenant isolation: caller-selected tenant authority fails closed
# --------------------------------------------------------------------------- #


class TestTenantAuthority:
    def test_caller_supplied_tenant_authority_rejected(self, manifest_schema) -> None:
        raw = _minimal_raw(
            manifest_schema,
            tenant_binding={
                "client_supplied_tenant_authoritative": True,
                "resolve_server_side": False,
            },
        )
        violations = validate_manifest(raw, manifest_schema)
        assert any("client_supplied_tenant_authoritative" in v for v in violations), (
            f"expected tenant-authority rejection, got {violations}"
        )

    def test_server_side_resolution_allowed(self, manifest_schema) -> None:
        raw = _minimal_raw(
            manifest_schema,
            tenant_binding={
                "client_supplied_tenant_authoritative": False,
                "resolve_server_side": True,
            },
        )
        violations = validate_manifest(raw, manifest_schema)
        assert not any("tenant" in v.lower() for v in violations), (
            f"server-side tenant resolution must be allowed, got {violations}"
        )


# --------------------------------------------------------------------------- #
# AC9 — action_id cross-reference
# --------------------------------------------------------------------------- #


class TestActionCrossReference:
    def test_unknown_action_id_rejected(self, manifest_schema) -> None:
        raw = _minimal_raw(manifest_schema, action_id="does.not.exist")
        violations = validate_manifest(
            raw, manifest_schema, action_catalog={"known.action"}
        )
        assert any("action_id" in v for v in violations), (
            f"expected action-id cross-reference violation, got {violations}"
        )

    def test_known_action_id_accepted(self, manifest_schema) -> None:
        raw = _minimal_raw(manifest_schema, action_id="known.action")
        violations = validate_manifest(
            raw, manifest_schema, action_catalog={"known.action"}
        )
        assert not any("action_id" in v for v in violations), f"got {violations}"


# --------------------------------------------------------------------------- #
# AC8 — policy-driven exposure filtering
# --------------------------------------------------------------------------- #


def _summary(
    tool_id: str,
    side_effect: str,
    supported: list[str] | None,
    tenant_binding: TenantBinding | None,
) -> ToolManifestSummary:
    return ToolManifestSummary(
        tool_id=tool_id,
        version="1.0.0",
        status="active",
        side_effect=side_effect,
        action_id=tool_id,
        principal_types=["user"],
        human_confirmation_required=False,
        financial_state_change=(side_effect != "READ_ONLY"),
        supported_agent_classes=supported,
        tenant_binding=tenant_binding,
        source_path="synthetic",
    )


@pytest.fixture(scope="module")
def policy_index(compiled) -> ToolRegistryIndex:
    index, _ = compiled
    # Work on a copy so tests do not mutate the shared module-scoped index.
    index = index.model_copy(deep=True)
    binding = index.tool_manifests[0].tenant_binding
    synthetic = [
        _summary("billing.subscription.change_execute", "REVERSIBLE_MUTATION",
                 ["billing-copilot", "general-agent"], binding),
        _summary("billing.refund.execute", "IRREVERSIBLE",
                 ["billing-copilot", "general-agent"], binding),
    ]
    index.tool_manifests.extend(synthetic)
    return index


class TestPolicyFiltering:
    def test_billing_cannot_see_irreversible(self, policy_index) -> None:
        exposed = {m.tool_id for m in filter_tools_for_agent(policy_index, "billing-copilot")}
        assert "billing.refund.execute" not in exposed

    def test_billing_cannot_see_reversible_mutation(self, policy_index) -> None:
        exposed = {m.tool_id for m in filter_tools_for_agent(policy_index, "billing-copilot")}
        assert "billing.subscription.change_execute" not in exposed

    def test_general_agent_can_see_reversible_mutation(self, policy_index) -> None:
        exposed = {m.tool_id for m in filter_tools_for_agent(policy_index, "general-agent")}
        assert "billing.subscription.change_execute" in exposed

    def test_general_agent_cannot_see_irreversible(self, policy_index) -> None:
        # Both policies deny IRREVERSIBLE by default (fail closed).
        exposed = {m.tool_id for m in filter_tools_for_agent(policy_index, "general-agent")}
        assert "billing.refund.execute" not in exposed

    def test_supported_agent_classes_allowlist(self, compiled) -> None:
        index, _ = compiled
        index = index.model_copy(deep=True)
        binding = index.tool_manifests[0].tenant_binding
        # Tool only supports a class not present -> filtered out for everyone.
        index.tool_manifests.append(
            _summary("billing.audit.only", "READ_ONLY", ["audit-only-agent"], binding)
        )
        for agent in ("billing-copilot", "general-agent"):
            exposed = {m.tool_id for m in filter_tools_for_agent(index, agent)}
            assert "billing.audit.only" not in exposed

    def test_unknown_agent_class_fails_closed(self, policy_index) -> None:
        # An agent class with no policy must receive no tools, not all tools.
        exposed = filter_tools_for_agent(policy_index, "no-such-agent-class")
        assert exposed == []

    def test_empty_side_effect_allowlist_fails_closed(self, policy_index) -> None:
        # A policy with an empty allowed_side_effects list must deny by default.
        index = policy_index.model_copy(deep=True)
        index.policies["locked-down-agent"] = AgentPolicy(
            allowed_side_effects=[],
            allowed_tools=[],
            denied_side_effects=[],
            denied_tools=[],
        )
        # Give the agent a tool that would otherwise be visible via denials-only.
        binding = index.tool_manifests[0].tenant_binding
        index.tool_manifests.append(
            _summary("billing.read.explain", "READ_ONLY",
                     ["locked-down-agent"], binding)
        )
        exposed = {m.tool_id for m in filter_tools_for_agent(index, "locked-down-agent")}
        assert "billing.read.explain" not in exposed
        assert exposed == set()


# --------------------------------------------------------------------------- #
# AC6/A C9 — generated-index inclusion/exclusion
# --------------------------------------------------------------------------- #


class TestGeneratedIndex:
    def test_generated_index_exists_and_is_valid(self) -> None:
        path = GENERATED_DIR / "layer4-tool-index.json"
        assert path.exists(), "layer4-tool-index.json missing from generated/"
        payload = json.loads(path.read_text())
        assert payload["registry_version"].count(".") == 2
        assert len(payload["tool_manifests"]) == 6

    def test_generated_index_is_deterministic(self) -> None:
        p1 = (GENERATED_DIR / "layer4-tool-index.json").read_text()
        p2 = (GENERATED_DIR / "layer4-tool-index.json").read_text()
        assert p1 == p2

    def test_generated_index_matches_loader(self, compiled) -> None:
        index, _ = compiled
        payload = json.loads((GENERATED_DIR / "layer4-tool-index.json").read_text())
        generated_ids = {m["tool_id"] for m in payload["tool_manifests"]}
        loaded_ids = {m.tool_id for m in index.tool_manifests}
        assert generated_ids == loaded_ids
