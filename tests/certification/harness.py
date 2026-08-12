"""Certification harness: gateway entry, trace continuity, and artifact export.

Extends the shared live-service harness with the pieces the production-path
certification needs on top of per-layer calls:

- a gateway client (the canonical external boundary, decision D1),
- one ``trace_id`` propagated across every hop of the journey,
- a stage recorder that writes the machine-readable certification manifest
  and execution report after every stage, so artifacts survive a crash.

No mocks are used anywhere in this suite: every call targets a live service
and every assertion reads back through a real persistence boundary.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import httpx
import pytest

from tests.shared.live_harness import BackendValidationHarness, SeedIds

GATEWAY_URL = os.getenv("GATEWAY_API_URL", "http://localhost:8008").rstrip("/")
GATEWAY_HEALTH_PATHS = ("/health", "/v1/health", "/healthz")
CERT_HTTP_TIMEOUT = float(os.getenv("CERTIFICATION_HTTP_TIMEOUT", "10.0"))
ARTIFACT_DIR = Path(
    os.getenv("CERTIFICATION_ARTIFACT_DIR", "artifacts/certification")
)

# Gateway paths exactly as the frontend generates them: the browser calls
# /api/v1{segment}{path}; the dev proxy strips /api/v1, so the gateway sees
# /v1{segment}{path}. The certification journey must enter through these
# same paths (decision D1).
FRONTEND_SEGMENTS = {
    "l1": "/ingest",
    "l2": "/extract",
    "l3": "/graph",
    "l4": "/agents",
    "l5": "/truths",
    "l6": "/benchmarks",
}


def current_git_sha() -> str:
    try:
        return (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip()
        )
    except (subprocess.SubprocessError, OSError):
        return "unknown"


@dataclass
class StageResult:
    name: str
    status: str  # "passed" | "failed"
    detail: str
    started_at: str
    duration_ms: int


@dataclass
class CertificationRecorder:
    """Collects stage results and exports certification artifacts."""

    run_id: str
    trace_id: str
    git_sha: str
    stages: list[StageResult] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)

    @property
    def failed_stages(self) -> list[StageResult]:
        return [s for s in self.stages if s.status == "failed"]

    def record(self, result: StageResult) -> None:
        self.stages.append(result)
        self.export()

    def export(self) -> None:
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema_version": "1.0",
            "kind": "production-path-certification-manifest",
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "git_sha": self.git_sha,
            "generated_at": datetime.now(UTC).isoformat(),
            "scenario": "meridian-auto",
            "stages_total": len(self.stages),
            "stages_passed": len(self.stages) - len(self.failed_stages),
            "stages_failed": len(self.failed_stages),
            "certified": not self.failed_stages and bool(self.stages),
            "journey_context": self.context,
        }
        (ARTIFACT_DIR / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )
        report = {
            "schema_version": "1.0",
            "kind": "production-path-execution-report",
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "git_sha": self.git_sha,
            "stages": [
                {
                    "name": s.name,
                    "status": s.status,
                    "detail": s.detail,
                    "started_at": s.started_at,
                    "duration_ms": s.duration_ms,
                }
                for s in self.stages
            ],
        }
        (ARTIFACT_DIR / "execution-report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
        )


class CertificationHarness(BackendValidationHarness):
    """Live harness for the certification journey (gateway-first)."""

    def __init__(self, seed_ids: SeedIds, recorder: CertificationRecorder) -> None:
        super().__init__(seed_ids)
        self.cert_timeout = CERT_HTTP_TIMEOUT
        self.recorder = recorder

    @property
    def trace_headers(self) -> dict[str, str]:
        return {
            "X-Request-ID": f"cert-{self.recorder.run_id}-{uuid.uuid4().hex[:8]}",
            "X-Correlation-ID": self.recorder.trace_id,
            "X-Trace-ID": self.recorder.trace_id,
        }

    async def gateway_request(
        self,
        method: str,
        path: str,
        *,
        tenant_id: str | None = None,
        user_id: str | None = None,
        role: str = "super_admin",
        json_body: dict[str, Any] | None = None,
        expected: Iterable[int] = (200,),
    ) -> tuple[Any, httpx.Response]:
        """Call the canonical external boundary (gateway) with trace headers."""
        expected_set = set(expected)
        headers = self.headers(tenant_id=tenant_id, user_id=user_id, role=role)
        headers.update(self.trace_headers)
        async with httpx.AsyncClient(
            base_url=GATEWAY_URL, timeout=self.cert_timeout, follow_redirects=False
        ) as client:
            try:
                response = await client.request(
                    method, path, headers=headers, json=json_body
                )
            except httpx.HTTPError as exc:
                pytest.fail(
                    f"GATEWAY {method} {path} is unreachable at {GATEWAY_URL}; "
                    f"certification requires the live gateway. Error: {exc!r}"
                )
        assert response.status_code in expected_set, (
            f"GATEWAY {method} {path} expected one of {sorted(expected_set)}, "
            f"got {response.status_code}: {response.text[:1000]}"
        )
        if response.content and "json" in response.headers.get("content-type", ""):
            return response.json(), response
        return response.text if response.content else {}, response

    async def frontend_path_request(
        self,
        layer: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> tuple[Any, httpx.Response]:
        """Call the gateway using the exact route shape the frontend generates.

        ``apiGet("l4", "/hypotheses/generate")`` becomes ``/v1/agents/...``
        at the gateway after the dev proxy strips ``/api/v1`` — this method
        reproduces that same resolved path.
        """
        segment = FRONTEND_SEGMENTS[layer]
        return await self.gateway_request(method, f"/v1{segment}{path}", **kwargs)

    async def gateway_healthy(self) -> tuple[str, Any]:
        last_error: AssertionError | None = None
        for path in GATEWAY_HEALTH_PATHS:
            try:
                body, _ = await self.gateway_request("GET", path, expected=(200, 204))
                return path, body
            except AssertionError as exc:
                last_error = exc
        raise AssertionError(f"No gateway health endpoint passed: {last_error}")

    async def stage(self, name: str, coro: Any) -> Any:
        """Run one journey stage, recording pass/fail into the manifest.

        Stage failures are recorded and re-raised as AssertionErrors so the
        journey runner can continue to independent stages and report one
        aggregated failure list at the end.
        """
        started = datetime.now(UTC)
        monotonic = time.monotonic()
        try:
            result = await coro
        except Exception as exc:  # noqa: BLE001 - record any stage failure
            detail = f"{type(exc).__name__}: {str(exc)[:1500]}"
            self.recorder.record(
                StageResult(
                    name=name,
                    status="failed",
                    detail=detail,
                    started_at=started.isoformat(),
                    duration_ms=int((time.monotonic() - monotonic) * 1000),
                )
            )
            raise AssertionError(detail) from exc
        self.recorder.record(
            StageResult(
                name=name,
                status="passed",
                detail="ok",
                started_at=started.isoformat(),
                duration_ms=int((time.monotonic() - monotonic) * 1000),
            )
        )
        return result
