from __future__ import annotations

"""Integration-ish tests for deterministic claim promotion into Layer 5."""


from typing import Any
from unittest.mock import AsyncMock

import pytest
from value_fabric.shared.models.typed_dict import TypedDictModel

from layer4_agents.services.export_provenance import build_export_provenance_manifest
from layer4_agents.workflows.business_case import (
    BusinessCaseGeneratorWorkflow,
    MissingTenantContextError,
)


class _FakeLayer5Client_list_truthsResult(TypedDictModel):
    items: list[Any]

class _FakeLayer5Client_submit_truthResult(TypedDictModel):
    id: Any

class _FakeLayer5Client_validate_truthResult(TypedDictModel):
    ok: bool

class _FakeLayer5Client_sync_validated_truthsResult(TypedDictModel):
    failed: int
    synced: int


class _FakeLayer5Client:
    def __init__(self, *args, **kwargs):
        self.created_truths: list[dict] = []
        self.validations: list[dict] = []

    async def list_truths(self, **kwargs):
        return {"items": []}

    async def submit_truth(self, **kwargs):
        truth_id = f"truth-{len(self.created_truths) + 1}"
        self.created_truths.append({"id": truth_id, **kwargs})
        return {"id": truth_id}

    async def validate_truth(self, **kwargs):
        self.validations.append(kwargs)
        return {"ok": True}

    async def sync_validated_truths(self, **kwargs):
        return {"synced": 0, "failed": 0}

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_promotes_claims_and_persists_traceability(monkeypatch):
    registry = AsyncMock()
    registry.execute = AsyncMock(return_value={"document_url": "https://example/doc.pdf"})
    workflow = BusinessCaseGeneratorWorkflow(tool_registry=registry)
    state = workflow.create_initial_state(
        {
            "account_id": "550e8400-e29b-41d4-a716-446655440001",
            "opportunity_id": "opp-1",
            "sections_requested": ["roi_analysis"],
            "output_format": "pdf",
            "custom_inputs": {
                "organization_id": "org-1",
                "source_references": [{"id": "src-1", "uri": "https://source/1"}],
                "claim_promotion_thresholds": {"min_confidence": 0.7, "min_evidence_sources": 1},
            },
        },
        tenant_id="test-tenant",
    )
    state.output_data = {
        "verify_truth_requirements": {"passed": True, "requirements": [], "remediation_items": []},
        "generate_narrative": {
            "sections": [
                {
                    "title": "ROI Analysis",
                    "content": "This initiative yields 140% ROI within 8 months.",
                    "charts": [],
                    "tables": [],
                }
            ]
        },
        "run_roi": {
            "roi_results": {
                "simple_roi_percent": 140.0,
                "payback_period_months": 8.0,
                "three_year_npv": 1230000.0,
            }
        },
    }

    state.metadata["authenticated_tenant_id"] = "test-tenant"
    monkeypatch.setattr("layer4_agents.workflows.business_case.Layer5GroundTruthClient", _FakeLayer5Client)
    workflow._sync_ground_truths_to_kg = AsyncMock(return_value={"synced": 0, "failed": 0})  # type: ignore[method-assign]

    result = await workflow._execute_assemble_document(state)

    assert result["truth_object_ids"]
    assert result["case_metadata"]["truth_object_ids"] == result["truth_object_ids"]
    assert result["case_metadata"]["claim_traceability"]
    assert any(
        d["decision"] in {"promoted", "existing"} for d in result["case_metadata"]["threshold_decisions"]
    )


