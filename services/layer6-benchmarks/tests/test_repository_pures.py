"""Unit tests for pure functions in the benchmark repository."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from value_fabric.layer6.models.benchmark_dataset import (
    BenchmarkDataset,
    BenchmarkMetric,
    StatisticalProfile,
)
from value_fabric.layer6.repositories.benchmark_repository import (
    _metric_to_dict,
    _node_to_dataset,
)


class TestMetricToDict:
    def test_serializes_decimals(self) -> None:
        metric = BenchmarkMetric(
            name="m1",
            unit="percent",
            description="desc",
            profile=StatisticalProfile(
                p10=Decimal("1.1"),
                p25=Decimal("2.2"),
                p50=Decimal("3.3"),
                p75=Decimal("4.4"),
                p90=Decimal("5.5"),
                mean=Decimal("3.0"),
                std_dev=Decimal("1.0"),
                sample_size=100,
            ),
            lower_bound=Decimal("0.0"),
            upper_bound=Decimal("100.0"),
            is_higher_better=True,
        )
        d = _metric_to_dict(metric)
        assert d["name"] == "m1"
        assert d["lower_bound"] == "0.0"
        assert d["upper_bound"] == "100.0"
        assert d["p10"] == "1.1"
        assert d["mean"] == "3.0"
        assert d["sample_size"] == 100

    def test_handles_none_bounds(self) -> None:
        metric = BenchmarkMetric(
            name="m1",
            unit="percent",
            description="desc",
            profile=StatisticalProfile(
                p10=Decimal("1"),
                p25=Decimal("2"),
                p50=Decimal("3"),
                p75=Decimal("4"),
                p90=Decimal("5"),
                mean=Decimal("3"),
                std_dev=Decimal("1"),
                sample_size=10,
            ),
            lower_bound=None,
            upper_bound=None,
        )
        d = _metric_to_dict(metric)
        assert d["lower_bound"] is None
        assert d["upper_bound"] is None


class TestNodeToDataset:
    def _make_node(self, **kwargs):
        defaults = {
            "dataset_id": "ds1",
            "name": "Dataset One",
            "description": "desc",
            "industry": "test",
            "segment": "enterprise",
            "geography": "global",
            "version": "1.0.0",
            "data_source": "test",
            "is_public": False,
            "tenant_id": "tenant-1",
            "ownership_mode": "tenant",
        }
        defaults.update(kwargs)
        return defaults

    def _make_metric_node(self, **kwargs):
        defaults = {
            "name": "m1",
            "unit": "percent",
            "description": "metric one",
            "p10": "1.0",
            "p25": "2.0",
            "p50": "3.0",
            "p75": "4.0",
            "p90": "5.0",
            "mean": "3.0",
            "std_dev": "1.0",
            "sample_size": 100,
            "lower_bound": "0.0",
            "upper_bound": "100.0",
            "is_higher_better": True,
        }
        defaults.update(kwargs)
        return defaults

    def test_reconstructs_from_mock_nodes(self) -> None:
        node = self._make_node()
        m_node = self._make_metric_node()
        dataset = _node_to_dataset(node, [m_node])
        assert dataset.dataset_id == "ds1"
        assert dataset.name == "Dataset One"
        assert len(dataset.metrics) == 1
        assert "m1" in dataset.metrics
        metric = dataset.metrics["m1"]
        assert metric.name == "m1"
        assert metric.profile.mean == Decimal("3.0")

    def test_skips_none_metric_nodes(self) -> None:
        node = self._make_node()
        dataset = _node_to_dataset(node, [None, self._make_metric_node(), None])
        assert len(dataset.metrics) == 1

    def test_parses_dates(self) -> None:
        created = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        updated = datetime(2024, 6, 20, 14, 0, 0, tzinfo=timezone.utc)
        node = self._make_node(
            created_at=created.isoformat(),
            updated_at=updated.isoformat(),
        )
        dataset = _node_to_dataset(node, [])
        assert dataset.created_at == created
        assert dataset.updated_at == updated
