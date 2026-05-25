"""
Unit tests for Benchmark Governance models.

Tests for BenchmarkDataset, BenchmarkVersion, and BenchmarkScope models.
"""

import uuid
from datetime import UTC, datetime

import pytest

from layer5_ground_truth.models.benchmark_governance import (
    BenchmarkDataset,
    BenchmarkScope,
    BenchmarkStatus,
    BenchmarkType,
    BenchmarkVersion,
)


class TestBenchmarkDataset:
    def test_create_benchmark_dataset(self):
        """Should create a benchmark dataset with required fields."""
        benchmark = BenchmarkDataset(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Industry ROI Benchmarks",
            slug="industry-roi-benchmarks",
            benchmark_type=BenchmarkType.INDUSTRY_STANDARD.value,
            description="Industry-standard ROI benchmarks",
            current_version="1.0.0",
            latest_version="1.0.0",
            source_name="Gartner",
            source_type="research",
            confidence_level="high",
            is_active=True,
        )
        assert benchmark.slug == "industry-roi-benchmarks"
        assert benchmark.benchmark_type == BenchmarkType.INDUSTRY_STANDARD.value
        assert benchmark.confidence_level == "high"

    def test_benchmark_type_enum_values(self):
        """BenchmarkType enum should have expected values."""
        assert {s.value for s in BenchmarkType} == {
            "industry_standard",
            "competitive",
            "historical",
            "customer_reference",
            "internal",
            "third_party",
        }

    def test_benchmark_source_metadata(self):
        """Should track complete source metadata."""
        benchmark = BenchmarkDataset(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Competitive Analysis",
            slug="competitive-analysis",
            benchmark_type=BenchmarkType.COMPETITIVE.value,
            current_version="1.0.0",
            latest_version="1.0.0",
            source_name="Competitor Reports",
            source_url="https://example.com/reports",
            source_type="external",
            source_date=datetime(2025, 1, 1, tzinfo=UTC),
            collection_methodology="Survey of 500 companies",
            confidence_level="medium",
            sample_size=500,
            margin_of_error={"value": 0.05, "confidence": 0.95},
            data_quality_notes="Self-reported data",
        )
        assert benchmark.source_url is not None
        assert benchmark.sample_size == 500
        assert benchmark.margin_of_error is not None


class TestBenchmarkVersion:
    def test_create_benchmark_version(self):
        """Should create a benchmark version with required fields."""
        version = BenchmarkVersion(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            benchmark_id=uuid.uuid4(),
            version="1.0.0",
            data={"average_roi": 3.5, "median_roi": 2.8},
            data_schema={"type": "object"},
            effective_from=datetime.now(UTC),
            status=BenchmarkStatus.DRAFT.value,
        )
        assert version.version == "1.0.0"
        assert version.data is not None
        assert version.status == BenchmarkStatus.DRAFT.value

    def test_benchmark_status_enum_values(self):
        """BenchmarkStatus enum should have expected values."""
        assert {s.value for s in BenchmarkStatus} == {
            "draft",
            "pending_approval",
            "approved",
            "deprecated",
            "archived",
        }

    def test_benchmark_version_effective_dates(self):
        """Should support effective date ranges."""
        effective_from = datetime(2025, 1, 1, tzinfo=UTC)
        effective_until = datetime(2025, 12, 31, tzinfo=UTC)
        version = BenchmarkVersion(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            benchmark_id=uuid.uuid4(),
            version="1.0.0",
            data={},
            data_schema={},
            effective_from=effective_from,
            effective_until=effective_until,
            status=BenchmarkStatus.APPROVED.value,
        )
        assert version.effective_from == effective_from
        assert version.effective_until == effective_until

    def test_benchmark_version_approval(self):
        """Should track approval information."""
        version = BenchmarkVersion(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            benchmark_id=uuid.uuid4(),
            version="1.0.0",
            data={},
            data_schema={},
            effective_from=datetime.now(UTC),
            status=BenchmarkStatus.APPROVED.value,
            approved_by="approver@example.com",
            approved_at=datetime.now(UTC),
        )
        assert version.status == BenchmarkStatus.APPROVED.value
        assert version.approved_by == "approver@example.com"


class TestBenchmarkScope:
    def test_create_benchmark_scope(self):
        """Should create a benchmark scope with required fields."""
        scope = BenchmarkScope(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            benchmark_id=uuid.uuid4(),
            scope_type="industry",
            scope_value="technology",
            description="Technology industry benchmarks",
        )
        assert scope.scope_type == "industry"
        assert scope.scope_value == "technology"

    def test_benchmark_scope_types(self):
        """Should support different scope types."""
        scopes = [
            ("global", "all"),
            ("industry", "technology"),
            ("region", "north_america"),
            ("segment", "enterprise"),
            ("account", "acme-corp"),
        ]
        for scope_type, scope_value in scopes:
            scope = BenchmarkScope(
                id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                benchmark_id=uuid.uuid4(),
                scope_type=scope_type,
                scope_value=scope_value,
            )
            assert scope.scope_type == scope_type
            assert scope.scope_value == scope_value


class TestBenchmarkRelationships:
    def test_benchmark_has_versions(self):
        """BenchmarkDataset should have versions relationship."""
        benchmark = BenchmarkDataset(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Test Benchmark",
            slug="test-benchmark",
            benchmark_type=BenchmarkType.CUSTOM.value,
            current_version="1.0.0",
            latest_version="1.0.0",
            source_name="Test",
            source_type="internal",
            confidence_level="medium",
        )
        assert hasattr(benchmark, "versions")

    def test_benchmark_has_scopes(self):
        """BenchmarkDataset should have scopes relationship."""
        benchmark = BenchmarkDataset(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Test Benchmark",
            slug="test-benchmark",
            benchmark_type=BenchmarkType.CUSTOM.value,
            current_version="1.0.0",
            latest_version="1.0.0",
            source_name="Test",
            source_type="internal",
            confidence_level="medium",
        )
        assert hasattr(benchmark, "scopes")

    def test_benchmark_version_has_benchmark(self):
        """BenchmarkVersion should have benchmark relationship."""
        version = BenchmarkVersion(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            benchmark_id=uuid.uuid4(),
            version="1.0.0",
            data={},
            data_schema={},
            effective_from=datetime.now(UTC),
        )
        assert hasattr(version, "benchmark")

    def test_benchmark_scope_has_benchmark(self):
        """BenchmarkScope should have benchmark relationship."""
        scope = BenchmarkScope(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            benchmark_id=uuid.uuid4(),
            scope_type="industry",
            scope_value="technology",
        )
        assert hasattr(scope, "benchmark")
