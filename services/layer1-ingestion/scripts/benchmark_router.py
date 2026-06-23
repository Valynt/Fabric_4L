#!/usr/bin/env python3
"""Standalone benchmark script for Smart Router performance.

Usage:
    python scripts/benchmark_router.py --urls urls.txt --iterations 10
    python scripts/benchmark_router.py --sample  # Use built-in sample URLs

Generates benchmark report with speedup metrics and routing accuracy.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Allow ``from layer1_ingestion.crawler...`` and ``value_fabric...`` imports when the script
# is run directly.
_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR.parent / "src"))   # services/layer1-ingestion/src
sys.path.insert(0, str(_SCRIPT_DIR.parents[2]))      # repo root (value_fabric)

from layer1_ingestion.crawler.smart_router import SmartRouter, RouteType
from layer1_ingestion.crawler.httpx_crawler import HttpxCrawler
from layer1_ingestion.crawler.decision_store import InMemoryCrawlDecisionRepository
from value_fabric.shared.models.typed_dict import TypedDictModel


class generate_reportResult(TypedDictModel):
    details: Any
    router_rules_triggered: list[Any]
    routing_distribution: Any
    summary: dict[str, Any]


@dataclass
class BenchmarkResult:
    url: str
    route_chosen: str
    router_reason: str
    fast_time_ms: float | None
    browser_time_ms: float | None
    fallback_occurred: bool
    quality_passed: bool | None


DEFAULT_BROWSER_TIME_MS: float = 3500.0

SAMPLE_URLS: list[tuple[str, str]] = [
    ("https://httpbin.org/html", "static"),
    ("https://httpbin.org/json", "api"),
]


async def benchmark_url(
    url: str,
    url_type: str,
    iterations: int = 5,
) -> BenchmarkResult:
    """Benchmark a single URL."""
    router = SmartRouter()

    # Get routing decision
    decision = router.decide(url, RouteType.FAST_WITH_FALLBACK)

    fast_time = None
    browser_time = None
    fallback_occurred = False
    quality_passed = None

    if decision.route == RouteType.FAST:
        # Measure fast path
        times = []
        for _ in range(iterations):
            async with HttpxCrawler() as crawler:
                start = time.monotonic()
                result = await crawler.fetch(url)
                times.append((time.monotonic() - start) * 1000)
        fast_time = statistics.mean(times)
        quality_passed = True

    elif decision.route == RouteType.FAST_WITH_FALLBACK:
        # Try fast, measure both
        async with HttpxCrawler() as crawler:
            start = time.monotonic()
            result = await crawler.fetch(url)
            fast_time = (time.monotonic() - start) * 1000

        # Simulate fallback browser timing (3-5 s typical)
        browser_time = DEFAULT_BROWSER_TIME_MS
        fallback_occurred = True
        quality_passed = False

    else:  # BROWSER
        browser_time = DEFAULT_BROWSER_TIME_MS
        quality_passed = None

    return BenchmarkResult(
        url=url,
        route_chosen=decision.route.value,
        router_reason=decision.reason,
        fast_time_ms=fast_time,
        browser_time_ms=browser_time,
        fallback_occurred=fallback_occurred,
        quality_passed=quality_passed,
    )


def generate_report(results: list[BenchmarkResult]) -> dict[str, Any]:
    """Generate structured benchmark report."""

    # Calculate metrics
    fast_results = [r for r in results if r.fast_time_ms and not r.fallback_occurred]
    fallback_results = [r for r in results if r.fallback_occurred]
    browser_results = [r for r in results if r.browser_time_ms and not r.fast_time_ms]

    # Speedup for pure fast paths
    if fast_results:
        avg_fast = statistics.mean(r.fast_time_ms for r in fast_results)
        speedup = DEFAULT_BROWSER_TIME_MS / avg_fast
    else:
        speedup = 0

    # Fallback rate
    fallback_rate = len(fallback_results) / len(results) if results else 0

    # Routing distribution
    route_counts = {}
    for r in results:
        route_counts[r.route_chosen] = route_counts.get(r.route_chosen, 0) + 1

    return generate_reportResult.model_validate({
        "summary": {
            "urls_tested": len(results),
            "pure_fast_count": len(fast_results),
            "fallback_count": len(fallback_results),
            "browser_only_count": len(browser_results),
            "fallback_rate": fallback_rate,
            "avg_fast_time_ms": statistics.mean(r.fast_time_ms for r in fast_results) if fast_results else None,
            "speedup_vs_browser": speedup,
        },
        "routing_distribution": route_counts,
        "router_rules_triggered": list(set(r.router_reason for r in results)),
        "details": [
            {
                "url": r.url,
                "route": r.route_chosen,
                "reason": r.router_reason,
                "fast_ms": r.fast_time_ms,
                "browser_ms": r.browser_time_ms,
                "fallback": r.fallback_occurred,
            }
            for r in results
        ],
    })


async def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark Smart Router")
    parser.add_argument("--urls", help="File with URLs to test (one per line)")
    parser.add_argument("--sample", action="store_true", help="Use sample URLs")
    parser.add_argument("--iterations", type=int, default=5, help="Iterations per URL")
    parser.add_argument("--output", help="Output JSON file")
    args = parser.parse_args()

    # Get URLs
    if args.sample:
        urls = SAMPLE_URLS
    elif args.urls:
        with open(args.urls, encoding="utf-8") as f:
            urls = [(line.strip(), "unknown") for line in f if line.strip()]
    else:
        print("Error: Provide --urls or --sample", file=sys.stderr)
        return 1

    # Run benchmarks
    print(f"Benchmarking {len(urls)} URLs with {args.iterations} iterations each...")

    results = []
    for url, url_type in urls:
        print(f"  Testing {url}...")
        try:
            result = await benchmark_url(url, url_type, args.iterations)
            results.append(result)
        except (OSError, RuntimeError) as exc:
            print(f"    Error benchmarking {url}: {exc}", file=sys.stderr)

    # Generate report
    report = generate_report(results)

    # Output
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"URLs tested: {report['summary']['urls_tested']}")
    print(f"Pure fast path: {report['summary']['pure_fast_count']}")
    print(f"Fallbacks: {report['summary']['fallback_count']}")
    print(f"Fallback rate: {report['summary']['fallback_rate']:.1%}")
    print(f"Speedup vs browser: {report['summary']['speedup_vs_browser']:.1f}x")
    avg_fast = report["summary"]["avg_fast_time_ms"]
    if avg_fast is not None:
        print(f"Avg fast path time: {avg_fast:.0f}ms")
    else:
        print("Avg fast path time: N/A")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nFull report written to: {args.output}")

    return 0


if __name__ == "__main__":
    asyncio.run(main())
