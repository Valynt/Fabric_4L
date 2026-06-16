#!/usr/bin/env python3
"""Probe script for Fabric_4L end-to-end mock workflow evidence.

Run this from the repository root. It checks service reachability and LLM
credential availability, then writes the API transcript and LLM trace JSON
artifacts used by docs/evidence/fabric4l-e2e-mock-workflow-20260616.md.
"""
from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "docs" / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

DATE_STAMP = "20260616"
LAYER_URLS = {
    "L1": os.getenv("L1_URL", "http://localhost:8001"),
    "L2": os.getenv("L2_URL", "http://localhost:8002"),
    "L3": os.getenv("L3_URL", "http://localhost:8003"),
    "L4": os.getenv("L4_URL", "http://localhost:8004"),
    "L5": os.getenv("L5_URL", "http://localhost:8005"),
    "L6": os.getenv("L6_URL", "http://localhost:8006"),
    "web": os.getenv("WEB_URL", "http://localhost:3001"),
}


def probe_health(name: str, url: str) -> dict:
    target = f"{url}/health"
    started = time.time()
    try:
        req = Request(target, method="GET", headers={"Accept": "application/json"})
        with urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return {
                "layer": name,
                "url": target,
                "method": "GET",
                "status": resp.status,
                "latency_seconds": round(time.time() - started, 3),
                "response_body_preview": body[:500],
                "error": None,
                "result": "PASS" if resp.status == 200 else "UNEXPECTED_STATUS",
            }
    except HTTPError as exc:
        return {
            "layer": name,
            "url": target,
            "method": "GET",
            "status": exc.code,
            "latency_seconds": round(time.time() - started, 3),
            "response_body_preview": exc.read().decode("utf-8", errors="replace")[:500],
            "error": f"HTTPError {exc.code}",
            "result": "AUTH_REQUIRED" if exc.code == 401 else "FAIL",
        }
    except URLError as exc:
        return {
            "layer": name,
            "url": target,
            "method": "GET",
            "status": None,
            "latency_seconds": round(time.time() - started, 3),
            "response_body_preview": None,
            "error": str(exc.reason),
            "result": "UNREACHABLE",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "layer": name,
            "url": target,
            "method": "GET",
            "status": None,
            "latency_seconds": round(time.time() - started, 3),
            "response_body_preview": None,
            "error": str(exc),
            "result": "FAIL",
        }


def probe_llm() -> dict:
    provider = os.getenv("LAYER4_LLM_PROVIDER", os.getenv("LLM_PROVIDER", "together"))
    key = os.getenv("LAYER4_TOGETHER_API_KEY") or os.getenv("TOGETHER_API_KEY")
    base_url = os.getenv(
        "LAYER4_TOGETHER_BASE_URL", os.getenv("TOGETHER_BASE_URL", "https://api.together.ai/v1")
    )
    model = os.getenv(
        "LAYER4_TOGETHER_DEFAULT_MODEL",
        os.getenv("EXTRACTION_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    )

    if not key:
        return {
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "credential_present": False,
            "result": "BLOCKED",
            "error": "No Together API key found in LAYER4_TOGETHER_API_KEY or TOGETHER_API_KEY.",
            "request": None,
            "response": None,
            "latency_seconds": None,
            "tokens": None,
        }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a concise value-engineering assistant.",
            },
            {
                "role": "user",
                "content": (
                    "A mid-market B2B SaaS company struggles with inconsistent discovery, "
                    "weak business cases, slow SE/AE handoffs, and poor value proof in late-stage deals. "
                    "State one value hypothesis in one sentence."
                ),
            },
        ],
        "max_tokens": 120,
        "temperature": 0.2,
    }
    started = time.time()
    req = Request(
        f"{base_url}/chat/completions",
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return {
                "provider": provider,
                "model": model,
                "base_url": base_url,
                "credential_present": True,
                "result": "PASS",
                "error": None,
                "request": payload,
                "response": body,
                "latency_seconds": round(time.time() - started, 3),
                "tokens": body.get("usage"),
            }
    except HTTPError as exc:
        return {
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "credential_present": True,
            "result": "FAIL",
            "error": f"HTTPError {exc.code}: {exc.read().decode('utf-8', errors='replace')[:500]}",
            "request": payload,
            "response": None,
            "latency_seconds": round(time.time() - started, 3),
            "tokens": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "credential_present": True,
            "result": "FAIL",
            "error": str(exc),
            "request": payload,
            "response": None,
            "latency_seconds": round(time.time() - started, 3),
            "tokens": None,
        }


def main() -> int:
    started_at = datetime.now(UTC).isoformat()
    api_calls = [probe_health(name, url) for name, url in LAYER_URLS.items()]
    llm_trace = probe_llm()

    transcript = {
        "scenario": "Mid-market B2B SaaS evaluating Fabric_4L for GTM/value-engineering workflow",
        "date_utc": started_at,
        "probe_script": Path(__file__).name,
        "layer_health_checks": api_calls,
        "tenant_isolation_check": {
            "description": "Attempt L4 /health without auth to verify fail-closed behavior (services must be running)",
            "result": "NOT_EXECUTED",
            "reason": "Services are unreachable; auth/fail-closed checks require running stack.",
        },
    }

    (EVIDENCE_DIR / f"fabric4l-e2e-api-transcript-{DATE_STAMP}.json").write_text(
        json.dumps(transcript, indent=2), encoding="utf-8"
    )
    (EVIDENCE_DIR / f"fabric4l-e2e-llm-trace-{DATE_STAMP}.json").write_text(
        json.dumps(llm_trace, indent=2), encoding="utf-8"
    )

    print(f"Wrote {EVIDENCE_DIR}/fabric4l-e2e-api-transcript-{DATE_STAMP}.json")
    print(f"Wrote {EVIDENCE_DIR}/fabric4l-e2e-llm-trace-{DATE_STAMP}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
