#!/usr/bin/env python3
"""
Unit tests for the certification harness fail-closed behavior.

These tests verify that the harness correctly FAILS when:
1. No L2 extraction found for source
2. L4 workflow doesn't reach terminal completed status
3. Missing value_case_id after L4 workflow
4. No validated evidence-backed L5 TruthObjects
5. No L6 benchmark participation
6. Missing source_version_id from source creation
7. Cross-tenant isolation violation (Tenant B sees Tenant A data)
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from certify_production_path import (
    CertificationEvidence,
    ProductionPathCertifier,
    TestContext,
)


class TestHarnessFailClosed:
    """Test that harness phases fail closed when required artifacts are missing."""

    def setup_method(self):
        """Set up test certifier with mock commit SHA."""
        self.certifier = ProductionPathCertifier(commit_sha="abc123def456")
        self.certifier.ctx = TestContext(
            tenant_a="tenant-a-test",
            tenant_b="tenant-b-test",
            user_admin="admin",
            account_id="account-123",
            source_id="source-123",
            job_id="job-123",
            extraction_job_id="extraction-123",
            kg_node_ids=[],
            truth_object_ids=[],
            workflow_id="workflow-123",
            value_case_id=None,
            benchmark_comparison_id=None,
        )

    @pytest.mark.asyncio
    async def test_l2_extraction_fails_when_no_extraction_found(self):
        """Test L2 verification FAILS when no extraction found for source."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        self.certifier._request = AsyncMock(return_value=([], mock_resp))
        
        with pytest.raises(AssertionError) as exc_info:
            await self.certifier.verify_l2_extraction()
        
        assert "No L2 extraction found for source_version_id" in str(exc_info.value)
        failed_evidence = [e for e in self.certifier.evidence if e.layer == "l2" and e.status == "failed"]
        assert len(failed_evidence) == 1
        assert "No extraction found" in failed_evidence[0].output_data.get("error", "")

    @pytest.mark.asyncio
    async def test_l2_extraction_fails_when_extraction_times_out(self):
        """Test L2 verification FAILS when extraction never completes."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # Mock _request to return pending status forever
        self.certifier._request = AsyncMock(
            side_effect=[
                ({"job_id": "extraction-123", "status": "pending"}, mock_resp),
            ] * 35  # More than 30 attempts
        )
        
        with pytest.raises(AssertionError) as exc_info:
            await self.certifier.verify_l2_extraction()
        
        assert "L2 extraction timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_l2_extraction_fails_when_no_entities_extracted(self):
        """Test L2 verification FAILS when extraction completes but no entities."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        self.certifier._request = AsyncMock(
            return_value=(["ext-123"], mock_resp)  # First call: list extractions
        )
        
        with pytest.raises(AssertionError) as exc_info:
            await self.certifier.verify_l2_extraction()
        
        assert "no entities extracted" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_l4_workflow_fails_when_not_terminal(self):
        """Test L4 workflow FAILS when it never reaches completed/failed status."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp_gw = MagicMock()
        mock_resp_gw.status_code = 201
        
        self.certifier._gateway_request = AsyncMock(
            return_value=({"workflow_id": "workflow-123"}, mock_resp_gw)
        )
        self.certifier._request = AsyncMock(
            return_value=({"workflow_id": "workflow-123", "status": "running"}, mock_resp)
        )
        
        with pytest.raises(AssertionError) as exc_info:
            await self.certifier.execute_l4_workflow()
        
        assert "L4 workflow timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_l4_workflow_fails_when_no_value_case_id(self):
        """Test L4 workflow FAILS when completed but no value_case_id produced."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp_gw = MagicMock()
        mock_resp_gw.status_code = 201
        
        self.certifier._gateway_request = AsyncMock(
            return_value=({"workflow_id": "workflow-123"}, mock_resp_gw)
        )
        self.certifier._request = AsyncMock(
            return_value=({"workflow_id": "workflow-123", "status": "completed", "output": {}}, mock_resp)
        )
        
        with pytest.raises(AssertionError) as exc_info:
            await self.certifier.execute_l4_workflow()
        
        assert "no value_case_id produced" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_l5_ground_truth_fails_when_no_validated_truths(self):
        """Test L5 Ground Truth FAILS when no validated, evidence-backed TruthObjects."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        self.certifier._request = AsyncMock(
            return_value=(
                {"items": [
                    {"id": "truth-1", "status": "draft", "applies_to": {"source_version_id": "source-version-123"}, "sources": []},
                    {"id": "truth-2", "status": "proposed", "applies_to": {"source_version_id": "source-version-123"}, "sources": []},
                ]},
                mock_resp
            )
        )
        
        with pytest.raises(AssertionError) as exc_info:
            await self.certifier.verify_l5_ground_truth()
        
        assert "no validated TruthObjects found" in str(exc_info.value)
        assert "validated=0" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_l5_ground_truth_fails_when_no_truths_at_all(self):
        """Test L5 Ground Truth FAILS when no TruthObjects exist for source."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        self.certifier._request = AsyncMock(
            return_value=({"items": []}, mock_resp)
        )
        
        with pytest.raises(AssertionError) as exc_info:
            await self.certifier.verify_l5_ground_truth()
        
        assert "no validated TruthObjects found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_l6_benchmark_fails_when_no_comparisons(self):
        """Test L6 benchmark FAILS when no benchmark comparisons for value case."""
        self.certifier.ctx.value_case_id = "value-case-123"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        self.certifier._request = AsyncMock(
            return_value=({"items": []}, mock_resp)
        )
        
        with pytest.raises(AssertionError) as exc_info:
            await self.certifier.verify_l6_benchmark()
        
        assert "no comparisons found for value_case_id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_source_creation_fails_when_missing_source_version_id(self):
        """Test source creation FAILS when response missing source_version_id."""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        self.certifier._gateway_request = AsyncMock(
            return_value=({"source_id": "source-123", "id": "source-123"}, mock_resp)
        )
        
        with pytest.raises(AssertionError) as exc_info:
            await self.certifier.submit_source()
        
        assert "missing source_version_id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cross_tenant_isolation_fails_when_tenant_b_sees_tenant_a_data(self):
        """Test cross-tenant isolation FAILS when Tenant B can access Tenant A data."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp_404 = MagicMock()
        mock_resp_404.status_code = 404
        
        self.certifier._request = AsyncMock(
            side_effect=[
                # L4 account check - 404
                ({}, mock_resp_404),
                # L4 workflow check - 404  
                ({}, mock_resp_404),
                # L5 truths - returns Tenant A's truths (ISOLATION VIOLATION)
                ({"items": [
                    {"id": "truth-a1", "applies_to": {"source_version_id": "source-version-123"}}
                ]}, mock_resp),
                # L3 entities - empty
                ({"items": []}, mock_resp),
                # L6 benchmarks - empty
                ({"items": []}, mock_resp),
            ]
        )
        
        result = await self.certifier.prove_cross_tenant_isolation()
        
        assert result is False
        failed_checks = [e for e in self.certifier.evidence if e.layer == "security" and e.status == "failed"]
        assert len(failed_checks) == 1
        checks = failed_checks[0].output_data.get("checks", {})
        assert checks.get("l5_truths", {}).get("passed") is False


class TestHarnessGatewayRouting:
    """Test that user-facing operations use gateway routing."""

    def setup_method(self):
        self.certifier = ProductionPathCertifier(commit_sha="abc123def456")

    @pytest.mark.asyncio
    async def test_create_tenants_uses_gateway(self):
        """Test tenant creation uses gateway endpoint."""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        self.certifier._gateway_request = AsyncMock(
            return_value=({"id": "tenant-a-test", "slug": "tenant-a-test"}, mock_resp)
        )
        
        self.certifier.ctx = TestContext(
            tenant_a="tenant-a-test",
            tenant_b="tenant-b-test",
            user_admin="admin",
            account_id="account-123",
            source_id="",
        )
        
        await self.certifier.create_tenants()
        
        assert self.certifier._gateway_request.call_count == 2
        calls = self.certifier._gateway_request.call_args_list
        assert calls[0][0][1] == "/v1/tenants"
        assert calls[1][0][1] == "/v1/tenants"

    @pytest.mark.asyncio
    async def test_create_account_uses_gateway(self):
        """Test account creation uses gateway endpoint."""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        self.certifier._gateway_request = AsyncMock(
            return_value=({"id": "account-123"}, mock_resp)
        )
        
        self.certifier.ctx = TestContext(
            tenant_a="tenant-a-test",
            tenant_b="tenant-b-test",
            user_admin="admin",
            account_id="account-123",
            source_id="",
        )
        
        await self.certifier.create_account()
        
        self.certifier._gateway_request.assert_called_once()
        args, kwargs = self.certifier._gateway_request.call_args
        assert args[1] == "/v1/accounts"

    @pytest.mark.asyncio
    async def test_submit_source_uses_l1_direct(self):
        """Test source submission uses L1 directly (internal ingestion)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        self.certifier._gateway_request = AsyncMock(
            return_value=({"source_id": "source-123", "source_version_id": "sv-123"}, mock_resp)
        )
        
        self.certifier.ctx = TestContext(
            tenant_a="tenant-a-test",
            tenant_b="tenant-b-test",
            user_admin="admin",
            account_id="account-123",
            source_id="",
        )
        
        await self.certifier.submit_source()
        
        self.certifier._gateway_request.assert_called_once()
        args, kwargs = self.certifier._gateway_request.call_args
        assert "/api/v1/ingestion/sources" in args[1]

    @pytest.mark.asyncio
    async def test_execute_workflow_uses_gateway(self):
        """Test workflow execution uses gateway endpoint."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp_gw = MagicMock()
        mock_resp_gw.status_code = 201
        
        self.certifier._gateway_request = AsyncMock(
            return_value=({"workflow_id": "wf-123"}, mock_resp_gw)
        )
        self.certifier._request = AsyncMock(
            return_value=({"status": "completed", "value_case_id": "vc-123"}, mock_resp)
        )
        
        self.certifier.ctx = TestContext(
            tenant_a="tenant-a-test",
            tenant_b="tenant-b-test",
            user_admin="admin",
            account_id="account-123",
            source_id="source-123",
            source_version_id="sv-123",
        )
        
        await self.certifier.execute_l4_workflow()
        
        self.certifier._gateway_request.assert_called()
        args, kwargs = self.certifier._gateway_request.call_args
        assert "/v1/workflows" in args[1]

    @pytest.mark.asyncio
    async def test_retrieve_value_case_uses_gateway(self):
        """Test value case retrieval uses gateway endpoint."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        self.certifier._gateway_request = AsyncMock(
            return_value=({"items": [{"account_id": "account-123"}]}, mock_resp)
        )
        
        self.certifier.ctx = TestContext(
            tenant_a="tenant-a-test",
            tenant_b="tenant-b-test",
            user_admin="admin",
            account_id="account-123",
            source_id="source-123",
        )
        
        await self.certifier.retrieve_value_case_via_gateway()
        
        self.certifier._gateway_request.assert_called_once()
        args, kwargs = self.certifier._gateway_request.call_args
        assert "/v1/accounts/account-123/value-cases" in args[1]


