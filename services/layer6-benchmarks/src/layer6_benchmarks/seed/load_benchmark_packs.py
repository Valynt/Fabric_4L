"""Load benchmark packs from JSON files into the Layer 6 Neo4j store.

Packs live under ``packs/benchmarks/`` in the repository root. They are
upserted with ``tenant_id="system"`` and ``ownership_mode="global_system"``
so that every tenant can read them but only a privileged admin can mutate
baseline packs.

Usage as a module (startup hook):

    from layer6_benchmarks.seed.load_benchmark_packs import load_default_benchmark_packs
    await load_default_benchmark_packs(repo)

Usage as an admin CLI:

    python -m layer6_benchmarks.seed.load_benchmark_packs
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Any

from layer6_benchmarks.models.benchmark_dataset import (
    BenchmarkDataset,
    BenchmarkMetric,
    StatisticalProfile,
)
from layer6_benchmarks.repositories.benchmark_repository import BenchmarkRepository

logger = logging.getLogger(__name__)

REQUIRED_DATASET_FIELDS = {"dataset_id", "name", "description", "industry", "metrics"}
REQUIRED_PROFILE_FIELDS = {"p10", "p25", "p50", "p75", "p90", "mean", "std_dev", "sample_size"}


def default_benchmark_packs_dir() -> Path:
    """Return the canonical ``packs/benchmarks`` directory under the repo root.

    Walks up from this module until it finds a directory containing
    ``packs/benchmarks``.
    """
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        candidate = parent / "packs" / "benchmarks"
        if candidate.is_dir():
            return candidate
    # Fallback: assume the standard repo layout from this file's location.
    return current.parents[4] / "packs" / "benchmarks"


def _validate_pack(data: dict[str, Any], source: Path) -> None:
    """Fail fast if a pack file is missing required structure."""
    missing = REQUIRED_DATASET_FIELDS - set(data.keys())
    if missing:
        raise ValueError(f"{source}: missing dataset fields {sorted(missing)}")

    if not isinstance(data["metrics"], dict) or not data["metrics"]:
        raise ValueError(f"{source}: metrics must be a non-empty object")

    for metric_name, metric in data["metrics"].items():
        if not isinstance(metric, dict):
            raise ValueError(f"{source}: metric {metric_name} must be an object")
        profile = metric.get("profile")
        if not isinstance(profile, dict):
            raise ValueError(f"{source}: metric {metric_name} missing profile")
        missing_profile = REQUIRED_PROFILE_FIELDS - set(profile.keys())
        if missing_profile:
            raise ValueError(
                f"{source}: metric {metric_name} missing profile fields {sorted(missing_profile)}"
            )
        if int(profile["sample_size"]) <= 0:
            raise ValueError(
                f"{source}: metric {metric_name} sample_size must be positive"
            )


def load_benchmark_pack(path: str | Path) -> BenchmarkDataset:
    """Parse a single benchmark pack file and return a ``BenchmarkDataset``.

    The returned dataset is always configured as a global system baseline,
    regardless of any ``ownership_mode`` value in the source file.
    """
    source = Path(path)
    with source.open("r", encoding="utf-8") as f:
        data = json.load(f)

    _validate_pack(data, source)

    dataset = BenchmarkDataset(
        dataset_id=data["dataset_id"],
        name=data["name"],
        description=data["description"],
        industry=data["industry"],
        segment=data.get("segment"),
        geography=data.get("geography"),
        version=data.get("version", "1.0.0"),
        data_source=data.get("data_source"),
        is_public=data.get("is_public", True),
        tenant_id="system",
        ownership_mode="global_system",
    )

    for metric_name, metric_data in data["metrics"].items():
        profile = StatisticalProfile.from_dict(metric_data["profile"])
        metric = BenchmarkMetric(
            name=metric_data.get("name", metric_name),
            unit=metric_data["unit"],
            description=metric_data["description"],
            profile=profile,
            lower_bound=(
                Decimal(metric_data["lower_bound"])
                if "lower_bound" in metric_data
                else None
            ),
            upper_bound=(
                Decimal(metric_data["upper_bound"])
                if "upper_bound" in metric_data
                else None
            ),
            is_higher_better=metric_data.get("is_higher_better", True),
        )
        dataset.add_metric(metric)

    return dataset


async def upsert_benchmark_pack(repo: BenchmarkRepository, path: str | Path) -> str:
    """Load a single pack file and persist it through ``repo``.

    Returns the loaded ``dataset_id``.
    """
    dataset = load_benchmark_pack(path)
    await repo.save_dataset(dataset)
    logger.info("Upserted benchmark pack %s from %s", dataset.dataset_id, path)
    return dataset.dataset_id


async def load_all_benchmark_packs(
    repo: BenchmarkRepository,
    packs_dir: str | Path | None = None,
) -> list[str]:
    """Load every ``*.json`` pack file in ``packs_dir``.

    Returns the list of upserted ``dataset_id`` values.
    """
    directory = Path(packs_dir) if packs_dir is not None else default_benchmark_packs_dir()

    if not directory.is_dir():
        logger.warning("Benchmark packs directory not found: %s", directory)
        return []

    loaded: list[str] = []
    for pack_file in sorted(directory.glob("*.json")):
        try:
            dataset_id = await upsert_benchmark_pack(repo, pack_file)
            loaded.append(dataset_id)
        except Exception:
            logger.exception("Failed to load benchmark pack %s", pack_file)
            raise

    logger.info("Loaded %d benchmark pack(s) from %s", len(loaded), directory)
    return loaded


async def load_default_benchmark_packs(repo: BenchmarkRepository) -> list[str]:
    """Convenience helper used by the service startup lifespan."""
    return await load_all_benchmark_packs(repo)


def main() -> int:
    """Synchronous entry point for the admin CLI."""
    return asyncio.run(_cli_main())


async def _cli_main() -> int:
    parser = argparse.ArgumentParser(
        description="Load benchmark packs as global system datasets."
    )
    parser.add_argument(
        "--packs-dir",
        type=Path,
        default=None,
        help="Directory containing benchmark pack JSON files "
             "(defaults to packs/benchmarks under the repo root).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse packs and print dataset IDs without writing to Neo4j.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.dry_run:
        directory = args.packs_dir or default_benchmark_packs_dir()
        for pack_file in sorted(directory.glob("*.json")):
            dataset = load_benchmark_pack(pack_file)
            print(f"{pack_file.name} -> {dataset.dataset_id} ({len(dataset.metrics)} metrics)")
        return 0

    from layer6_benchmarks.database import close_driver, get_driver

    driver = await get_driver()
    try:
        repo = BenchmarkRepository(driver)
        loaded = await load_all_benchmark_packs(repo, packs_dir=args.packs_dir)
        print(f"Loaded {len(loaded)} benchmark pack(s): {', '.join(loaded)}")
        return 0
    finally:
        await close_driver()


if __name__ == "__main__":
    raise SystemExit(main())
