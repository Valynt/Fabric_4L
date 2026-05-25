"""
Unit tests for Policy Governance models.

Tests for Policy, PolicyVersion, PolicyRule, and PolicyApplication models.
"""

import uuid
from datetime import UTC, datetime

import pytest

from layer5_ground_truth.models.policy_governance import (
    Policy,
    PolicyApplication,
    PolicyRule,
    PolicyStatus,
    PolicyType,
    PolicyVersion,
    RuleOperator,
)


class TestPolicy:
    def test_create_policy(self):
        """Should create a policy with required fields."""
        policy = Policy(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Formula Approval Policy",
            slug="formula-approval-policy",
            policy_type=PolicyType.FORMULA_APPROVAL.value,
            description="Policy governing formula approval requirements",
            current_version="1.0.0",
            latest_version="1.0.0",
            is_mandatory=True,
            severity="high",
            applies_to_entity_types=["formula"],
            is_active=True,
        )
        assert policy.slug == "formula-approval-policy"
        assert policy.policy_type == PolicyType.FORMULA_APPROVAL.value
        assert policy.is_mandatory is True
        assert policy.severity == "high"

    def test_policy_type_enum_values(self):
        """PolicyType enum should have expected values."""
        assert {s.value for s in PolicyType} == {
            "formula_approval",
            "benchmark_approval",
            "assumption_approval",
            "value_threshold",
            "risk_assessment",
            "compliance",
            "custom",
        }

    def test_policy_severity_levels(self):
        """Should support different severity levels."""
        for severity in ["low", "medium", "high", "critical"]:
            policy = Policy(
                id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                name="Test Policy",
                slug=f"test-policy-{severity}",
                policy_type=PolicyType.CUSTOM.value,
                current_version="1.0.0",
                latest_version="1.0.0",
                severity=severity,
                applies_to_entity_types=[],
                is_active=True,
            )
            assert policy.severity == severity

    def test_policy_applies_to_multiple_entity_types(self):
        """Should apply to multiple entity types."""
        policy = Policy(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Multi-Entity Policy",
            slug="multi-entity-policy",
            policy_type=PolicyType.CUSTOM.value,
            current_version="1.0.0",
            latest_version="1.0.0",
            applies_to_entity_types=["formula", "benchmark", "assumption"],
            is_active=True,
        )
        assert policy.applies_to_entity_types == ["formula", "benchmark", "assumption"]


class TestPolicyVersion:
    def test_create_policy_version(self):
        """Should create a policy version with required fields."""
        version = PolicyVersion(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            policy_id=uuid.uuid4(),
            version="1.0.0",
            rules_engine_config={"rules": []},
            effective_from=datetime.now(UTC),
            status=PolicyStatus.DRAFT.value,
        )
        assert version.version == "1.0.0"
        assert version.rules_engine_config is not None
        assert version.status == PolicyStatus.DRAFT.value

    def test_policy_status_enum_values(self):
        """PolicyStatus enum should have expected values."""
        assert {s.value for s in PolicyStatus} == {
            "draft",
            "pending_approval",
            "approved",
            "deprecated",
            "archived",
        }

    def test_policy_version_effective_dates(self):
        """Should support effective date ranges."""
        effective_from = datetime(2025, 1, 1, tzinfo=UTC)
        effective_until = datetime(2025, 12, 31, tzinfo=UTC)
        version = PolicyVersion(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            policy_id=uuid.uuid4(),
            version="1.0.0",
            rules_engine_config={},
            effective_from=effective_from,
            effective_until=effective_until,
            status=PolicyStatus.APPROVED.value,
        )
        assert version.effective_from == effective_from
        assert version.effective_until == effective_until


