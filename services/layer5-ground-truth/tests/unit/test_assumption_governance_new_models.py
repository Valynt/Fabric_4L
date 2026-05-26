"""
Unit tests for Assumption Governance models (new implementation).

Tests for Assumption, AssumptionEvidence, and AssumptionReview models.
"""

import uuid
from datetime import UTC, datetime

import pytest

from layer5_ground_truth.models.assumption_registry import (
    Assumption,
    AssumptionEvidence,
    AssumptionImpact,
    AssumptionReview,
    AssumptionStatus,
    AssumptionType,
)


class TestAssumption:
    def test_create_assumption(self):
        """Should create an assumption with required fields."""
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Market Growth Rate",
            slug="market-growth-rate",
            assumption_type=AssumptionType.MARKET_GROWTH.value,
            description="Annual market growth rate assumption",
            value={"rate": 0.15},
            value_type="percentage",
            impact_level=AssumptionImpact.HIGH.value,
            status=AssumptionStatus.DRAFT.value,
            is_active=True,
        )
        assert assumption.slug == "market-growth-rate"
        assert assumption.assumption_type == AssumptionType.MARKET_GROWTH.value
        assert assumption.impact_level == AssumptionImpact.HIGH.value

    def test_assumption_type_enum_values(self):
        """AssumptionType enum should have expected values."""
        assert {s.value for s in AssumptionType} == {
            "market_growth",
            "pricing",
            "cost_structure",
            "timeline",
            "resource_availability",
            "competitive_response",
            "customer_behavior",
            "technical_feasibility",
            "regulatory",
            "custom",
        }

    def test_assumption_impact_enum_values(self):
        """AssumptionImpact enum should have expected values."""
        assert {s.value for s in AssumptionImpact} == {
            "low",
            "medium",
            "high",
            "critical",
        }

    def test_assumption_status_enum_values(self):
        """AssumptionStatus enum should have expected values."""
        assert {s.value for s in AssumptionStatus} == {
            "draft",
            "pending_approval",
            "approved",
            "rejected",
            "deprecated",
            "archived",
        }

    def test_assumption_sensitivity_analysis(self):
        """Should support sensitivity analysis."""
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Pricing Assumption",
            slug="pricing-assumption",
            assumption_type=AssumptionType.PRICING.value,
            description="Pricing assumption with sensitivity",
            value={"price": 100},
            value_type="currency",
            impact_level=AssumptionImpact.HIGH.value,
            sensitivity_analysis={
                "base_case": 100,
                "optimistic": 120,
                "pessimistic": 80,
                "impact_on_roi": {"high": 0.5, "low": -0.3},
            },
        )
        assert assumption.sensitivity_analysis is not None
        assert "base_case" in assumption.sensitivity_analysis

    def test_assumption_truth_object_linkage(self):
        """Should link to TruthObject for evidence."""
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Cost Assumption",
            slug="cost-assumption",
            assumption_type=AssumptionType.COST_STRUCTURE.value,
            description="Cost structure assumption",
            value={"cost": 50000},
            value_type="currency",
            impact_level=AssumptionImpact.MEDIUM.value,
            truth_object_id=uuid.uuid4(),
            evidence_count=3,
        )
        assert assumption.truth_object_id is not None
        assert assumption.evidence_count == 3

    def test_assumption_approval_integration(self):
        """Should integrate with approval workflow."""
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Critical Assumption",
            slug="critical-assumption",
            assumption_type=AssumptionType.CUSTOM.value,
            description="Critical assumption requiring approval",
            value={"value": 100},
            value_type="number",
            impact_level=AssumptionImpact.CRITICAL.value,
            status=AssumptionStatus.APPROVED.value,
            approval_request_id=uuid.uuid4(),
            approved_by="approver@example.com",
            approved_at=datetime.now(UTC),
        )
        assert assumption.status == AssumptionStatus.APPROVED.value
        assert assumption.approval_request_id is not None
        assert assumption.approved_by == "approver@example.com"

    def test_assumption_context_links(self):
        """Should link to opportunity and formula."""
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Timeline Assumption",
            slug="timeline-assumption",
            assumption_type=AssumptionType.TIMELINE.value,
            description="Timeline assumption",
            value={"months": 6},
            value_type="duration",
            impact_level=AssumptionImpact.MEDIUM.value,
            applies_to_opportunity_id=uuid.uuid4(),
            applies_to_formula_id=uuid.uuid4(),
        )
        assert assumption.applies_to_opportunity_id is not None
        assert assumption.applies_to_formula_id is not None


