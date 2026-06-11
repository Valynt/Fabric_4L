#!/usr/bin/env python3
"""Critical-path E2E smoke test: L1 → L2 → L3 → L4 → L5 → L6.

Runs the minimum viable end-to-end sequence required for Phase 1 sign-off.
Captures per-layer health status, request/response summaries, and timestamps
into a JSON artifact committed under signoff-evidence/.

Port / network notes (docker-compose.live.yml)
-----------------------------------------------
Only L4 (8004) and the frontend (3001) are bound to the host. All other
layers run on internal Docker network ports:

    Layer  Container port  Host port  Docker service name
    -----  --------------  ---------  -------------------
    L1     8000            —          layer1
    L2     8000            —          layer2
    L3     8001            —          layer3
    L4     8000            8004       layer4
    L5     8005            —          layer5
    L6     8006            —          layer6

Run modes:

  --network   Use Docker internal service names (default when running inside
              the compose network, e.g. via `docker compose exec`):
                L1=http://layer1:8000  L2=http://layer2:8000
                L3=http://layer3:8001  L4=http://layer4:8000
                L5=http://layer5:8005  L6=http://layer6:8006

  --host      Use host-accessible URLs. Only L4 is directly reachable;
              L1/L2/L3/L5/L6 must be tunnelled or proxied first:
                L4=http://localhost:8004
              Override individual layers via env vars (see below).

  env vars    Override any URL regardless of mode:
                L1_URL, L2_URL, L3_URL, L4_URL, L5_URL, L6_URL

Usage:
    # Inside the compose network (recommended)
    docker compose -f docker-compose.live.yml exec layer4 \\
        python /app/scripts/e2e/critical_path_smoke.py --network

    # From host (L4 only reachable directly; others need tunnels)
    python scripts/e2e/critical_path_smoke.py --host

    # Dry run (health checks only, no data mutations)
    python scripts/e2e/critical_path_smoke.py --network --dry-run

    # Fully custom URLs
    L1_URL=http://... L2_URL=http://... python scripts/e2e/critical_path_smoke.py

Exit codes:
    0  All steps passed
    1  One or more steps failed
    2  Configuration error
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

try:
    import jwt
except ImportError:
    jwt = None

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "signoff-evidence" / "e2e"

# Docker-internal service URLs (correct when running inside the compose network)
_NETWORK_DEFAULTS: dict[str, str] = {
    "L1": "http://layer1:8000",
    "L2": "http://layer2:8000",
    "L3": "http://layer3:8001",
    "L4": "http://layer4:8000",
    "L5": "http://layer5:8005",
    "L6": "http://layer6:8006",
}

# Host-accessible URLs (only L4 is bound to the host in docker-compose.live.yml)
# L1/L2/L3/L5/L6 are not host-exposed; set *_URL env vars to override.
_HOST_DEFAULTS: dict[str, str] = {
    "L1": "http://localhost:8001",   # not host-bound — override via L1_URL
    "L2": "http://localhost:8002",   # not host-bound — override via L2_URL
    "L3": "http://localhost:8003",   # not host-bound — override via L3_URL
    "L4": "http://localhost:8004",   # host-bound: 8004→container:8000 ✓
    "L5": "http://localhost:8005",   # not host-bound — override via L5_URL
    "L6": "http://localhost:8006",   # not host-bound — override via L6_URL
}


def _build_layer_urls(network_mode: bool) -> dict[str, str]:
    """Build the layer URL map, applying env var overrides on top of mode defaults."""
    defaults = _NETWORK_DEFAULTS if network_mode else _HOST_DEFAULTS
    return {
        layer: os.getenv(f"{layer}_URL", default)
        for layer, default in defaults.items()
    }


# Service-to-service auth via GovernanceMiddleware (X-Tenant-ID + X-Service-Auth)
SERVICE_AUTH_SECRET = (
    os.getenv("E2E_SERVICE_AUTH_SECRET")
    or os.getenv("SERVICE_AUTH_SECRET")
    or "dev-service-auth-secret-change-in-production"
)
TENANT_ID = os.getenv("E2E_TENANT_ID", "00000000-0000-4000-8000-000000000001")
try:
    TIMEOUT = int(os.getenv("E2E_TIMEOUT_SECONDS") or "10")
except ValueError as exc:
    raise SystemExit(
        f"Invalid E2E_TIMEOUT_SECONDS: {os.getenv('E2E_TIMEOUT_SECONDS')!r} — must be an integer"
    ) from exc


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class StepResult:
    step: str
    layer: str
    status: str          # "pass" | "fail" | "skip"
    http_status: int | None = None
    url: str = ""
    request_summary: str = ""
    response_summary: str = ""
    duration_ms: float = 0.0
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class SmokeResult:
    run_id: str
    started_at: str
    completed_at: str = ""
    overall_status: str = "unknown"   # "pass" | "fail" | "partial"
    dry_run: bool = False
    layer_health: dict[str, str] = field(default_factory=dict)
    steps: list[StepResult] = field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Tenant-ID": TENANT_ID,
        "X-Service-Auth": SERVICE_AUTH_SECRET,
        "X-Request-ID": f"e2e-smoke-{uuid.uuid4().hex[:8]}",
    }


def _encode_s2s_jwt(sub: str, aud: str) -> str | None:
    """Encode a service-to-service JWT using SERVICE_AUTH_SECRET."""
    if jwt is None:
        return None
    secret = SERVICE_AUTH_SECRET
    if not secret:
        return None
    now = int(time.time())
    payload = {
        "sub": sub,
        "aud": aud,
        "tenant_id": TENANT_ID,
        "iat": now,
        "nbf": now,
        "exp": now + 300,
        "iss": "value-fabric-s2s",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _http(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    timeout: int = TIMEOUT,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Make an HTTP request; return (status_code, response_body)."""
    data = json.dumps(body).encode() if body else None
    headers = _headers()
    if extra_headers:
        headers.update(extra_headers)
    req = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, {"_raw": raw[:500]}
    except URLError as exc:
        raise ConnectionError(f"HTTP {method} {url} failed: {exc}") from exc


