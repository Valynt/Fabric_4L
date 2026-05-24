#!/usr/bin/env python3
"""
Layer 1 Real-Data Test Harness — Frontend-Style Output

Mimics the exact API flow the frontend uses (useSources.ts + useIngestion.ts)
and formats responses with the same normalization logic the UI applies.

Usage:
    python scripts/test-l1-real-data.py --scenario fast
    python scripts/test-l1-real-data.py --scenario spider
    python scripts/test-l1-real-data.py --scenario skill
"""

from __future__ import annotations

import argparse
import sys
import time
import uuid
from typing import Any

import httpx
import jwt

LAYER1_BASE = "http://localhost:8001/api/v1/ingestion"
POLL_INTERVAL = 3.0
MAX_POLL_SECONDS = 120

# JWT configuration (matches docker-compose.live.yml dev defaults)
JWT_SECRET = "dev-local-secret-do-not-use-in-production-minimum-32-chars"
JWT_ISSUER = "value-fabric-internal"
JWT_AUDIENCE = "value-fabric-services"


def make_jwt_token() -> str:
    """Generate a short-lived dev JWT token for Layer 1 API access."""
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    payload = {
        "exp": int(time.time()) + 3600,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "sub": user_id,
        "tenant_id": tenant_id,
        "roles": ["admin"],
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# ═══════════════════════════════════════════════════════════════════════════════
# Frontend-style normalization (ported from useSources.ts / useIngestion.ts)
# ═══════════════════════════════════════════════════════════════════════════════

FRONTEND_TO_BACKEND_TARGET_TYPE = {
    "crm": "API_ENDPOINT",
    "database": "API_ENDPOINT",
    "file": "SINGLE_PAGE",
    "api": "API_ENDPOINT",
    "cloud_storage": "API_ENDPOINT",
}

BACKEND_TARGET_TYPE_TO_FRONTEND = {v: k for k, v in FRONTEND_TO_BACKEND_TARGET_TYPE.items()}

JOB_STATUS_MAP = {
    "PENDING": "pending",
    "QUEUED": "pending",
    "VALIDATING": "processing",
    "BROWSER_ACQUIRING": "processing",
    "NAVIGATING": "processing",
    "EXTRACTING": "processing",
    "TRANSFORMING": "processing",
    "STORING": "processing",
    "COMPLETED": "completed",
    "FAILED": "failed",
    "CANCELLED": "failed",
    "PARTIAL_SUCCESS": "completed",
}


def map_target_type(source_category: str | None, target_type: str, tags: list[str] | None = None, url: str = "") -> str:
    """Map backend target info to frontend SourceType."""
    if source_category:
        normalized = source_category.lower()
        if normalized in FRONTEND_TO_BACKEND_TARGET_TYPE:
            return normalized
    tag_map = {
        "crm": "crm", "salesforce": "crm", "hubspot": "crm",
        "database": "database", "postgres": "database", "mysql": "database",
        "s3": "cloud_storage", "gcs": "cloud_storage", "azure": "cloud_storage",
        "file": "file", "csv": "file", "json": "file",
    }
    for tag in (tags or []):
        lower = tag.lower()
        if lower in tag_map:
            return tag_map[lower]
    lower_url = url.lower()
    if "salesforce" in lower_url or "hubapi" in lower_url:
        return "crm"
    if "postgres" in lower_url or "mysql" in lower_url or "://db" in lower_url:
        return "database"
    if "s3." in lower_url or "blob.core.windows.net" in lower_url:
        return "cloud_storage"
    return "api"


def derive_connection_status(target_status: str, last_success_at: str | None, last_error_at: str | None, error_count: int) -> str:
    if target_status == "ERROR":
        return "error"
    if target_status == "PAUSED":
        return "disconnected"
    if error_count > 0 and last_error_at and (not last_success_at or last_error_at > last_success_at):
        return "error"
    if last_success_at:
        return "connected"
    return "disconnected"


def calculate_health_score(success_count: int, error_count: int) -> int:
    total = success_count + error_count
    if total == 0:
        return 0
    return round((success_count / total) * 100)


def map_job_status(status: str) -> str:
    return JOB_STATUS_MAP.get(status, "pending")


# ═══════════════════════════════════════════════════════════════════════════════
# Pretty-print helpers
# ═══════════════════════════════════════════════════════════════════════════════

def print_header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_kv(data: dict[str, Any], indent: int = 2) -> None:
    pad = " " * indent
    for k, v in data.items():
        if isinstance(v, dict):
            print(f"{pad}{k}:")
            print_kv(v, indent + 2)
        elif isinstance(v, list):
            print(f"{pad}{k}: [{len(v)} items]")
            for item in v[:5]:
                print(f"{pad}  - {item}")
            if len(v) > 5:
                print(f"{pad}  ... and {len(v) - 5} more")
        else:
            print(f"{pad}{k}: {v}")


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    if not rows:
        print("  (no data)")
        return
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    print(f"  {sep}")
    print("  | " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |")
    print(f"  {sep}")
    for row in rows:
        print("  | " + " | ".join(str(c).ljust(w) for c, w in zip(row, widths)) + " |")
    print(f"  {sep}")


# ═══════════════════════════════════════════════════════════════════════════════
# API helpers
# ═══════════════════════════════════════════════════════════════════════════════

# Reuse the same tenant/user for the entire test run so entities are visible
_test_token: str | None = None

def _auth_headers() -> dict[str, str]:
    global _test_token
    if _test_token is None:
        _test_token = make_jwt_token()
    return {"Authorization": f"Bearer {_test_token}"}


def l1_post(path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
    resp = httpx.post(f"{LAYER1_BASE}{path}", json=json, headers=_auth_headers(), timeout=30.0)
    resp.raise_for_status()
    return resp.json()


def l1_get(path: str) -> dict[str, Any]:
    resp = httpx.get(f"{LAYER1_BASE}{path}", headers=_auth_headers(), timeout=30.0)
    resp.raise_for_status()
    return resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
# Scenarios
# ═══════════════════════════════════════════════════════════════════════════════

def scenario_fast() -> None:
    """Single-page crawl on example.com (fast httpx path)."""
    print_header("Scenario A: Single-Page Fast Crawl")

    # 1. Create target
    print("\n[API] POST /targets")
    target = l1_post("/targets", {
        "name": "example.com",
        "url": "https://example.com",
        "target_type": "SINGLE_PAGE",
        "source_category": "api",
        "crawl_path": "fast",
        "tags": ["test", "fast-path"],
    })
    target_id = target["id"]
    print_kv({
        "id": target_id,
        "name": target["name"],
        "url": target["url"],
        "target_type": target["target_type"],
        "source_category": target.get("source_category"),
        "status": target["status"],
    })

    # 2. Validate
    print("\n[API] POST /targets/{id}/validate")
    validation = l1_post(f"/targets/{target_id}/validate", {})
    print_kv(validation)

    # 3. Execute
    print("\n[API] POST /targets/{id}/execute")
    execution = l1_post(f"/targets/{target_id}/execute", {"priority": 5})
    job_id = execution["job_id"]
    print_kv({"job_id": job_id})

    # 4. Poll job
    print_header("Polling Job")
    job = poll_job(job_id)
    if not job:
        print("[FAIL] Job polling timed out")
        return

    # 5. Results
    print_header("Job Results")
    try:
        results = l1_get(f"/jobs/{job_id}/results")
        print_kv(results)
    except httpx.HTTPStatusError as e:
        print(f"  (no results endpoint data: {e.response.status_code})")

    # 6. Compliance logs
    print_header("Compliance Logs")
    try:
        logs = l1_get(f"/compliance/logs?job_id={job_id}")
        items = logs.get("items") or logs.get("data") or []
        if items:
            print_table(
                ["event_type", "severity", "request_url", "action"],
                [
                    [
                        i.get("event_type", "-"),
                        i.get("severity", "-"),
                        (i.get("request_url") or "-")[:40],
                        i.get("response_action_taken", "-"),
                    ]
                    for i in items
                ],
            )
        else:
            print("  (no compliance logs)")
    except httpx.HTTPStatusError as e:
        print(f"  (compliance logs unavailable: {e.response.status_code})")

    # 7. Source corpora / skill outputs (if any)
    print_header("Source Corpora")
    try:
        corpora = l1_get("/source-corpora")
        data = corpora.get("data") or corpora.get("items") or []
        if data:
            print_table(
                ["id", "domain", "status"],
                [[c.get("id", "-"), c.get("domain", "-"), c.get("status", "-")] for c in data[:5]],
            )
        else:
            print("  (no source corpora yet)")
    except httpx.HTTPStatusError as e:
        print(f"  (source corpora unavailable: {e.response.status_code})")

    print_header("Scenario A Complete")


def scenario_spider() -> None:
    """Shallow spider crawl on Wikipedia."""
    print_header("Scenario B: Spider Crawl (Wikipedia)")

    print("\n[API] POST /targets")
    target = l1_post("/targets", {
        "name": "Wikipedia Web Crawling",
        "url": "https://en.wikipedia.org/wiki/Web_crawling",
        "target_type": "SPIDER",
        "source_category": "api",
        "extraction_config": {"max_depth": 1, "follow_links": True},
        "tags": ["test", "spider"],
    })
    target_id = target["id"]
    print_kv({
        "id": target_id,
        "name": target["name"],
        "url": target["url"],
        "target_type": target["target_type"],
        "status": target["status"],
    })

    print("\n[API] POST /targets/{id}/execute")
    execution = l1_post(f"/targets/{target_id}/execute", {"priority": 5})
    job_id = execution["job_id"]
    print_kv({"job_id": job_id})

    print_header("Polling Job")
    job = poll_job(job_id)
    if not job:
        print("[FAIL] Job polling timed out")
        return

    print_header("Job Results")
    try:
        results = l1_get(f"/jobs/{job_id}/results")
        print_kv(results)
    except httpx.HTTPStatusError as e:
        print(f"  (no results: {e.response.status_code})")

    print_header("Scenario B Complete")


def scenario_skill() -> None:
    """Prospect research skill job."""
    print_header("Scenario C: Prospect Research Skill Job")

    print("\n[API] POST /jobs/prospect-research")
    try:
        job = l1_post("/jobs/prospect-research", {
            "target_entity_id": "wikipedia-org",
            "target_url": "https://en.wikipedia.org",
            "priority": 5,
        })
    except httpx.HTTPStatusError as e:
        print(f"[FAIL] Skill job creation failed: {e.response.status_code}")
        print(f"   {e.response.text}")
        return

    job_id = job["id"]
    print_kv({"job_id": job_id, "job_type": job.get("job_type"), "status": job.get("status")})

    print_header("Polling Job")
    job = poll_job(job_id)
    if not job:
        print("[FAIL] Job polling timed out")
        return

    print_header("Skill Output")
    try:
        output = l1_get(f"/jobs/{job_id}/skill-output")
        print_kv(output)
    except httpx.HTTPStatusError as e:
        print(f"  (skill output unavailable: {e.response.status_code})")

    print_header("Scenario C Complete")


# ═══════════════════════════════════════════════════════════════════════════════
# Polling
# ═══════════════════════════════════════════════════════════════════════════════

def poll_job(job_id: str) -> dict[str, Any] | None:
    start = time.time()
    while time.time() - start < MAX_POLL_SECONDS:
        job = l1_get(f"/jobs/{job_id}")
        status = job.get("status", "UNKNOWN")
        frontend_status = map_job_status(status)
        progress = job.get("progress", {})
        percent = progress.get("percent_complete", 0)
        current_stage = progress.get("current_stage", "INIT")
        processed = progress.get("processed_pages", 0)
        total = progress.get("total_pages")

        bar_len = 20
        filled = int(bar_len * percent / 100)
        bar = "#" * filled + "-" * (bar_len - filled)

        total_str = str(total) if total else "?"
        print(
            f"\r  [{bar}] {percent:>3}% | {frontend_status:<10} | stage: {current_stage:<15} "
            f"| pages: {processed}/{total_str}",
            end="",
            flush=True,
        )

        if status in ("COMPLETED", "FAILED", "CANCELLED", "PARTIAL_SUCCESS"):
            print()  # newline
            print(f"\n[OK] Job finished with status: {status}")
            # Print final summary
            print_kv({
                "id": job["id"],
                "status": status,
                "frontend_status": frontend_status,
                "target_id": job.get("target_id"),
                "priority": job.get("priority"),
                "started_at": job.get("started_at"),
                "completed_at": job.get("completed_at"),
                "progress": progress,
                "results": job.get("results", {}),
                "resources": job.get("resources", {}),
                "errors": job.get("errors", []),
            })
            return job

        time.sleep(POLL_INTERVAL)

    print()  # newline
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(description="Layer 1 Real-Data Test Harness")
    parser.add_argument(
        "--scenario",
        choices=["fast", "spider", "skill", "all"],
        default="fast",
        help="Test scenario to run",
    )
    parser.add_argument(
        "--base-url",
        default=LAYER1_BASE,
        help="Layer 1 base URL",
    )
    args = parser.parse_args()

    # Update base URL if overridden
    base_url = args.base_url.rstrip("/")

    # Quick health check
    print_header("Layer 1 Health Check")
    try:
        health = l1_get("/health")
        print_kv(health)
    except Exception as e:
        print(f"[FAIL] Layer 1 health check failed: {e}")
        return 1

    if args.scenario in ("fast", "all"):
        scenario_fast()
    if args.scenario in ("spider", "all"):
        scenario_spider()
    if args.scenario in ("skill", "all"):
        scenario_skill()

    return 0


if __name__ == "__main__":
    sys.exit(main())