class TestHarnessDirectLayerCalls:
    """Test that direct layer calls are only used for postcondition inspection."""

    def setup_method(self):
        self.certifier = ProductionPathCertifier(commit_sha="abc123def456")

    @pytest.mark.asyncio
    async def test_l2_verification_uses_direct_layer(self):
        """Test L2 verification uses direct layer call for postcondition check."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        self.certifier._request = AsyncMock(
            return_value=([{"job_id": "ext-123", "status": "completed", "entities": [{"id": "e1"}]}], mock_resp)
        )
        
        self.certifier.ctx = TestContext(
            tenant_a="tenant-a-test",
            tenant_b="tenant-b-test",
            user_admin="admin",
            account_id="account-123",
            source_id="source-123",
            source_version_id="sv-123",
        )
        
        await self.certifier.verify_l2_extraction()
        
        self.certifier._request.assert_called()
        for call in self.certifier._request.call_args_list:
            assert call[0][0] == "l2"

    @pytest.mark.asyncio
    async def test_l3_verification_uses_direct_layer(self):
        """Test L3 verification uses direct layer call for postcondition check."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        self.certifier._request = AsyncMock(
            return_value=({"results": [{"id": "e1", "source_version_id": "sv-123"}]}, mock_resp)
        )
        
        self.certifier.ctx = TestContext(
            tenant_a="tenant-a-test",
            tenant_b="tenant-b-test",
            user_admin="admin",
            account_id="account-123",
            source_id="source-123",
            source_version_id="sv-123",
        )
        
        await self.certifier.verify_l3_graph()
        
        self.certifier._request.assert_called()
        for call in self.certifier._request.call_args_list:
            assert call[0][0] == "l3"

    @pytest.mark.asyncio
    async def test_l5_verification_uses_direct_layer(self):
        """Test L5 verification uses direct layer call for postcondition check."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        self.certifier._request = AsyncMock(
            return_value=({"items": [
                {"id": "t1", "status": "validated", "applies_to": {"source_version_id": "sv-123"}, "sources": ["src1"]}
            ]}, mock_resp)
        )
        
        self.certifier.ctx = TestContext(
            tenant_a="tenant-a-test",
            tenant_b="tenant-b-test",
            user_admin="admin",
            account_id="account-123",
            source_id="source-123",
            source_version_id="sv-123",
            workflow_id="wf-123",
        )
        
        await self.certifier.verify_l5_ground_truth()
        
        self.certifier._request.assert_called()
        for call in self.certifier._request.call_args_list:
            assert call[0][0] == "l5"


class TestReadinessChecks:
    """Test that readiness checks are explicit and fail when service unready."""

    def setup_method(self):
        self.certifier = ProductionPathCertifier(commit_sha="abc123def456")

    @pytest.mark.asyncio
    async def test_wait_for_service_ready_passes_on_ready(self):
        """Test wait_for_service_ready passes when service is ready."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(
            side_effect=[
                MagicMock(status_code=200),  # health
                MagicMock(status_code=200),  # ready
            ]
        )
        
        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await self.certifier.wait_for_service_ready("l4", max_attempts=1)
            assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_service_ready_fails_on_health_failure(self):
        """Test wait_for_service_ready fails when health check fails."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=MagicMock(status_code=503))
        
        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await self.certifier.wait_for_service_ready("l4", max_attempts=2)
            assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_service_ready_fails_on_ready_failure(self):
        """Test wait_for_service_ready fails when ready check fails."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(
            side_effect=[
                MagicMock(status_code=200),  # health OK
                MagicMock(status_code=503),  # ready FAIL
            ]
        )
        
        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await self.certifier.wait_for_service_ready("l4", max_attempts=2)
            assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_service_ready_times_out(self):
        """Test wait_for_service_ready fails after max attempts."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(
            side_effect=[
                MagicMock(status_code=200),  # health OK
                MagicMock(status_code=503),  # ready not ready
            ] * 15  # 30 attempts
        )
        
        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await self.certifier.wait_for_service_ready("l4", max_attempts=30)
            assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