def _health(layer: str, layer_urls: dict[str, str]) -> tuple[bool, int | None, str]:
    """Check /health endpoint. Returns (ok, status_code, detail)."""
    url = f"{layer_urls[layer]}/health"
    try:
        status, body = _http("GET", url, timeout=5)
        ok = status == 200
        return ok, status, json.dumps(body)[:200]
    except ConnectionError as exc:
        return False, None, str(exc)


# ---------------------------------------------------------------------------
# Smoke steps
# ---------------------------------------------------------------------------


def step_health_checks(result: SmokeResult, layer_urls: dict[str, str]) -> bool:
    """Step 0: Verify all six layer health endpoints return 200."""
    all_ok = True
    for layer in ["L1", "L2", "L3", "L4", "L5", "L6"]:
        ok, code, detail = _health(layer, layer_urls)
        result.layer_health[layer] = "healthy" if ok else f"unhealthy (HTTP {code})"
        sr = StepResult(
            step=f"health_{layer}",
            layer=layer,
            status="pass" if ok else "fail",
            http_status=code,
            url=f"{layer_urls[layer]}/health",
            response_summary=detail,
        )
        result.steps.append(sr)
        if not ok:
            all_ok = False
            print(f"  ❌ {layer} health: {detail}")
        else:
            print(f"  ✅ {layer} health: OK")
    return all_ok


def step_l1_ingest(result: SmokeResult, layer_urls: dict[str, str], dry_run: bool) -> str | None:
    """Step 1: GET L1 /api/v1/ingestion/jobs — list jobs to verify reachability."""
    url = f"{layer_urls['L1']}/api/v1/ingestion/jobs"
    t0 = time.monotonic()
    try:
        if dry_run:
            sr = StepResult(step="l1_ingest", layer="L1", status="skip",
                            request_summary=f"GET {url}", response_summary="dry_run")
            result.steps.append(sr)
            print("  ⏭  L1 ingest: skipped (dry run)")
            return "dry-run-job-id"

        status, body = _http("GET", url)
        duration = (time.monotonic() - t0) * 1000
        job_id = None
        if isinstance(body, dict):
            job_id = body.get("job_id") or body.get("id")
            data = body.get("data")
            if not job_id and isinstance(data, dict):
                job_id = data.get("job_id")
            elif not job_id and isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, dict):
                    job_id = first.get("id") or first.get("job_id")
        elif isinstance(body, list) and body:
            first = body[0]
            if isinstance(first, dict):
                job_id = first.get("id") or first.get("job_id")
        ok = status == 200
        sr = StepResult(
            step="l1_ingest", layer="L1",
            status="pass" if ok else "fail",
            http_status=status,
            url=url,
            request_summary=f"GET {url} tenant={TENANT_ID}",
            response_summary=f"job_id={job_id} status={status}",
            duration_ms=duration,
        )
        result.steps.append(sr)
        if ok:
            print(f"  ✅ L1 ingest: reachable (HTTP {status})")
            return str(job_id) if job_id else "listed"
        else:
            print(f"  ❌ L1 ingest: HTTP {status} body={json.dumps(body)[:200]}")
            return None
    except ConnectionError as exc:
        result.steps.append(StepResult(step="l1_ingest", layer="L1", status="fail",
                                        error=str(exc), url=url))
        print(f"  ❌ L1 ingest: {exc}")
        return None


