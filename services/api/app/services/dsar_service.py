from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from app.core.database import db
from app.models.schemas import DSARPackage, DSARRequestCreate, DSARRequestRecord

from app.core.config import get_settings as _get_settings

def _get_signing_key() -> bytes:
    return _get_settings().secret_key.encode()


def _now() -> datetime:
    return datetime.now(UTC)


def register_request(payload: DSARRequestCreate, *, tenant_id: str, requester_user_id: str) -> DSARRequestRecord:
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
    db.dsar_requests.insert(record.id, record)
    return record


async def _tenant_export_payload(*, tenant_id: str) -> dict:
    def _build() -> dict:
        return {
            "accounts": [a.model_dump(mode="json") for a in db.accounts.list(tenant_id=tenant_id)],
            "evidence": [e.model_dump(mode="json") for e in db.evidence.list(tenant_id=tenant_id)],
            "hypotheses": [h.model_dump(mode="json") for h in db.hypotheses.list(tenant_id=tenant_id)],
        }
    return await asyncio.to_thread(_build)


async def launch_export_pipeline(record: DSARRequestRecord) -> DSARPackage:
    db.dsar_requests.update(record.id, tenant_id=record.tenant_id, status="exporting")
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
    db.dsar_packages.insert(package.id, package)
    db.dsar_requests.update(record.id, tenant_id=record.tenant_id, package_id=package.id, status="reconciling")
    return package


def reconcile_package(record: DSARRequestRecord) -> DSARRequestRecord:
    pkg = db.dsar_packages.get(record.package_id, tenant_id=record.tenant_id) if record.package_id else None
    complete = bool(pkg and any(pkg.export_payload.get(k) for k in ("accounts", "evidence", "hypotheses")))
    if not complete:
        raise ValueError("DSAR package incomplete")
    db.dsar_packages.update(pkg.id, tenant_id=record.tenant_id, completeness_verified=True)
    updated = db.dsar_requests.update(record.id, tenant_id=record.tenant_id, status="complete", completed_at=_now().isoformat(), completion_evidence=["completeness_verified"])
    return updated


def maybe_escalate(record: DSARRequestRecord) -> DSARRequestRecord:
    if record.status not in ("complete", "escalated") and _now() > datetime.fromisoformat(record.sla_deadline_at):
        return db.dsar_requests.update(record.id, tenant_id=record.tenant_id, status="escalated", escalated_at=_now().isoformat())
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
