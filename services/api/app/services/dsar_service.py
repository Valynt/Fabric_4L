from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta

from prometheus_client import Counter, Histogram

from app.core.database import db
from app.core.metrics import registry
from app.models.schemas import DSARPackage, DSARRequestCreate, DSARRequestRecord

from app.core.config import get_settings as _get_settings

DSAR_QUERY_LATENCY_SECONDS = Histogram(
    "fabric_api_dsar_query_duration_seconds",
    "Latency for DSAR repository operations executed from async service paths.",
    ("operation",),
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=registry,
)

DSAR_EVENT_LOOP_BLOCKING_RISK_TOTAL = Counter(
    "fabric_api_dsar_event_loop_blocking_risk_total",
    "Count of DSAR sync repository operations offloaded to an executor as interim mitigation.",
    ("operation",),
    registry=registry,
)


def _get_signing_key() -> bytes:
    return _get_settings().secret_key.encode()


def _now() -> datetime:
    return datetime.now(UTC)


async def _run_blocking_repo_call(operation: str, fn, /, *args, **kwargs):
    """Run sync repo/database calls off the event loop until async repositories are available.

    TODO: Remove executor offloading once DSAR repositories expose native async APIs.
    """

    DSAR_EVENT_LOOP_BLOCKING_RISK_TOTAL.labels(operation).inc()
    start = time.perf_counter()
    result = await asyncio.get_running_loop().run_in_executor(None, lambda: fn(*args, **kwargs))
    DSAR_QUERY_LATENCY_SECONDS.labels(operation).observe(time.perf_counter() - start)
    return result


async def register_request(payload: DSARRequestCreate, *, tenant_id: str, requester_user_id: str) -> DSARRequestRecord:
    request_id = str(uuid.uuid4())
    requested_at = _now()
    record = DSARRequestRecord(
        id=request_id,
        tenant_id=tenant_id,
        requester_user_id=requester_user_id,
        subject_identity=payload.subject_identity,
        scope=payload.scope,
        legal_basis=payload.legal_basis,
        requester_channel=payload.requester_channel,
        tenant_context=payload.tenant_context,
        data_categories=sorted(set(payload.scope)),
        sla_deadline_at=(requested_at + timedelta(days=30)).isoformat(),
        requested_at=requested_at.isoformat(),
    )
    await _run_blocking_repo_call("dsar_requests.insert", db.dsar_requests.insert, record.id, record)
    return record


async def _tenant_export_payload(*, tenant_id: str) -> dict:
    accounts = await _run_blocking_repo_call("accounts.list", db.accounts.list, tenant_id=tenant_id)
    evidence = await _run_blocking_repo_call("evidence.list", db.evidence.list, tenant_id=tenant_id)
    hypotheses = await _run_blocking_repo_call("hypotheses.list", db.hypotheses.list, tenant_id=tenant_id)
    return {
        "accounts": [a.model_dump(mode="json") for a in accounts],
        "evidence": [e.model_dump(mode="json") for e in evidence],
        "hypotheses": [h.model_dump(mode="json") for h in hypotheses],
    }


async def launch_export_pipeline(record: DSARRequestRecord) -> DSARPackage:
    await _run_blocking_repo_call("dsar_requests.update_status_exporting", db.dsar_requests.update, record.id, tenant_id=record.tenant_id, status="exporting")
    payload = await _tenant_export_payload(tenant_id=record.tenant_id)
    package_id = str(uuid.uuid4())
    package = DSARPackage(
        id=package_id,
        dsar_request_id=record.id,
        tenant_id=record.tenant_id,
        requester_user_id=record.requester_user_id,
        export_payload=payload,
        expires_at=(_now() + timedelta(hours=1)).isoformat(),
    )
    await _run_blocking_repo_call("dsar_packages.insert", db.dsar_packages.insert, package.id, package)
    await _run_blocking_repo_call("dsar_requests.update_package", db.dsar_requests.update, record.id, tenant_id=record.tenant_id, package_id=package.id, status="reconciling")
    return package


async def reconcile_package(record: DSARRequestRecord) -> DSARRequestRecord:
    pkg = await _run_blocking_repo_call("dsar_packages.get", db.dsar_packages.get, record.package_id, tenant_id=record.tenant_id) if record.package_id else None
    complete = bool(pkg and any(pkg.export_payload.get(k) for k in ("accounts", "evidence", "hypotheses")))
    if not complete:
        raise ValueError("DSAR package incomplete")
    await _run_blocking_repo_call("dsar_packages.update", db.dsar_packages.update, pkg.id, tenant_id=record.tenant_id, completeness_verified=True)
    updated = await _run_blocking_repo_call("dsar_requests.complete", db.dsar_requests.update, record.id, tenant_id=record.tenant_id, status="complete", completed_at=_now().isoformat(), completion_evidence=["completeness_verified"])
    return updated


async def maybe_escalate(record: DSARRequestRecord) -> DSARRequestRecord:
    if record.status not in ("complete", "escalated") and _now() > datetime.fromisoformat(record.sla_deadline_at):
        return await _run_blocking_repo_call("dsar_requests.escalate", db.dsar_requests.update, record.id, tenant_id=record.tenant_id, status="escalated", escalated_at=_now().isoformat())
    return record


def _sign_token(package_id: str, requester_user_id: str, expires_at: str) -> str:
    nonce = secrets.token_hex(6)
    msg = f"{package_id}:{requester_user_id}:{expires_at}:{nonce}".encode()
    sig = hmac.new(_get_signing_key(), msg, hashlib.sha256).hexdigest()
    return f"{package_id}.{requester_user_id}.{expires_at}.{nonce}.{sig}"


def issue_download_url(package: DSARPackage) -> str:
    token = _sign_token(package.id, package.requester_user_id, package.expires_at)
    return f"/v1/privacy/dsar/packages/{package.id}/download?token={token}"


def validate_download_access(package: DSARPackage, *, requester_user_id: str, token: str) -> None:
    if package.requester_user_id != requester_user_id:
        raise PermissionError("requester mismatch")
    if _now() > datetime.fromisoformat(package.expires_at):
        raise PermissionError("download url expired")
    expected = _sign_token(package.id, package.requester_user_id, package.expires_at).rsplit('.',1)[-1]
    provided_sig = token.rsplit('.',1)[-1]
    if not hmac.compare_digest(expected, provided_sig):
        raise PermissionError("invalid token")


def serialize_package(package: DSARPackage) -> bytes:
    return json.dumps(package.export_payload, sort_keys=True).encode()