def step_l2_extract(result: SmokeResult, layer_urls: dict[str, str], job_id: str, dry_run: bool) -> str | None:
    """Step 2: Trigger L2 extraction — returns entity_id or None."""
    url = f"{layer_urls['L2']}/v1/extract"
    payload = {
        "content_id": job_id,
        "source_url": "https://example.com/e2e-smoke-test",
        "markdown_content": "Value Fabric E2E smoke test entity for critical path validation.",
    }
    t0 = time.monotonic()
    try:
        if dry_run:
            sr = StepResult(step="l2_extract", layer="L2", status="skip",
                            request_summary=f"POST {url}", response_summary="dry_run")
            result.steps.append(sr)
            print("  ⏭  L2 extract: skipped (dry run)")
            return "dry-run-entity-id"

        s2s_token = _encode_s2s_jwt(sub="layer1-ingestion", aud="layer2-extraction")
        extra_headers = {"Authorization": f"Bearer {s2s_token}"} if s2s_token else {}
        status, body = _http("POST", url, body=payload, extra_headers=extra_headers)
        duration = (time.monotonic() - t0) * 1000
        entity_id = None
        if isinstance(body, dict):
            entity_id = body.get("entity_id") or body.get("id")
            data = body.get("data")
            if not entity_id and isinstance(data, dict):
                entity_id = data.get("entity_id")
            elif not entity_id and isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, dict):
                    entity_id = first.get("id") or first.get("entity_id")
        ok = status in (200, 201, 202)
        sr = StepResult(
            step="l2_extract", layer="L2",
            status="pass" if ok else "fail",
            http_status=status,
            url=url,
            request_summary=f"POST {url} job_id={job_id}",
            response_summary=f"entity_id={entity_id} status={status}",
            duration_ms=duration,
        )
        result.steps.append(sr)
        if ok:
            print(f"  ✅ L2 extract: entity_id={entity_id}")
            return str(entity_id) if entity_id else "extracted"
        else:
            print(f"  ❌ L2 extract: HTTP {status} body={json.dumps(body)[:200]}")
            return None
    except ConnectionError as exc:
        result.steps.append(StepResult(step="l2_extract", layer="L2", status="fail",
                                        error=str(exc), url=url))
        print(f"  ❌ L2 extract: {exc}")
        return None


def step_l3_graph(result: SmokeResult, layer_urls: dict[str, str], dry_run: bool) -> bool:
    """Step 3: Verify L3 formulas endpoint is reachable (GET /v1/formulas)."""
    url = f"{layer_urls['L3']}/v1/formulas?limit=1"
    t0 = time.monotonic()
    try:
        if dry_run:
            result.steps.append(StepResult(step="l3_graph", layer="L3", status="skip",
                                            request_summary=f"GET {url}", response_summary="dry_run"))
            print("  ⏭  L3 graph: skipped (dry run)")
            return True

        status, body = _http("GET", url)
        duration = (time.monotonic() - t0) * 1000
        ok = status == 200
        count = len(body.get("entities", body.get("items", body.get("data", []))))
        sr = StepResult(
            step="l3_graph", layer="L3",
            status="pass" if ok else "fail",
            http_status=status,
            url=url,
            request_summary=f"GET {url}",
            response_summary=f"status={status} entity_count={count}",
            duration_ms=duration,
        )
        result.steps.append(sr)
        if ok:
            print(f"  ✅ L3 graph: {count} entities visible for tenant")
        else:
            print(f"  ❌ L3 graph: HTTP {status}")
        return ok
    except ConnectionError as exc:
        result.steps.append(StepResult(step="l3_graph", layer="L3", status="fail",
                                        error=str(exc), url=url))
        print(f"  ❌ L3 graph: {exc}")
        return False


