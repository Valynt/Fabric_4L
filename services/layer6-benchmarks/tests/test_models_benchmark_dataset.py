"""Unit tests for benchmark dataset models."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from layer6_benchmarks.models.benchmark_dataset import (
    FINANCIAL_SERVICES_BENCHMARK_SEED,
    HEALTHCARE_BENCHMARK_SEED,
    MANUFACTURING_BENCHMARK_SEED,
    SAAS_B2B_BENCHMARK_SEED,
    BenchmarkDataset,
    BenchmarkMetric,
    StatisticalProfile,
)


class TestStatisticalProfile:
    def test_to_dict_serializes_decimals_as_strings(self) -> None:
        profile = StatisticalProfile(
            p10=Decimal("1.1"),
            p25=Decimal("2.2"),
            p50=Decimal("3.3"),
            p75=Decimal("4.4"),
            p90=Decimal("5.5"),
            mean=Decimal("3.0"),
            std_dev=Decimal("1.0"),
            sample_size=100,
        )
        d = profile.to_dict()
        assert d["p10"] == "1.1"
        assert d["p25"] == "2.2"
        assert d["mean"] == "3.0"
        assert d["sample_size"] == 100

    def test_from_dict_reconstructs_profile(self) -> None:
        data = {
            "p10": "1.1",
            "p25": "2.2",
            "p50": "3.3",
            "p75": "4.4",
            "p90": "5.5",
            "mean": "3.0",
            "std_dev": "1.0",
            "sample_size": 100,
        }
        profile = StatisticalProfile.from_dict(data)
        assert profile.p10 == Decimal("1.1")
        assert profile.sample_size == 100

    def test_from_dict_rejects_invalid_decimal(self) -> None:
        data = {
            "p10": "not_a_number",
            "p25": "2.2",
            "p50": "3.3",
            "p75": "4.4",
            "p90": "5.5",
            "mean": "3.0",
            "std_dev": "1.0",
            "sample_size": 100,
        }
        with pytest.raises(Exception):
            StatisticalProfile.from_dict(data)

    def test_roundtrip_preserves_values(self) -> None:
        original = StatisticalProfile(
            p10=Decimal("10.5"),
            p25=Decimal("25.5"),
            p50=Decimal("50.0"),
            p75=Decimal("75.5"),
            p90=Decimal("90.0"),
            mean=Decimal("55.0"),
            std_dev=Decimal("15.0"),
            sample_size=500,
        )
        restored = StatisticalProfile.from_dict(original.to_dict())
        assert original == restored


class TestBenchmarkDataset:
    def test_get_metric_returns_existing_metric(self) -> None:
        dataset = BenchmarkDataset(
            dataset_id="test",
            name="Test",
            description="desc",
            industry="test",
            segment=None,
            geography=None,
        )
        metric = BenchmarkMetric(
            name="m1",
            unit="percent",
            description="metric one",
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
        )
        dataset.add_metric(metric)
        assert dataset.get_metric("m1") is metric

    def test_get_metric_returns_none_for_missing(self) -> None:
        dataset = BenchmarkDataset(
            dataset_id="test",
            name="Test",
            description="desc",
            industry="test",
            segment=None,
            geography=None,
        )
        assert dataset.get_metric("missing") is None

    def test_add_metric_stores_and_updates_timestamp(self) -> None:
        dataset = BenchmarkDataset(
            dataset_id="test",
            name="Test",
            description="desc",
            industry="test",
            segment=None,
            geography=None,
        )
        before = datetime.now(timezone.utc)
        metric = BenchmarkMetric(
            name="m1",
            unit="percent",
            description="metric one",
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
        )
        dataset.add_metric(metric)
        after = datetime.now(timezone.utc)
        assert dataset.metrics["m1"] is metric
        assert dataset.updated_at is not None
        assert before <= dataset.updated_at <= after

    def test_add_metric_overwrites_existing(self) -> None:
        dataset = BenchmarkDataset(
            dataset_id="test",
            name="Test",
            description="desc",
            industry="test",
            segment=None,
            geography=None,
        )
        m1 = BenchmarkMetric(
            name="m1",
            unit="percent",
            description="first",
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
        )
        m2 = BenchmarkMetric(
            name="m1",
            unit="percent",
            description="second",
            profile=StatisticalProfile(
                p10=Decimal("10"),
                p25=Decimal("20"),
                p50=Decimal("30"),
                p75=Decimal("40"),
                p90=Decimal("50"),
                mean=Decimal("30"),
                std_dev=Decimal("10"),
                sample_size=100,
            ),
        )
        dataset.add_metric(m1)
        dataset.add_metric(m2)
        assert dataset.metrics["m1"].description == "second"


class TestSeedDataIntegrity:
    @pytest.mark.parametrize(
        "seed",
        [
            MANUFACTURING_BENCHMARK_SEED,
            SAAS_B2B_BENCHMARK_SEED,
            HEALTHCARE_BENCHMARK_SEED,
            FINANCIAL_SERVICES_BENCHMARK_SEED,
        ],
    )
    def test_seed_has_required_fields(self, seed: dict) -> None:
        assert "dataset_id" in seed
        assert "name" in seed
        assert "industry" in seed
        assert "metrics" in seed
        assert isinstance(seed["metrics"], dict)
        assert len(seed["metrics"]) > 0

    @pytest.mark.parametrize(
        "seed",
        [
            MANUFACTURING_BENCHMARK_SEED,
            SAAS_B2B_BENCHMARK_SEED,
            HEALTHCARE_BENCHMARK_SEED,
            FINANCIAL_SERVICES_BENCHMARK_SEED,
        ],
    )
    def test_seed_metrics_have_valid_profiles(self, seed: dict) -> None:
        for metric_name, metric in seed["metrics"].items():
            profile = metric["profile"]
            required_keys = {"p10", "p25", "p50", "p75", "p90", "mean", "std_dev", "sample_size"}
            assert required_keys.issubset(profile.keys()), f"{metric_name} missing profile keys"
            assert profile["sample_size"] > 0

    def test_all_seed_profiles_have_positive_sample_size(self) -> None:
        for seed in [
            MANUFACTURING_BENCHMARK_SEED,
            SAAS_B2B_BENCHMARK_SEED,
            HEALTHCARE_BENCHMARK_SEED,
            FINANCIAL_SERVICES_BENCHMARK_SEED,
        ]:
            for metric in seed["metrics"].values():
                assert metric["profile"]["sample_size"] > 0