class TestAssumptionEvidence:
    def test_create_assumption_evidence(self):
        """Should create assumption evidence with required fields."""
        evidence = AssumptionEvidence(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            assumption_id=uuid.uuid4(),
            evidence_type="truth_object",
            truth_object_id=uuid.uuid4(),
            confidence="high",
            relevance="high",
        )
        assert evidence.evidence_type == "truth_object"
        assert evidence.truth_object_id is not None
        assert evidence.confidence == "high"

    def test_assumption_evidence_external_source(self):
        """Should support external source evidence."""
        evidence = AssumptionEvidence(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            assumption_id=uuid.uuid4(),
            evidence_type="external_source",
            source_url="https://example.com/report",
            source_title="Industry Report 2025",
            excerpt="Market growth is expected to be 15%",
            confidence="medium",
            relevance="high",
        )
        assert evidence.source_url is not None
        assert evidence.source_title is not None
        assert evidence.excerpt is not None

    def test_assumption_evidence_quality_ratings(self):
        """Should support confidence and relevance ratings."""
        for confidence in ["high", "medium", "low"]:
            for relevance in ["high", "medium", "low"]:
                evidence = AssumptionEvidence(
                    id=uuid.uuid4(),
                    tenant_id=uuid.uuid4(),
                    assumption_id=uuid.uuid4(),
                    evidence_type="truth_object",
                    confidence=confidence,
                    relevance=relevance,
                )
                assert evidence.confidence == confidence
                assert evidence.relevance == relevance


class TestAssumptionReview:
    def test_create_assumption_review(self):
        """Should create an assumption review with required fields."""
        review = AssumptionReview(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            assumption_id=uuid.uuid4(),
            review_type="approval",
            reviewed_by="reviewer@example.com",
            reviewed_at=datetime.now(UTC),
            decision="approve",
            review_notes="Assumption is well-supported by evidence",
        )
        assert review.review_type == "approval"
        assert review.decision == "approve"
        assert review.reviewed_by == "reviewer@example.com"

    def test_assumption_review_decision_types(self):
        """Should support different decision types."""
        for decision in ["approve", "reject", "request_changes"]:
            review = AssumptionReview(
                id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                assumption_id=uuid.uuid4(),
                review_type="approval",
                reviewed_by="reviewer@example.com",
                decision=decision,
            )
            assert review.decision == decision

    def test_assumption_review_status_tracking(self):
        """Should track status changes."""
        review = AssumptionReview(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            assumption_id=uuid.uuid4(),
            review_type="approval",
            reviewed_by="reviewer@example.com",
            decision="approve",
            previous_status=AssumptionStatus.PENDING_APPROVAL.value,
            new_status=AssumptionStatus.APPROVED.value,
        )
        assert review.previous_status == AssumptionStatus.PENDING_APPROVAL.value
        assert review.new_status == AssumptionStatus.APPROVED.value


class TestAssumptionRelationships:
    def test_assumption_has_evidence(self):
        """Assumption should have evidence relationship."""
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Test Assumption",
            slug="test-assumption",
            assumption_type=AssumptionType.CUSTOM.value,
            description="Test assumption",
            value={"value": 1},
            value_type="number",
            impact_level=AssumptionImpact.LOW.value,
        )
        assert hasattr(assumption, "evidence")

    def test_assumption_has_reviews(self):
        """Assumption should have reviews relationship."""
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Test Assumption",
            slug="test-assumption",
            assumption_type=AssumptionType.CUSTOM.value,
            description="Test assumption",
            value={"value": 1},
            value_type="number",
            impact_level=AssumptionImpact.LOW.value,
        )
        assert hasattr(assumption, "reviews")

    def test_assumption_evidence_has_assumption(self):
        """AssumptionEvidence should have assumption relationship."""
        evidence = AssumptionEvidence(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            assumption_id=uuid.uuid4(),
            evidence_type="truth_object",
            confidence="medium",
            relevance="medium",
        )
        assert hasattr(evidence, "assumption")

    def test_assumption_review_has_assumption(self):
        """AssumptionReview should have assumption relationship."""
        review = AssumptionReview(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            assumption_id=uuid.uuid4(),
            review_type="approval",
            reviewed_by="reviewer@example.com",
        )
        assert hasattr(review, "assumption")