def step_l4_agent(result: SmokeResult, layer_urls: dict[str, str], dry_run: bool) -> str | None:
    """Step 4: Trigger L4 ROI workflow — returns workflow_id or None."""
    url = f"{layer_urls['L4']}/v1/workflows"
    payload = {
        "workflow_type": "roi_calculator",
        "inputs": {
            "prospect_id": "e2e-smoke-prospect-001",
            "use_case_ids": ["uc-e2e-001"],
        },
    }
    t0 = time.monotonic()
    try:
        if dry_run:
            result.steps.append(StepResult(step="l4_agent", layer="L4", status="skip",
                                            request_summary=f"POST {url}", response_summary="dry_run"))
            print("  ⏭  L4 agent: skipped (dry run)")
            return "dry-run-workflow-id"

        # L4 workflow execution is synchronous and can take up to ~120s
        status, body = _http("POST", url, body=payload, timeout=180)
        duration = (time.monotonic() - t0) * 1000
        wf_id = (body.get("workflow_id") or body.get("id")
                 or body.get("data", {}).get("workflow_id"))
        ok = status in (200, 201, 202)
        sr = StepResult(
            step="l4_agent", layer="L4",
            status="pass" if ok else "fail",
            http_status=status,
            url=url,
            request_summary=f"POST {url} tenant={TENANT_ID}",
            response_summary=f"workflow_id={wf_id} status={status}",
            duration_ms=duration,
        )
        result.steps.append(sr)
        if ok:
            print(f"  ✅ L4 agent: workflow_id={wf_id}")
            return str(wf_id) if wf_id else "started"
        else:
            print(f"  ❌ L4 agent: HTTP {status} body={json.dumps(body)[:200]}")
            return None
    except ConnectionError as exc:
        result.steps.append(StepResult(step="l4_agent", layer="L4", status="fail",
                                        error=str(exc), url=url))
        print(f"  ❌ L4 agent: {exc}")
        return None


def step_l5_ground_truth(result: SmokeResult, layer_urls: dict[str, str], dry_run: bool) -> bool:
    """Step 5: Verify L5 ground-truth validation endpoint is reachable."""
    url = f"{layer_urls['L5']}/api/v1/truths?limit=1"
    t0 = time.monotonic()
    try:
        if dry_run:
            result.steps.append(StepResult(step="l5_ground_truth", layer="L5", status="skip",
                                            request_summary=f"GET {url}", response_summary="dry_run"))
            print("  ⏭  L5 ground truth: skipped (dry run)")
            return True

        status, body = _http("GET", url)
        duration = (time.monotonic() - t0) * 1000
        ok = status in (200, 404)  # 404 is acceptable (no data yet in smoke run)
        sr = StepResult(
            step="l5_ground_truth", layer="L5",
            status="pass" if ok else "fail",
            http_status=status,
            url=url,
            request_summary=f"GET {url}",
            response_summary=f"status={status}",
            duration_ms=duration,
        )
        result.steps.append(sr)
        if ok:
            print(f"  ✅ L5 ground truth: reachable (HTTP {status})")
        else:
            print(f"  ❌ L5 ground truth: HTTP {status}")
        return ok
    except ConnectionError as exc:
        result.steps.append(StepResult(step="l5_ground_truth", layer="L5", status="fail",
                                        error=str(exc), url=url))
        print(f"  ❌ L5 ground truth: {exc}")
        return False