class TestPolicyRule:
    def test_create_policy_rule(self):
        """Should create a policy rule with required fields."""
        rule = PolicyRule(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            policy_id=uuid.uuid4(),
            rule_name="Minimum Confidence",
            rule_order=1,
            target_field="confidence",
            operator=RuleOperator.GREATER_THAN_OR_EQUAL.value,
            expected_value=0.5,
            error_message="Confidence must be at least 0.5",
            is_blocking=True,
            severity="high",
        )
        assert rule.rule_name == "Minimum Confidence"
        assert rule.operator == RuleOperator.GREATER_THAN_OR_EQUAL.value
        assert rule.is_blocking is True

    def test_rule_operator_enum_values(self):
        """RuleOperator enum should have expected values."""
        assert {s.value for s in RuleOperator} == {
            "equals",
            "not_equals",
            "greater_than",
            "less_than",
            "greater_than_or_equal",
            "less_than_or_equal",
            "contains",
            "not_contains",
            "in",
            "not_in",
            "regex",
        }

    def test_policy_rule_ordering(self):
        """Should support rule ordering."""
        rule1 = PolicyRule(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            policy_id=uuid.uuid4(),
            rule_name="First Rule",
            rule_order=1,
            target_field="field1",
            operator="equals",
            expected_value="value1",
        )
        rule2 = PolicyRule(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            policy_id=uuid.uuid4(),
            rule_name="Second Rule",
            rule_order=2,
            target_field="field2",
            operator="equals",
            expected_value="value2",
        )
        assert rule1.rule_order < rule2.rule_order

    def test_policy_rule_non_blocking(self):
        """Should support non-blocking rules."""
        rule = PolicyRule(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            policy_id=uuid.uuid4(),
            rule_name="Warning Rule",
            rule_order=1,
            target_field="field",
            operator="equals",
            expected_value="value",
            is_blocking=False,
            severity="low",
        )
        assert rule.is_blocking is False
        assert rule.severity == "low"


class TestPolicyApplication:
    def test_create_policy_application(self):
        """Should create a policy application record."""
        application = PolicyApplication(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            policy_id=uuid.uuid4(),
            entity_type="formula",
            entity_id=uuid.uuid4(),
            entity_version="1.0.0",
            applied_at=datetime.now(UTC),
            applied_by="system",
            result="passed",
            rule_results=[{"rule_id": "1", "result": "passed"}],
            context={"test": True},
        )
        assert application.entity_type == "formula"
        assert application.result == "passed"
        assert application.rule_results is not None

    def test_policy_application_results(self):
        """Should support different result types."""
        for result in ["passed", "failed", "warning"]:
            application = PolicyApplication(
                id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                policy_id=uuid.uuid4(),
                entity_type="formula",
                entity_id=uuid.uuid4(),
                applied_at=datetime.now(UTC),
                applied_by="system",
                result=result,
            )
            assert application.result == result


class TestPolicyRelationships:
    def test_policy_has_versions(self):
        """Policy should have versions relationship."""
        policy = Policy(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Test Policy",
            slug="test-policy",
            policy_type=PolicyType.CUSTOM.value,
            current_version="1.0.0",
            latest_version="1.0.0",
            applies_to_entity_types=[],
            is_active=True,
        )
        assert hasattr(policy, "versions")

    def test_policy_has_rules(self):
        """Policy should have rules relationship."""
        policy = Policy(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Test Policy",
            slug="test-policy",
            policy_type=PolicyType.CUSTOM.value,
            current_version="1.0.0",
            latest_version="1.0.0",
            applies_to_entity_types=[],
            is_active=True,
        )
        assert hasattr(policy, "rules")

    def test_policy_has_applications(self):
        """Policy should have applications relationship."""
        policy = Policy(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Test Policy",
            slug="test-policy",
            policy_type=PolicyType.CUSTOM.value,
            current_version="1.0.0",
            latest_version="1.0.0",
            applies_to_entity_types=[],
            is_active=True,
        )
        assert hasattr(policy, "applications")

    def test_policy_version_has_policy(self):
        """PolicyVersion should have policy relationship."""
        version = PolicyVersion(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            policy_id=uuid.uuid4(),
            version="1.0.0",
            rules_engine_config={},
            effective_from=datetime.now(UTC),
        )
        assert hasattr(version, "policy")

    def test_policy_rule_has_policy(self):
        """PolicyRule should have policy relationship."""
        rule = PolicyRule(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            policy_id=uuid.uuid4(),
            rule_name="Test Rule",
            rule_order=1,
            target_field="field",
            operator="equals",
            expected_value="value",
        )
        assert hasattr(rule, "policy")

    def test_policy_application_has_policy(self):
        """PolicyApplication should have policy relationship."""
        application = PolicyApplication(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            policy_id=uuid.uuid4(),
            entity_type="formula",
            entity_id=uuid.uuid4(),
            applied_at=datetime.now(UTC),
            applied_by="system",
            result="passed",
        )
        assert hasattr(application, "policy")
