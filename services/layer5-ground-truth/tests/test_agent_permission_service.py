"""
Integration tests for Agent Permission Service.

Tests for agent permission checks for formula/benchmark application.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from layer5_ground_truth.models.formula_governance import (
    Formula,
    FormulaStatus,
    FormulaVersion,
)
from layer5_ground_truth.models.benchmark_governance import (
    BenchmarkDataset,
    BenchmarkStatus,
    BenchmarkVersion,
)
from layer5_ground_truth.models.policy_governance import Policy, PolicyApplication
from layer5_ground_truth.services.agent_permission_service import (
    AgentPermissionError,
    AgentPermissionService,
)
from tests.conftest import TEST_ORG_ID


class TestAgentPermissionService:
    @pytest.mark.asyncio
    async def test_can_use_approved_formula(self, db):
        """Should allow using an approved formula."""
        service = AgentPermissionService()
        formula = Formula(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="ROI Formula",
            slug="roi-formula",
            formula_type="roi_calculation",
            current_version="1.0.0",
            latest_version="1.0.0",
            input_schema={},
            output_schema={},
            is_active=True,
        )
        db.add(formula)
        await db.flush()

        version = FormulaVersion(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            formula_id=formula.id,
            version="1.0.0",
            expression="return value",
            expression_language="python",
            status=FormulaStatus.APPROVED.value,
        )
        db.add(version)
        await db.flush()

        can_use, reason = await service.can_use_formula(
            db=db,
            tenant_id=TEST_ORG_ID,
            formula_id=formula.id,
        )

        assert can_use is True
        assert "approved" in reason.lower()

    @pytest.mark.asyncio
    async def test_cannot_use_unapproved_formula(self, db):
        """Should deny using an unapproved formula."""
        service = AgentPermissionService()
        formula = Formula(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="ROI Formula",
            slug="roi-formula",
            formula_type="roi_calculation",
            current_version="1.0.0",
            latest_version="1.0.0",
            input_schema={},
            output_schema={},
            is_active=True,
        )
        db.add(formula)
        await db.flush()

        version = FormulaVersion(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            formula_id=formula.id,
            version="1.0.0",
            expression="return value",
            expression_language="python",
            status=FormulaStatus.DRAFT.value,  # Not approved
        )
        db.add(version)
        await db.flush()

        can_use, reason = await service.can_use_formula(
            db=db,
            tenant_id=TEST_ORG_ID,
            formula_id=formula.id,
        )

        assert can_use is False
        assert "not approved" in reason.lower()

    @pytest.mark.asyncio
    async def test_cannot_use_deprecated_formula(self, db):
        """Should deny using a deprecated formula."""
        service = AgentPermissionService()
        formula = Formula(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="Old Formula",
            slug="old-formula",
            formula_type="custom",
            current_version="1.0.0",
            latest_version="1.0.0",
            input_schema={},
            output_schema={},
            is_active=False,
            deprecated_at=datetime.now(UTC),
            deprecation_reason="Replaced",
        )
        db.add(formula)
        await db.flush()

        can_use, reason = await service.can_use_formula(
            db=db,
            tenant_id=TEST_ORG_ID,
            formula_id=formula.id,
        )

        assert can_use is False
        assert "deprecated" in reason.lower()

    @pytest.mark.asyncio
    async def test_cannot_use_formula_not_found(self, db):
        """Should deny using a non-existent formula."""
        service = AgentPermissionService()

        can_use, reason = await service.can_use_formula(
            db=db,
            tenant_id=TEST_ORG_ID,
            formula_id=uuid.uuid4(),
        )

        assert can_use is False
        assert "not found" in reason.lower()

    @pytest.mark.asyncio
    async def test_can_use_approved_benchmark(self, db):
        """Should allow using an approved and effective benchmark."""
        service = AgentPermissionService()
        benchmark = BenchmarkDataset(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="Industry Benchmark",
            dataset_uri="s3://test-benchmarks/industry.json",
            slug="industry-benchmark",
            benchmark_type="industry_standard",
            current_version="1.0.0",
            latest_version="1.0.0",
            source_name="Gartner",
            source_type="research",
            confidence_level="high",
            is_active=True,
        )
        db.add(benchmark)
        await db.flush()

        version = BenchmarkVersion(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            benchmark_id=benchmark.id,
            version="1.0.0",
            data={},
            data_schema={},
            effective_from=datetime(2025, 1, 1, tzinfo=UTC),
            status=BenchmarkStatus.APPROVED.value,
        )
        db.add(version)
        await db.flush()

        can_use, reason = await service.can_use_benchmark(
            db=db,
            tenant_id=TEST_ORG_ID,
            benchmark_id=benchmark.id,
        )

        assert can_use is True
        assert "approved" in reason.lower()

    @pytest.mark.asyncio
    async def test_cannot_use_benchmark_not_yet_effective(self, db):
        """Should deny using a benchmark that is not yet effective."""
        service = AgentPermissionService()
        benchmark = BenchmarkDataset(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="Future Benchmark",
            dataset_uri="s3://test-benchmarks/future.json",
            slug="future-benchmark",
            benchmark_type="industry_standard",
            current_version="1.0.0",
            latest_version="1.0.0",
            source_name="Gartner",
            source_type="research",
            confidence_level="high",
            is_active=True,
        )
        db.add(benchmark)
        await db.flush()

        # Effective date in the future
        future_date = datetime(2030, 1, 1, tzinfo=UTC)
        version = BenchmarkVersion(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            benchmark_id=benchmark.id,
            version="1.0.0",
            data={},
            data_schema={},
            effective_from=future_date,
            status=BenchmarkStatus.APPROVED.value,
        )
        db.add(version)
        await db.flush()

        can_use, reason = await service.can_use_benchmark(
            db=db,
            tenant_id=TEST_ORG_ID,
            benchmark_id=benchmark.id,
        )

        assert can_use is False
        assert "not yet effective" in reason.lower()

    @pytest.mark.asyncio
    async def test_cannot_use_expired_benchmark(self, db):
        """Should deny using an expired benchmark."""
        service = AgentPermissionService()
        benchmark = BenchmarkDataset(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="Expired Benchmark",
            dataset_uri="s3://test-benchmarks/expired.json",
            slug="expired-benchmark",
            benchmark_type="industry_standard",
            current_version="1.0.0",
            latest_version="1.0.0",
            source_name="Gartner",
            source_type="research",
            confidence_level="high",
            is_active=True,
        )
        db.add(benchmark)
        await db.flush()

        # Effective date in the past, expired
        version = BenchmarkVersion(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            benchmark_id=benchmark.id,
            version="1.0.0",
            data={},
            data_schema={},
            effective_from=datetime(2020, 1, 1, tzinfo=UTC),
            effective_until=datetime(2021, 1, 1, tzinfo=UTC),
            status=BenchmarkStatus.APPROVED.value,
        )
        db.add(version)
        await db.flush()

        can_use, reason = await service.can_use_benchmark(
            db=db,
            tenant_id=TEST_ORG_ID,
            benchmark_id=benchmark.id,
        )

        assert can_use is False
        assert "expired" in reason.lower()

    @pytest.mark.asyncio
    async def test_require_formula_permission_raises_error(self, db):
        """Should raise AgentPermissionError when formula cannot be used."""
        service = AgentPermissionService()
        formula = Formula(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="Unapproved Formula",
            slug="unapproved-formula",
            formula_type="custom",
            current_version="1.0.0",
            latest_version="1.0.0",
            input_schema={},
            output_schema={},
            is_active=True,
        )
        db.add(formula)
        await db.flush()

        version = FormulaVersion(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            formula_id=formula.id,
            version="1.0.0",
            expression="return value",
            expression_language="python",
            status=FormulaStatus.DRAFT.value,
        )
        db.add(version)
        await db.flush()

        with pytest.raises(AgentPermissionError):
            await service.require_formula_permission(
                db=db,
                tenant_id=TEST_ORG_ID,
                formula_id=formula.id,
            )

    @pytest.mark.asyncio
    async def test_require_benchmark_permission_raises_error(self, db):
        """Should raise AgentPermissionError when benchmark cannot be used."""
        service = AgentPermissionService()
        benchmark = BenchmarkDataset(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="Unapproved Benchmark",
            dataset_uri="s3://test-benchmarks/unapproved.json",
            slug="unapproved-benchmark",
            benchmark_type="custom",
            current_version="1.0.0",
            latest_version="1.0.0",
            source_name="Test",
            source_type="internal",
            confidence_level="medium",
            is_active=True,
        )
        db.add(benchmark)
        await db.flush()

        version = BenchmarkVersion(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            benchmark_id=benchmark.id,
            version="1.0.0",
            data={},
            data_schema={},
            effective_from=datetime.now(UTC),
            status=BenchmarkStatus.DRAFT.value,
        )
        db.add(version)
        await db.flush()

        with pytest.raises(AgentPermissionError):
            await service.require_benchmark_permission(
                db=db,
                tenant_id=TEST_ORG_ID,
                benchmark_id=benchmark.id,
            )

    @pytest.mark.asyncio
    async def test_check_policy_compliance_no_policies(self, db):
        """Should return compliant when no policies exist."""
        service = AgentPermissionService()

        is_compliant, results = await service.check_policy_compliance(
            db=db,
            tenant_id=TEST_ORG_ID,
            entity_type="formula",
            entity_id=uuid.uuid4(),
        )

        assert is_compliant is True
        assert results == []

    @pytest.mark.asyncio
    async def test_record_policy_application(self, db):
        """Should record policy application for audit."""
        from layer5_ground_truth.models.policy_governance import Policy

        service = AgentPermissionService()
        policy = Policy(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="Test Policy",
            slug="test-policy",
            policy_type="custom",
            current_version="1.0.0",
            latest_version="1.0.0",
            applies_to_entity_types=["formula"],
            is_active=True,
        )
        db.add(policy)
        await db.flush()

        application = await service.record_policy_application(
            db=db,
            tenant_id=TEST_ORG_ID,
            policy_id=policy.id,
            entity_type="formula",
            entity_id=uuid.uuid4(),
            entity_version="1.0.0",
            result="passed",
            rule_results=[{"rule_id": "1", "result": "passed"}],
            applied_by="system",
            context={"test": True},
        )

        assert application.policy_id == policy.id
        assert application.result == "passed"
        assert application.rule_results is not None

    @pytest.mark.asyncio
    async def test_check_policy_compliance_mandatory_pass(self, db):
        service = AgentPermissionService()
        formula = Formula(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="Compliant Formula",
            slug="compliant-formula",
            formula_type="roi_calculation",
            current_version="1.0.0",
            latest_version="1.0.0",
            input_schema={},
            output_schema={},
            is_active=True,
        )
        db.add(formula)
        db.add(
            FormulaVersion(
                id=uuid.uuid4(),
                tenant_id=TEST_ORG_ID,
                formula_id=formula.id,
                version="1.0.0",
                expression="return value",
                expression_language="python",
                status=FormulaStatus.APPROVED.value,
            )
        )
        db.add(
            Policy(
                id=uuid.uuid4(),
                tenant_id=TEST_ORG_ID,
                name="Formula Must Be Approved",
                slug="formula-approved",
                policy_type="formula_approval",
                current_version="2.0.0",
                latest_version="2.0.0",
                applies_to_entity_types=["formula"],
                is_mandatory=True,
                is_active=True,
            )
        )
        await db.flush()

        compliant, results = await service.check_policy_compliance(
            db=db, tenant_id=TEST_ORG_ID, entity_type="formula", entity_id=formula.id
        )
        assert compliant is True
        assert len(results) == 1
        assert results[0]["result"] == "passed"

    @pytest.mark.asyncio
    async def test_check_policy_compliance_mandatory_fail(self, db):
        service = AgentPermissionService()
        formula = Formula(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="Non-compliant Formula",
            slug="non-compliant-formula",
            formula_type="roi_calculation",
            current_version="1.0.0",
            latest_version="1.0.0",
            input_schema={},
            output_schema={},
            is_active=True,
        )
        db.add(formula)
        db.add(
            FormulaVersion(
                id=uuid.uuid4(),
                tenant_id=TEST_ORG_ID,
                formula_id=formula.id,
                version="1.0.0",
                expression="return value",
                expression_language="python",
                status=FormulaStatus.DRAFT.value,
            )
        )
        db.add(
            Policy(
                id=uuid.uuid4(),
                tenant_id=TEST_ORG_ID,
                name="Formula Must Be Approved",
                slug="formula-approved-fail",
                policy_type="formula_approval",
                current_version="2.0.0",
                latest_version="2.0.0",
                applies_to_entity_types=["formula"],
                is_mandatory=True,
                is_active=True,
            )
        )
        await db.flush()

        compliant, results = await service.check_policy_compliance(
            db=db, tenant_id=TEST_ORG_ID, entity_type="formula", entity_id=formula.id
        )
        assert compliant is False
        assert results[0]["result"] == "failed"

    @pytest.mark.asyncio
    async def test_check_policy_compliance_advisory_warns(self, db):
        service = AgentPermissionService()
        formula_id = uuid.uuid4()
        db.add(
            Policy(
                id=uuid.uuid4(),
                tenant_id=TEST_ORG_ID,
                name="Advisory Formula Approval",
                slug="formula-advisory",
                policy_type="formula_approval",
                current_version="1.0.0",
                latest_version="1.0.0",
                applies_to_entity_types=["formula"],
                is_mandatory=False,
                is_active=True,
            )
        )
        await db.flush()

        compliant, results = await service.check_policy_compliance(
            db=db, tenant_id=TEST_ORG_ID, entity_type="formula", entity_id=formula_id
        )
        assert compliant is True
        assert results[0]["result"] == "warning"

    @pytest.mark.asyncio
    async def test_check_policy_compliance_unknown_policy_type_fails_closed(self, db):
        service = AgentPermissionService()
        db.add(
            Policy(
                id=uuid.uuid4(),
                tenant_id=TEST_ORG_ID,
                name="Unknown Type",
                slug="unknown-type-policy",
                policy_type="new_unknown_type",
                current_version="1.0.0",
                latest_version="1.0.0",
                applies_to_entity_types=["formula"],
                is_mandatory=True,
                is_active=True,
            )
        )
        await db.flush()

        compliant, results = await service.check_policy_compliance(
            db=db, tenant_id=TEST_ORG_ID, entity_type="formula", entity_id=uuid.uuid4()
        )
        assert compliant is False
        assert results[0]["result"] == "failed"
        assert "unknown policy type" in results[0]["message"].lower()

    @pytest.mark.asyncio
    async def test_check_policy_compliance_enforces_tenant_isolation(self, db):
        service = AgentPermissionService()
        tenant_b = uuid.uuid4()
        formula_b = Formula(
            id=uuid.uuid4(),
            tenant_id=tenant_b,
            name="Tenant B Formula",
            slug="tenant-b-formula",
            formula_type="roi_calculation",
            current_version="1.0.0",
            latest_version="1.0.0",
            input_schema={},
            output_schema={},
            is_active=True,
        )
        db.add(formula_b)
        db.add(
            FormulaVersion(
                id=uuid.uuid4(),
                tenant_id=tenant_b,
                formula_id=formula_b.id,
                version="1.0.0",
                expression="return value",
                expression_language="python",
                status=FormulaStatus.APPROVED.value,
            )
        )
        db.add(
            Policy(
                id=uuid.uuid4(),
                tenant_id=TEST_ORG_ID,
                name="Tenant A Formula Approval",
                slug="tenant-a-formula-approval",
                policy_type="formula_approval",
                current_version="1.0.0",
                latest_version="1.0.0",
                applies_to_entity_types=["formula"],
                is_mandatory=True,
                is_active=True,
            )
        )
        await db.flush()

        compliant, results = await service.check_policy_compliance(
            db=db, tenant_id=TEST_ORG_ID, entity_type="formula", entity_id=formula_b.id
        )
        assert compliant is False
        assert results[0]["result"] == "failed"
        applications = (await db.execute(select(PolicyApplication))).scalars().all()
        assert len(applications) >= 1
