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

from layer6_benchmarks.repositories.benchmark_repository import BenchmarkRepository

logger = logging.getLogger(__name__)


async def load_default_benchmark_packs(repo: BenchmarkRepository) -> None:
    """Load default benchmark packs into the repository.

    Currently a no-op placeholder. The canonical built-in benchmark datasets
    (manufacturing, SaaS B2B, healthcare, financial services) are seeded by
    ``_init_seed_data`` in ``api/main.py``. This function exists to satisfy the
    startup import contract and to be extended when pack-derived benchmark
    datasets are defined.

    Args:
        repo: Benchmark repository instance.
    """
    logger.debug("load_default_benchmark_packs is a no-op placeholder")


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
        print("Dry run: no benchmark packs would be loaded (placeholder).")
        return

    # Placeholder: real initialization requires a Neo4j driver and settings.
    print("No additional benchmark packs to load (placeholder).")


if __name__ == "__main__":
    main()