def step_l6_benchmark(result: SmokeResult, layer_urls: dict[str, str], dry_run: bool) -> bool:
    """Step 6: Verify L6 benchmark lookup returns a result."""
    url = f"{layer_urls['L6']}/v1/benchmarks/datasets?limit=1"
    t0 = time.monotonic()
    try:
        if dry_run:
            result.steps.append(StepResult(step="l6_benchmark", layer="L6", status="skip",
                                            request_summary=f"GET {url}", response_summary="dry_run"))
            print("  ⏭  L6 benchmark: skipped (dry run)")
            return True

        status, body = _http("GET", url)
        duration = (time.monotonic() - t0) * 1000
        ok = status in (200, 404)  # 404 acceptable (no seeded benchmarks in smoke run)
        sr = StepResult(
            step="l6_benchmark", layer="L6",
            status="pass" if ok else "fail",
            http_status=status,
            url=url,
            request_summary=f"GET {url}",
            response_summary=f"status={status}",
            duration_ms=duration,
        )
        result.steps.append(sr)
        if ok:
            print(f"  ✅ L6 benchmark: reachable (HTTP {status})")
        else:
            print(f"  ❌ L6 benchmark: HTTP {status}")
        return ok
    except ConnectionError as exc:
        result.steps.append(StepResult(step="l6_benchmark", layer="L6", status="fail",
                                        error=str(exc), url=url))
        print(f"  ❌ L6 benchmark: {exc}")
        return False


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_smoke(dry_run: bool = False, network_mode: bool = True) -> SmokeResult:
    layer_urls = _build_layer_urls(network_mode)
    run_id = uuid.uuid4().hex[:12]
    result = SmokeResult(
        run_id=run_id,
        started_at=datetime.now(UTC).isoformat(),
        dry_run=dry_run,
    )

    mode_label = "network (Docker internal)" if network_mode else "host"
    print(f"\n{'='*60}")
    print(f"Value Fabric Critical-Path E2E Smoke  run_id={run_id}")
    print(f"Mode: {mode_label}")
    print(f"{'='*60}")
    for layer, url in layer_urls.items():
        print(f"  {layer}: {url}")
    if dry_run:
        print("\n  MODE: dry-run (health checks only)")
    print()

    # Step 0: Health checks (always run, even in dry-run)
    print("\n[Step 0] Layer health checks")
    health_ok = step_health_checks(result, layer_urls)

    if not health_ok and not dry_run:
        print("\n⚠️  One or more layers unhealthy — continuing smoke to capture evidence")

    # Step 1: L1 ingest
    print("\n[Step 1] L1 → ingest job")
    job_id = step_l1_ingest(result, layer_urls, dry_run)

    # Step 2: L2 extract
    print("\n[Step 2] L2 → extract entity")
    entity_id = step_l2_extract(result, layer_urls, job_id or "unknown", dry_run)

    # Step 3: L3 graph
    print("\n[Step 3] L3 → graph entity lookup")
    l3_ok = step_l3_graph(result, layer_urls, dry_run)

    # Step 4: L4 agent
    print("\n[Step 4] L4 → ROI workflow")
    wf_id = step_l4_agent(result, layer_urls, dry_run)

    # Step 5: L5 ground truth
    print("\n[Step 5] L5 → ground truth validation")
    l5_ok = step_l5_ground_truth(result, layer_urls, dry_run)

    # Step 6: L6 benchmark
    print("\n[Step 6] L6 → benchmark lookup")
    l6_ok = step_l6_benchmark(result, layer_urls, dry_run)

    # Determine overall status
    result.completed_at = datetime.now(UTC).isoformat()
    failed = [s for s in result.steps if s.status == "fail"]
    passed = [s for s in result.steps if s.status == "pass"]
    skipped = [s for s in result.steps if s.status == "skip"]

    if dry_run:
        result.overall_status = "dry_run"
    elif not failed:
        result.overall_status = "pass"
    elif len(failed) < len(result.steps) / 2:
        result.overall_status = "partial"
    else:
        result.overall_status = "fail"

    result.summary = (
        f"overall={result.overall_status} "
        f"passed={len(passed)} failed={len(failed)} skipped={len(skipped)}"
    )

    print(f"\n{'='*60}")
    print(f"Result: {result.overall_status.upper()}  —  {result.summary}")
    print(f"{'='*60}\n")

    return result


# ---------------------------------------------------------------------------
# Evidence artifact
# ---------------------------------------------------------------------------


def write_evidence(result: SmokeResult) -> Path:
    """Write the smoke result to signoff-evidence/e2e/e2e-critical-path-YYYYMMDD.json."""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(UTC).strftime("%Y%m%d")
    artifact_path = EVIDENCE_DIR / f"e2e-critical-path-{date_str}.json"

    # Convert dataclasses to dict
    data = asdict(result)
    artifact_path.write_text(json.dumps(data, indent=2, default=str))
    print(f"Evidence written to: {artifact_path.relative_to(REPO_ROOT)}")
    return artifact_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run health checks only; skip data mutations",
    )
    parser.add_argument(
        "--no-artifact", action="store_true",
        help="Skip writing the evidence artifact",
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--network", dest="network_mode", action="store_true", default=True,
        help=(
            "Use Docker-internal service names (default). "
            "Run via `docker compose exec` inside the compose network."
        ),
    )
    mode_group.add_argument(
        "--host", dest="network_mode", action="store_false",
        help=(
            "Use host-accessible URLs. Only L4 (localhost:8004) is directly "
            "reachable from the host; set L1_URL…L6_URL env vars for others."
        ),
    )
    args = parser.parse_args()

    result = run_smoke(dry_run=args.dry_run, network_mode=args.network_mode)

    if not args.no_artifact:
        write_evidence(result)

    return 0 if result.overall_status in ("pass", "dry_run") else 1


if __name__ == "__main__":
    sys.exit(main())
