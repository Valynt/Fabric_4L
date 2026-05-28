from __future__ import annotations

"""Tests for export provenance manifest determinism and completeness."""


from typing import Any

from value_fabric.layer4.services.export_provenance import build_export_provenance_manifest
from value_fabric.shared.models.typed_dict import TypedDictModel


class _frozen_workflow_resultResult(TypedDictModel):
    completed_at: str
    created_at: str
    metadata: dict[str, Any]
    output: dict[str, Any]
    workflow_id: str


def _frozen_workflow_result() -> dict:
    return _frozen_workflow_resultResult.model_validate({
        "workflow_id": "wf-123",
        "created_at": "2026-04-01T00:00:00Z",
        "completed_at": "2026-04-01T00:05:00Z",
        "metadata": {
            "case_snapshot": {
                "id": "snap-123",
                "version": "v7",
                "version_hash": "sha256:abc123",
                "assumptions": ["adoption at 70%", "year-1 rollout"],
                "source_pointers": [
                    {"pointer": "doc://source-a", "type": "document"},
                    {"pointer": "doc://source-b", "type": "document"},
                ],
                "approvals": [
                    {"who": "risk.board", "when": "2026-03-15T10:00:00Z", "decision": "approved"}
                ],
                "metric_formulas": [
                    {
                        "metric": "roi",
                        "formula": "(benefit - cost) / cost",
                        "inputs": ["benefit", "cost"],
                        "input_provenance": ["truth://benefit", "truth://cost"],
                    }
                ],
                "narrative_claims": [
                    {
                        "claim_id": "claim-1",
                        "text": "Automation reduces handling time by 25%.",
                        "evidence_pointers": ["truth://claim-1"],
                    }
                ],
            }
        },
        "output": {
            "assemble_document": {
                "case_metadata": {
                    "truth_references": [
                        {"truth_object_id": "truth-1"},
                        {"truth_object_id": "truth-2"},
                    ]
                }
            }
        },
    })


def test_snapshot_replay_deterministic_snapshot_stable() -> None:
    workflow_result = _frozen_workflow_result()

    manifest_a = build_export_provenance_manifest(
        case_id="case-1",
        workflow_result=workflow_result,
        actor_context=None,
        export_id="exp-1",
    )
    manifest_b = build_export_provenance_manifest(
        case_id="case-1",
        workflow_result=workflow_result,
        actor_context=None,
        export_id="exp-2",
    )

    assert manifest_a["deterministic_snapshot"] == manifest_b["deterministic_snapshot"]
    assert manifest_a["deterministic_snapshot"]["provenance_validation"]["is_valid"] is True
    assert manifest_a["envelope"]["export_id"] != manifest_b["envelope"]["export_id"]


def test_provenance_validation_flags_missing_links() -> None:
    workflow_result = _frozen_workflow_result()
    snapshot = workflow_result["metadata"]["case_snapshot"]

    snapshot["narrative_claims"] = [{"claim_id": "claim-without-evidence", "text": "Unsupported claim"}]
    snapshot["metric_formulas"] = [{"metric": "roi", "formula": "benefit/cost", "inputs": ["benefit"]}]

    manifest = build_export_provenance_manifest(
        case_id="case-1",
        workflow_result=workflow_result,
        actor_context=None,
        export_id="exp-3",
    )

    validation = manifest["deterministic_snapshot"]["provenance_validation"]
    assert validation["is_valid"] is False
    violation_types = {v["type"] for v in validation["violations"]}
    assert "narrative_claim_missing_evidence" in violation_types
    assert "metric_missing_input_provenance" in violation_types
