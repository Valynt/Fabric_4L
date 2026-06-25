"""Default benchmark pack loader.

Provides the ``load_default_benchmark_packs`` entry point used during Layer 6
service startup and a CLI shim referenced in ``pyproject.toml``.

Built-in industry benchmark seeds are loaded separately by
``layer6_benchmarks.api.main._init_seed_data``. This module is reserved for
additional pack-derived benchmark datasets when pack definitions include
benchmark contributions.
"""

from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from decimal import Decimal

from layer6_benchmarks.models.benchmark_dataset import (
    BenchmarkDataset,
    BenchmarkMetric,
    StatisticalProfile,
)
from layer6_benchmarks.models.valueos_contracts import ValueOSBenchmarkMetric
from layer6_benchmarks.repositories.benchmark_repository import BenchmarkRepository
from layer6_benchmarks.seed.valueos_default_pack import (
    VALUEOS_BASELINE_METRIC_TARGET,
    VALUEOS_REQUIRED_INDUSTRIES,
    build_valueos_default_metrics,
)

logger = logging.getLogger(__name__)


class BenchmarkPackValidationError(ValueError):
    """Raised when a benchmark pack fails governance validation."""


async def load_default_benchmark_packs(repo: BenchmarkRepository) -> None:
    """Load default benchmark packs into the repository.

    The canonical built-in benchmark datasets are seeded separately by
    ``_init_seed_data`` in ``api/main.py``. This loader adds the governed
    ValueOS GTBL baseline pack: 100 distribution-first metrics across the five
    required ValueOS industries.

    Args:
        repo: Benchmark repository instance.
    """
    metrics = build_valueos_default_metrics()
    validate_valueos_pack(metrics)
    datasets = valueos_metrics_to_datasets(metrics)
    for dataset in datasets:
        await repo.save_dataset(dataset)
    logger.info(
        "Loaded ValueOS benchmark pack with %d metrics across %d datasets",
        len(metrics),
        len(datasets),
    )


def validate_valueos_pack(metrics: list[ValueOSBenchmarkMetric]) -> None:
    """Validate pack-level ValueOS coverage and governance invariants."""
    if len(metrics) < VALUEOS_BASELINE_METRIC_TARGET:
        raise BenchmarkPackValidationError(
            f"ValueOS benchmark pack must include at least {VALUEOS_BASELINE_METRIC_TARGET} metrics"
        )

    by_industry: dict[str, int] = defaultdict(int)
    seen_metric_ids: set[str] = set()
    for metric in metrics:
        if metric.metric_id in seen_metric_ids:
            raise BenchmarkPackValidationError(f"Duplicate metric_id: {metric.metric_id}")
        seen_metric_ids.add(metric.metric_id)

        by_industry[metric.segmentation.industry] += 1
        if not metric.provenance:
            raise BenchmarkPackValidationError(f"{metric.metric_id} has no provenance")
        if metric.governance.status != "active":
            raise BenchmarkPackValidationError(f"{metric.metric_id} is not active")
        for source in metric.provenance:
            if source.license_class not in {
                "public",
                "internal",
                "licensed_restricted",
                "partner_anonymized",
            }:
                raise BenchmarkPackValidationError(
                    f"{metric.metric_id} has unsupported license class {source.license_class}"
                )

    missing_industries = [
        industry for industry in VALUEOS_REQUIRED_INDUSTRIES if by_industry.get(industry, 0) == 0
    ]
    if missing_industries:
        raise BenchmarkPackValidationError(
            "ValueOS benchmark pack missing required industries: "
            + ", ".join(sorted(missing_industries))
        )


def valueos_metrics_to_datasets(metrics: list[ValueOSBenchmarkMetric]) -> list[BenchmarkDataset]:
    """Flatten validated ValueOS metrics into current BenchmarkDataset storage."""
    grouped: dict[str, list[ValueOSBenchmarkMetric]] = defaultdict(list)
    for metric in metrics:
        grouped[metric.segmentation.industry].append(metric)

    datasets: list[BenchmarkDataset] = []
    for industry, industry_metrics in sorted(grouped.items()):
        dataset = BenchmarkDataset(
            dataset_id=f"valueos-{industry}-gtbl-2026q2",
            name=f"ValueOS {industry.replace('_', ' ').title()} GTBL 2026Q2",
            description=(
                "ValueOS distribution-first ground-truth benchmark library baseline "
                f"for {industry.replace('_', ' ')}."
            ),
            industry=industry,
            segment="enterprise",
            geography="global",
            version="1.0.0",
            data_source="ValueOS GTBL default pack 2026Q2",
            is_public=True,
            tenant_id="system",
            ownership_mode="global_system",
        )
        for valueos_metric in industry_metrics:
            dataset.add_metric(_to_benchmark_metric(valueos_metric))
        datasets.append(dataset)
    return datasets


def _to_benchmark_metric(metric: ValueOSBenchmarkMetric) -> BenchmarkMetric:
    distribution = metric.distribution
    primary_source = metric.provenance[0]
    return BenchmarkMetric(
        name=metric.metric_id,
        unit=metric.unit,
        description=metric.description,
        profile=StatisticalProfile(
            p10=distribution.p10,
            p25=distribution.p25,
            p50=distribution.p50,
            p75=distribution.p75,
            p90=distribution.p90,
            mean=distribution.mean,
            std_dev=distribution.std_dev or Decimal("0"),
            sample_size=distribution.sample_size,
        ),
        lower_bound=distribution.p10,
        upper_bound=distribution.p90,
        is_higher_better=metric.taxonomy.value_type
        in {"revenue_growth", "revenue_uplift"},
        display_name=metric.display_name,
        functional_domain=metric.taxonomy.functional_domain,
        category=metric.taxonomy.category,
        lifecycle_stage=metric.taxonomy.lifecycle_stage,
        value_type=metric.taxonomy.value_type,
        company_size_band=metric.segmentation.company_size_band,
        maturity_band=metric.segmentation.maturity_band,
        revenue_band=metric.segmentation.revenue_band,
        distribution_shape=distribution.shape,
        source_name=primary_source.source_name,
        source_type=primary_source.source_type,
        source_count=len(metric.provenance),
        source_publication_year=primary_source.publication_year,
        license_class=primary_source.license_class,
        confidence_score=float(primary_source.confidence_score),
        caveats=primary_source.caveats,
        vintage=metric.governance.vintage,
        governance_status=metric.governance.status,
        stale_after=metric.governance.stale_after.isoformat()
        if metric.governance.stale_after
        else None,
    )


def main() -> None:
    """Console entry point for ``layer6-load-benchmark-packs``.

    This is a thin wrapper around ``load_default_benchmark_packs`` suitable for
    local development and container init scripts. It does not initialize the
    full Neo4j driver; use the service lifespan for production startup.
    """
    parser = argparse.ArgumentParser(
        description="Load default benchmark packs into the Layer 6 repository."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the action without writing to the repository.",
    )
    args = parser.parse_args()

    if args.dry_run:
        metrics = build_valueos_default_metrics()
        validate_valueos_pack(metrics)
        print(
            "Dry run: ValueOS benchmark pack validates "
            f"{len(metrics)} metrics across {len(VALUEOS_REQUIRED_INDUSTRIES)} industries."
        )
        return

    print("Use service startup to load default benchmark packs with a configured repository.")


if __name__ == "__main__":
    main()
