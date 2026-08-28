"""
Contract and behavior tests for Pillar 3: IntegrityAgent Hard Gate.

Proves:
1. Missing IntegrityArtifact -> 422 INTEGRITY_GATE_OPEN.
2. Mismatched content hash (stale integrity) -> 422 INTEGRITY_GATE_OPEN.
3. Unresolved findings -> 422 INTEGRITY_GATE_OPEN.
4. Passing IntegrityArtifact matching exact hashes -> 200 Export Success.
5. CRM sync fails closed if integrity expires or content changes after human approval.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from layer4_agents.api.routes.narratives import NarrativeExportRequest, export_narrative
from layer4_agents.contracts.artifacts import IntegrityPrecondition
from layer4_agents.integration.connectors.core.errors import IntegrityGateOpenError
from layer4_agents.services.crm_sync_service import CRMSyncService
from value_fabric.shared.error_handling.exceptions import ValidationError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_narrative_export_missing_integrity_fails_closed():
    """Prove export fails closed with 422 INTEGRITY_GATE_OPEN when integrity precondition is missing."""
    mock_request = MagicMock()
    mock_driver = MagicMock()
    mock_request.app.state.neo4j_driver = mock_driver

    mock_svc = AsyncMock()
    mock_svc.get_narrative.return_value = {
        "id": "nar_123",
        "title": "Value Case",
        "sections": {},
    }

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "layer4_agents.services.narrative_builder_service.NarrativeBuilderService",
            lambda d: mock_svc,
        )

        export_req = NarrativeExportRequest(
            format="PDF",
            narrative_version=1,
            narrative_content_hash="hash_abc123",
            evidence_set_hash="hash_evid456",
            integrity_precondition=None,
        )

        with pytest.raises(ValidationError) as exc_info:
            await export_narrative("nar_123", export_req, mock_request, tenant_id="tenant_001")

        assert exc_info.value.status_code == 422
        detail = exc_info.value.details
        assert detail["code"] == "INTEGRITY_GATE_OPEN"
        assert detail["integrity_status"] == "missing"
        assert detail["required_action"] == "rerun_integrity_validation"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_narrative_export_mismatched_content_hash_fails_closed():
    """Prove export fails closed if narrative content hash does not match the integrity precondition."""
    mock_request = MagicMock()
    mock_driver = MagicMock()
    mock_request.app.state.neo4j_driver = mock_driver

    mock_svc = AsyncMock()
    mock_svc.get_narrative.return_value = {
        "id": "nar_123",
        "title": "Value Case",
        "sections": {},
    }

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "layer4_agents.services.narrative_builder_service.NarrativeBuilderService",
            lambda d: mock_svc,
        )

        # Precondition was evaluated for old content hash
        precondition = IntegrityPrecondition(
            narrative_artifact_id="nar_123",
            narrative_version=1,
            narrative_content_hash="old_hash_999",
            evidence_set_hash="hash_evid456",
            tenant_id="tenant_001",
            account_id="acc_001",
            status="passed",
            unresolved_findings=0,
        )

        export_req = NarrativeExportRequest(
            format="PDF",
            narrative_version=1,
            narrative_content_hash="new_edited_hash_000",
            evidence_set_hash="hash_evid456",
            integrity_precondition=precondition,
        )

        with pytest.raises(ValidationError) as exc_info:
            await export_narrative("nar_123", export_req, mock_request, tenant_id="tenant_001")

        assert exc_info.value.status_code == 422
        detail = exc_info.value.details
        assert detail["code"] == "INTEGRITY_GATE_OPEN"
        assert detail["integrity_status"] == "mismatched"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_narrative_export_unresolved_findings_fails_closed():
    """Prove export fails closed if IntegrityArtifact has unresolved findings."""
    mock_request = MagicMock()
    mock_driver = MagicMock()
    mock_request.app.state.neo4j_driver = mock_driver

    mock_svc = AsyncMock()
    mock_svc.get_narrative.return_value = {
        "id": "nar_123",
        "title": "Value Case",
        "sections": {},
    }

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "layer4_agents.services.narrative_builder_service.NarrativeBuilderService",
            lambda d: mock_svc,
        )

        precondition = IntegrityPrecondition(
            narrative_artifact_id="nar_123",
            narrative_version=1,
            narrative_content_hash="hash_abc123",
            evidence_set_hash="hash_evid456",
            tenant_id="tenant_001",
            account_id="acc_001",
            status="passed",
            unresolved_findings=2,  # Has unresolved findings
        )

        export_req = NarrativeExportRequest(
            format="PDF",
            narrative_version=1,
            narrative_content_hash="hash_abc123",
            evidence_set_hash="hash_evid456",
            integrity_precondition=precondition,
        )

        with pytest.raises(ValidationError) as exc_info:
            await export_narrative("nar_123", export_req, mock_request, tenant_id="tenant_001")

        assert exc_info.value.status_code == 422
        detail = exc_info.value.details
        assert detail["code"] == "INTEGRITY_GATE_OPEN"
        assert detail["integrity_status"] == "unresolved_findings"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_narrative_export_valid_integrity_succeeds():
    """Prove export succeeds when all integrity preconditions are met."""
    mock_request = MagicMock()
    mock_driver = MagicMock()
    mock_request.app.state.neo4j_driver = mock_driver

    mock_svc = AsyncMock()
    mock_svc.get_narrative.return_value = {
        "id": "nar_123",
        "title": "Value Case",
        "sections": {},
    }

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "layer4_agents.services.narrative_builder_service.NarrativeBuilderService",
            lambda d: mock_svc,
        )

        precondition = IntegrityPrecondition(
            narrative_artifact_id="nar_123",
            narrative_version=1,
            narrative_content_hash="hash_abc123",
            evidence_set_hash="hash_evid456",
            tenant_id="tenant_001",
            account_id="acc_001",
            status="passed",
            unresolved_findings=0,
        )

        export_req = NarrativeExportRequest(
            format="PDF",
            narrative_version=1,
            narrative_content_hash="hash_abc123",
            evidence_set_hash="hash_evid456",
            integrity_precondition=precondition,
        )

        result = await export_narrative("nar_123", export_req, mock_request, tenant_id="tenant_001")

        assert result["status"] == "success"
        assert result["narrative_id"] == "nar_123"
        assert result["format"] == "PDF"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_crm_sync_toctou_defense_fails_closed_on_stale_or_mismatched():
    """Prove CRM write delegation fails closed if human approval or integrity is mismatched."""
    mock_db = AsyncMock()
    crm_service = CRMSyncService(mock_db)

    valid_precondition = IntegrityPrecondition(
        narrative_artifact_id="nar_123",
        narrative_version=1,
        narrative_content_hash="hash_abc123",
        evidence_set_hash="hash_evid456",
        tenant_id="tenant_001",
        account_id="acc_001",
        status="passed",
        unresolved_findings=0,
    )

    # 1. Mismatched human approval vs content hash
    with pytest.raises(IntegrityGateOpenError) as exc1:
        await crm_service.sync_narrative_to_crm(
            tenant_id="tenant_001",
            account_id="acc_001",
            narrative_artifact_id="nar_123",
            narrative_version=1,
            narrative_content_hash="hash_abc123",
            evidence_set_hash="hash_evid456",
            human_approved_hash="old_different_hash",  # Stale approval!
            integrity_precondition=valid_precondition,
        )
    assert exc1.value.detail["code"] == "INTEGRITY_GATE_OPEN"
    assert exc1.value.detail["integrity_status"] == "mismatched"

    # 2. Stale / failed integrity precondition
    stale_precondition = IntegrityPrecondition(
        narrative_artifact_id="nar_123",
        narrative_version=1,
        narrative_content_hash="hash_abc123",
        evidence_set_hash="hash_evid456",
        tenant_id="tenant_001",
        account_id="acc_001",
        status="stale",
        unresolved_findings=0,
    )
    with pytest.raises(IntegrityGateOpenError) as exc2:
        await crm_service.sync_narrative_to_crm(
            tenant_id="tenant_001",
            account_id="acc_001",
            narrative_artifact_id="nar_123",
            narrative_version=1,
            narrative_content_hash="hash_abc123",
            evidence_set_hash="hash_evid456",
            human_approved_hash="hash_abc123",
            integrity_precondition=stale_precondition,
        )
    assert exc2.value.detail["code"] == "INTEGRITY_GATE_OPEN"
    assert exc2.value.detail["integrity_status"] == "stale"

    # 3. Valid CRM sync
    res = await crm_service.sync_narrative_to_crm(
        tenant_id="tenant_001",
        account_id="acc_001",
        narrative_artifact_id="nar_123",
        narrative_version=1,
        narrative_content_hash="hash_abc123",
        evidence_set_hash="hash_evid456",
        human_approved_hash="hash_abc123",
        integrity_precondition=valid_precondition,
    )
    assert res["status"] == "synced"
    assert res["narrative_artifact_id"] == "nar_123"