@pytest.mark.asyncio
async def test_skips_claims_below_threshold(monkeypatch):
    registry = AsyncMock()
    registry.execute = AsyncMock(return_value={"document_url": "https://example/doc.pdf"})
    workflow = BusinessCaseGeneratorWorkflow(tool_registry=registry)
    state = workflow.create_initial_state(
        {
            "account_id": "550e8400-e29b-41d4-a716-446655440002",
            "sections_requested": ["executive_summary"],
            "output_format": "pdf",
            "custom_inputs": {
                "organization_id": "org-2",
                "source_references": [],
                "claim_promotion_thresholds": {"min_confidence": 0.9, "min_evidence_sources": 2},
            },
        },
        tenant_id="test-tenant",
    )
    state.output_data = {
        "verify_truth_requirements": {"passed": True},
        "generate_narrative": {
            "sections": [
                {
                    "title": "Executive Summary",
                    "content": "Expected impact is 12% in year one.",
                    "charts": [],
                    "tables": [],
                }
            ]
        },
        "run_roi": {"roi_results": {}},
    }

    monkeypatch.setattr("layer4_agents.workflows.business_case.Layer5GroundTruthClient", _FakeLayer5Client)
    state.metadata["authenticated_tenant_id"] = "test-tenant"
    workflow._sync_ground_truths_to_kg = AsyncMock(return_value={"synced": 0, "failed": 0})  # type: ignore[method-assign]

    result = await workflow._execute_assemble_document(state)
    decisions = result["case_metadata"]["threshold_decisions"]

    assert result["truth_object_ids"] == []
    assert decisions
    assert all(d["decision"] == "skipped" for d in decisions)


def test_export_manifest_reads_persisted_case_linkage():
    workflow_result = {
        "workflow_id": "case-1",
        "output": {
            "assemble_document": {
                "case_metadata": {
                    "truth_object_ids": ["truth-123"],
                    "claim_traceability": [{"claim": "A", "truth_object_id": "truth-123"}],
                    "threshold_decisions": [{"claim": "A", "decision": "promoted"}],
                    "source_references": [{"id": "truth-123", "type": "claim"}],
                }
            },
            # Legacy ad hoc fields should be ignored:
            "truth_object_ids": ["legacy-should-not-be-used"],
            "source_references": [{"legacy": True}],
        },
        "metadata": {},
    }

    manifest = build_export_provenance_manifest(
        case_id="case-1",
        workflow_result=workflow_result,
        actor_context=None,
        export_id="export-1",
    )

    assert manifest["truth_object_ids"] == ["truth-123"]
    assert manifest["source_references"] == [{"pointer": "truth-123", "type": "claim", "locator": None}]


def test_resolve_organization_id_fails_closed_without_authenticated_tenant():
    workflow = BusinessCaseGeneratorWorkflow(tool_registry=AsyncMock())
    state = workflow.create_initial_state(
        {
            "account_id": "550e8400-e29b-41d4-a716-446655440000",
            "sections_requested": ["executive_summary"],
            "output_format": "pdf",
            "custom_inputs": {"organization_id": "forged-org"},
        },
        tenant_id="test-tenant",
    )
    # Simulate a forged runtime context: the raw tenant_id is present but the
    # authenticated claim has been cleared. Only the authenticated claim is
    # trusted by _resolve_organization_id.
    state.metadata["tenant_id"] = "forged-metadata-tenant"
    state.metadata["authenticated_tenant_id"] = None

    with pytest.raises(MissingTenantContextError):
        workflow._resolve_organization_id(state)


def test_resolve_organization_id_ignores_forged_metadata_tenant():
    workflow = BusinessCaseGeneratorWorkflow(tool_registry=AsyncMock())
    state = workflow.create_initial_state(
        {
            "account_id": "550e8400-e29b-41d4-a716-446655440000",
            "sections_requested": ["executive_summary"],
            "output_format": "pdf",
            "custom_inputs": {"organization_id": "forged-org"},
            "tenant_id": "auth-tenant-1",
        },
        tenant_id="test-tenant",
    )
    state.metadata["tenant_id"] = "forged-metadata-tenant"
    state.metadata["authenticated_tenant_id"] = "auth-tenant-1"

    assert workflow._resolve_organization_id(state) == "auth-tenant-1"
