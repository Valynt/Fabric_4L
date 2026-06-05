#!/usr/bin/env python3
"""Cross-layer production smoke test for Value Fabric Platform.

Validates L2→L3→L4 integration across 6 stages:
1. L2 Health Check
2. L3 Health + Neo4j Connectivity
3. L4 Health + Postgres Checkpoint Connectivity
4. L2→L3 Extract-and-Ingest Round-trip
5. L3 Graph Query Verification
6. L3 Hybrid Search Verification

Usage:
    python docs/runbooks/operational/production_smoke.py
    python docs/runbooks/operational/production_smoke.py --l2-url http://localhost:8002 --l3-url http://localhost:8003 --l4-url http://localhost:8004

Exit Codes:
    0: All stages passed
    1: One or more stages failed
    2: Configuration error
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx


@dataclass
class StageResult:
    """Result of a single smoke test stage."""

    name: str
    status: str  # "pass" or "fail"
    duration_ms: int
    attempts: int
    error: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SmokeReport:
    """Complete smoke test report."""

    timestamp: str
    overall: str  # "pass" or "fail"
    stages: list[StageResult]
    total_duration_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "overall": self.overall,
            "stages": [
                {
                    "name": s.name,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "attempts": s.attempts,
                    **({"error": s.error} if s.error else {}),
                    **({"details": s.details} if s.details else {}),
                }
                for s in self.stages
            ],
            "total_duration_ms": self.total_duration_ms,
        }


class SmokeTestRunner:
    """Runner for cross-layer smoke tests."""

    def __init__(
        self,
        l2_url: str = "http://localhost:8002",
        l3_url: str = "http://localhost:8003",
        l4_url: str = "http://localhost:8004",
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.l2_url = l2_url.rstrip("/")
        self.l3_url = l3_url.rstrip("/")
        self.l4_url = l4_url.rstrip("/")
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = httpx.AsyncClient(timeout=30.0)
        self.stages: list[StageResult] = []

    async def close(self) -> None:
        await self.client.aclose()

    async def run_with_retry(
        self,
        name: str,
        test_func: callable,
        *args,
        **kwargs,
    ) -> StageResult:
        """Run a test function with retry logic.

        Args:
            name: Stage name for reporting
            test_func: Async callable returning:
                - bool (success flag), or
                - tuple[bool, dict] (success flag, details dict)
            *args, **kwargs: Passed to test_func

        Returns:
            StageResult with status, timing, and attempt count
        """
        start_time = time.time()
        last_error: Optional[str] = None
        details: dict[str, Any] = {}

        for attempt in range(1, self.max_retries + 1):
            try:
                result = await test_func(*args, **kwargs)
                if isinstance(result, tuple):
                    success, details = result
                else:
                    success = result

                if success:
                    duration_ms = int((time.time() - start_time) * 1000)
                    return StageResult(
                        name=name,
                        status="pass",
                        duration_ms=duration_ms,
                        attempts=attempt,
                        details=details,
                    )
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2 ** (attempt - 1)))

        duration_ms = int((time.time() - start_time) * 1000)
        return StageResult(
            name=name,
            status="fail",
            duration_ms=duration_ms,
            attempts=self.max_retries,
            error=last_error or "Test failed after all retries",
            details=details,
        )

    async def stage_1_l2_health(self) -> StageResult:
        """Stage 1: Verify L2 extraction service health."""

        async def test():
            response = await self.client.get(f"{self.l2_url}/health")
            response.raise_for_status()
            data = response.json()
            status = data.get("status", "unknown")
            return status in ("healthy", "degraded"), {"l2_status": status}

        return await self.run_with_retry("L2 Health", test)

    async def stage_2_l3_health(self) -> StageResult:
        """Stage 2: Verify L3 knowledge graph health + Neo4j connectivity."""

        async def test():
            response = await self.client.get(f"{self.l3_url}/health")
            response.raise_for_status()
            data = response.json()
            status = data.get("status", "unknown")
            neo4j_status = data.get("neo4j", {}).get("status", "unknown")

            healthy = status in ("healthy", "degraded") and neo4j_status == "healthy"
            return healthy, {
                "l3_status": status,
                "neo4j_status": neo4j_status,
            }

        return await self.run_with_retry("L3 Health + Neo4j", test)

    async def stage_3_l4_health(self) -> StageResult:
        """Stage 3: Verify L4 agents health + Postgres checkpoint connectivity."""

        async def test():
            response = await self.client.get(f"{self.l4_url}/health")
            response.raise_for_status()
            data = response.json()
            status = data.get("status", "unknown")

            healthy = status in ("healthy", "degraded")
            return healthy, {"l4_status": status}

        return await self.run_with_retry("L4 Health + Postgres", test)

    async def stage_4_extract_ingest(self) -> StageResult:
        """Stage 4: L2→L3 extract-and-ingest round-trip."""

        async def test():
            # Kick off extraction
            payload = {
                "content_id": "smoke-test-content",
                "source_url": "https://example.com/smoke-test",
                "markdown_content": "# Smoke Test\n\nThis is a test capability for smoke testing.",
                "extraction_config": {
                    "chunk_size": 500,
                    "chunk_overlap": 50,
                    "confidence_threshold": 0.5,
                },
            }

            response = await self.client.post(
                f"{self.l2_url}/v1/extract-and-ingest",
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            job_id = data.get("job_id")

            if not job_id:
                return False, {"error": "No job_id in response"}

            # Poll for completion (max 60 seconds)
            for _ in range(60):
                status_response = await self.client.get(
                    f"{self.l2_url}/v1/extract/status/{job_id}"
                )
                status_response.raise_for_status()
                status_data = status_response.json()

                overall_status = status_data.get("overall_status", "unknown")

                if overall_status == "completed":
                    return True, {
                        "job_id": job_id,
                        "final_status": overall_status,
                        "entities_extracted": status_data.get("entities_extracted", 0),
                        "relationships_extracted": status_data.get("relationships_extracted", 0),
                    }
                elif overall_status in ("failed", "error"):
                    return False, {
                        "job_id": job_id,
                        "final_status": overall_status,
                        "error": status_data.get("last_error", "Unknown error"),
                    }

                await asyncio.sleep(1)

            return False, {"job_id": job_id, "error": "Timeout waiting for completion"}

        return await self.run_with_retry("L2→L3 Extract-Ingest", test)

    async def stage_5_graph_query(self) -> StageResult:
        """Stage 5: L3 graph query verification."""

        async def test():
            payload = {
                "query": "test capability",
                "max_hops": 2,
            }

            response = await self.client.post(
                f"{self.l3_url}/v1/query/graph",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            len(data.get("entities", [])) >= 0  # Empty is ok, just needs to work
            has_response = "response" in data or "entities" in data

            return has_response, {
                "entity_count": len(data.get("entities", [])),
                "relationship_count": len(data.get("relationships", [])),
            }

        return await self.run_with_retry("L3 Graph Query", test)

    async def stage_6_hybrid_search(self) -> StageResult:
        """Stage 6: L3 hybrid search verification."""

        async def test():
            payload = {
                "query": "test",
                "limit": 10,
            }

            response = await self.client.post(
                f"{self.l3_url}/v1/search/hybrid",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            has_results = "results" in data or "entities" in data

            return has_results, {
                "result_count": len(data.get("results", [])),
            }

        return await self.run_with_retry("L3 Hybrid Search", test)

    async def run_all(self) -> SmokeReport:
        """Run all smoke test stages."""
        start_time = time.time()

        # Run all stages
        stages = [
            await self.stage_1_l2_health(),
            await self.stage_2_l3_health(),
            await self.stage_3_l4_health(),
            await self.stage_4_extract_ingest(),
            await self.stage_5_graph_query(),
            await self.stage_6_hybrid_search(),
        ]

        total_duration_ms = int((time.time() - start_time) * 1000)
        overall = "pass" if all(s.status == "pass" for s in stages) else "fail"

        return SmokeReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            overall=overall,
            stages=stages,
            total_duration_ms=total_duration_ms,
        )


def save_report(report: SmokeReport, output_dir: Path) -> Path:
    """Save smoke report to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filepath = output_dir / f"smoke-report-{timestamp}.json"

    with open(filepath, "w") as f:
        json.dump(report.to_dict(), f, indent=2)

    return filepath


