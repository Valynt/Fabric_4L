"""Tests for the benchmark pack loader."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from layer6_benchmarks.seed.load_benchmark_packs import (
    default_benchmark_packs_dir,
    load_all_benchmark_packs,
    load_benchmark_pack,
)


@pytest.fixture
def valid_pack(tmp_path: Path) -> Path:
    """Write a minimal valid benchmark pack file."""
    data = {
        "dataset_id": "test-pack-1",
        "name": "Test Pack",
        "description": "A test pack",
        "industry": "software",
        "segment": "mid-market",
        "geography": "global",
        "version": "1.0.0",
        "data_source": "test",
        "is_public": True,
        "ownership_mode": "tenant",
        "metrics": {
            "se_hours_per_opportunity": {
                "name": "se_hours_per_opportunity",
                "unit": "hours",
                "description": "SE hours",
                "profile": {
                    "p10": "1.0",
                    "p25": "2.0",
                    "p50": "3.0",
                    "p75": "5.0",
                    "p90": "8.0",
                    "mean": "3.5",
                    "std_dev": "1.5",
                    "sample_size": 100,
                },
                "lower_bound": "0.5",
                "upper_bound": "20.0",
                "is_higher_better": False,
            }
        },
    }
    path = tmp_path / "test-pack-1.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class TestLoadBenchmarkPack:
    def test_loads_dataset_with_global_system_ownership(self, valid_pack: Path) -> None:
        dataset = load_benchmark_pack(valid_pack)
        assert dataset.dataset_id == "test-pack-1"
        assert dataset.tenant_id == "system"
        assert dataset.ownership_mode == "global_system"
        assert dataset.industry == "software"
        assert dataset.segment == "mid-market"

    def test_loads_metric_profile_and_bounds(self, valid_pack: Path) -> None:
        dataset = load_benchmark_pack(valid_pack)
        metric = dataset.get_metric("se_hours_per_opportunity")
        assert metric is not None
        assert metric.unit == "hours"
        assert metric.profile.p50 == Decimal("3.0")
        assert metric.profile.sample_size == 100
        assert metric.lower_bound == Decimal("0.5")
        assert metric.upper_bound == Decimal("20.0")
        assert metric.is_higher_better is False

    def test_ignores_pack_ownership_mode_and_forces_global_system(self, valid_pack: Path) -> None:
        dataset = load_benchmark_pack(valid_pack)
        assert dataset.ownership_mode == "global_system"

    def test_rejects_missing_dataset_fields(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"dataset_id": "x", "name": "x"}), encoding="utf-8")
        with pytest.raises(ValueError, match="missing dataset fields"):
            load_benchmark_pack(path)

    def test_rejects_missing_profile_fields(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        data = {
            "dataset_id": "x",
            "name": "x",
            "description": "x",
            "industry": "x",
            "metrics": {
                "m1": {
                    "unit": "hours",
                    "description": "m",
                    "profile": {"p10": "1", "p50": "2", "sample_size": 10},
                }
            },
        }
        path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="missing profile fields"):
            load_benchmark_pack(path)

    def test_rejects_non_positive_sample_size(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        data = {
            "dataset_id": "x",
            "name": "x",
            "description": "x",
            "industry": "x",
            "metrics": {
                "m1": {
                    "unit": "hours",
                    "description": "m",
                    "profile": {
                        "p10": "1",
                        "p25": "2",
                        "p50": "3",
                        "p75": "4",
                        "p90": "5",
                        "mean": "3",
                        "std_dev": "1",
                        "sample_size": 0,
                    },
                }
            },
        }
        path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="sample_size must be positive"):
            load_benchmark_pack(path)


class TestLoadAllBenchmarkPacks:
    @pytest.mark.asyncio
    async def test_loads_all_json_files_in_directory(self, tmp_path: Path) -> None:
        for name in ("a.json", "b.json"):
            data = {
                "dataset_id": f"pack-{name[:-5]}",
                "name": f"Pack {name}",
                "description": "x",
                "industry": "x",
                "metrics": {
                    "m1": {
                        "unit": "hours",
                        "description": "m",
                        "profile": {
                            "p10": "1",
                            "p25": "2",
                            "p50": "3",
                            "p75": "4",
                            "p90": "5",
                            "mean": "3",
                            "std_dev": "1",
                            "sample_size": 10,
                        },
                    }
                },
            }
            (tmp_path / name).write_text(json.dumps(data), encoding="utf-8")

        repo = AsyncMock()
        loaded = await load_all_benchmark_packs(repo, packs_dir=tmp_path)
        assert sorted(loaded) == ["pack-a", "pack-b"]
        assert repo.save_dataset.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_directory_missing(self) -> None:
        repo = AsyncMock()
        loaded = await load_all_benchmark_packs(repo, packs_dir="/does/not/exist")
        assert loaded == []
        repo.save_dataset.assert_not_called()

    def test_default_packs_dir_resolves_to_repo_packs_benchmarks(self) -> None:
        directory = default_benchmark_packs_dir()
        assert directory.name == "benchmarks"
        assert (directory / "saas-se-efficiency-2025.json").is_file()


class TestPackLoaderIntegration:
    def test_real_pack_is_parseable(self) -> None:
        pack_path = default_benchmark_packs_dir() / "saas-se-efficiency-2025.json"
        dataset = load_benchmark_pack(pack_path)
        assert dataset.dataset_id == "saas-se-efficiency-2025"
        assert dataset.ownership_mode == "global_system"
        assert "se_hours_per_opportunity" in dataset.metrics
        assert dataset.metrics["se_hours_per_opportunity"].profile.sample_size > 0