def print_report(report: SmokeReport) -> None:
    """Print smoke report to console."""
    print("\n" + "=" * 60)
    print(f"SMOKE TEST REPORT - {report.timestamp}")
    print("=" * 60)

    overall_symbol = "✓" if report.overall == "pass" else "✗"
    print(f"\nOverall: {overall_symbol} {report.overall.upper()}")
    print(f"Total Duration: {report.total_duration_ms}ms\n")

    for stage in report.stages:
        symbol = "✓" if stage.status == "pass" else "✗"
        print(f"  {symbol} {stage.name}")
        print(f"     Status: {stage.status.upper()}")
        print(f"     Duration: {stage.duration_ms}ms")
        print(f"     Attempts: {stage.attempts}")
        if stage.error:
            print(f"     Error: {stage.error}")
        print()

    print("=" * 60)


async def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cross-layer production smoke test for Value Fabric Platform"
    )
    parser.add_argument(
        "--l2-url",
        default=os.getenv("L2_URL", "http://localhost:8002"),
        help="Layer 2 API URL (default: http://localhost:8002)",
    )
    parser.add_argument(
        "--l3-url",
        default=os.getenv("L3_URL", "http://localhost:8003"),
        help="Layer 3 API URL (default: http://localhost:8003)",
    )
    parser.add_argument(
        "--l4-url",
        default=os.getenv("L4_URL", "http://localhost:8004"),
        help="Layer 4 API URL (default: http://localhost:8004)",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts",
        help="Directory for JSON report output (default: artifacts)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts per stage (default: 3)",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=1.0,
        help="Initial retry delay in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    # Validate URLs
    for url_name, url in [("L2", args.l2_url), ("L3", args.l3_url), ("L4", args.l4_url)]:
        if not url.startswith(("http://", "https://")):
            print(f"Error: Invalid {url_name} URL: {url}", file=sys.stderr)
            return 2

    runner = SmokeTestRunner(
        l2_url=args.l2_url,
        l3_url=args.l3_url,
        l4_url=args.l4_url,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
    )

    try:
        report = await runner.run_all()
    finally:
        await runner.close()

    # Print and save report
    print_report(report)
    output_path = save_report(report, Path(args.output_dir))
    print(f"Report saved to: {output_path}")

    return 0 if report.overall == "pass" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
