import asyncio
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.core.database import db
from app.services import dsar_service
from app.models.schemas import DSARRequestCreate
from .conftest import TENANT_ALPHA, TENANT_BETA, auth_headers


def test_dsar_endpoint_authorization_and_tenant_scope():
    client = TestClient(app)
    payload = {"subject_identity": {"email": "a@example.com"}, "scope": ["accounts"], "legal_basis": "gdpr_art_15", "requester_channel": "portal", "tenant_context": {"region": "us"}}
    assert client.post('/v1/privacy/dsar', json=payload).status_code == 403
    res = client.post('/v1/privacy/dsar', json=payload, headers=auth_headers(TENANT_ALPHA, 'user-a'))
    assert res.status_code == 202
    req_id = res.json()['request']['id']
    assert client.get(f'/v1/privacy/dsar/{req_id}', headers=auth_headers(TENANT_BETA, 'user-b')).status_code == 404


def test_sla_deadline_and_escalation_path():
    req = asyncio.run(dsar_service.register_request(DSARRequestCreate(subject_identity={"email": "x@y.com"}), tenant_id=TENANT_ALPHA, requester_user_id='user-a'))
    deadline = datetime.fromisoformat(req.sla_deadline_at)
    requested = datetime.fromisoformat(req.requested_at)
    assert deadline - requested == timedelta(days=30)
    db.dsar_requests.update(req.id, tenant_id=TENANT_ALPHA, sla_deadline_at=(datetime.now(UTC)-timedelta(days=1)).isoformat())
    escalated = asyncio.run(dsar_service.maybe_escalate(db.dsar_requests.get(req.id, tenant_id=TENANT_ALPHA)))
    assert escalated.status == 'escalated'
    assert escalated.escalated_at is not None


def test_download_url_expiry_and_access_control():
    req = asyncio.run(dsar_service.register_request(DSARRequestCreate(subject_identity={"email": "x@y.com"}), tenant_id=TENANT_ALPHA, requester_user_id='user-a'))
    pkg = asyncio.run(dsar_service.launch_export_pipeline(req))
    token_url = dsar_service.issue_download_url(pkg)
    token = token_url.split('token=')[1]
    dsar_service.validate_download_access(pkg, requester_user_id='user-a', token=token)
    try:
        dsar_service.validate_download_access(pkg, requester_user_id='user-b', token=token)
        assert False
    except PermissionError:
        pass
    db.dsar_packages.update(pkg.id, tenant_id=TENANT_ALPHA, expires_at=(datetime.now(UTC)-timedelta(seconds=1)).isoformat())
    expired = db.dsar_packages.get(pkg.id, tenant_id=TENANT_ALPHA)
    try:
        dsar_service.validate_download_access(expired, requester_user_id='user-a', token=token)
        assert False
    except PermissionError:
        pass


def test_cross_tenant_data_isolation_in_export_payload():
    client = TestClient(app)
    payload = {"subject_identity": {"email": "a@example.com"}}
    ra = client.post('/v1/privacy/dsar', json=payload, headers=auth_headers(TENANT_ALPHA, 'user-a')).json()
    rb = client.post('/v1/privacy/dsar', json=payload, headers=auth_headers(TENANT_BETA, 'user-b')).json()
    pa = db.dsar_packages.get(ra['request']['package_id'], tenant_id=TENANT_ALPHA)
    pb = db.dsar_packages.get(rb['request']['package_id'], tenant_id=TENANT_BETA)
    assert all(item['tenant_id'] == TENANT_ALPHA for item in pa.export_payload['accounts'])
    assert all(item['tenant_id'] == TENANT_BETA for item in pb.export_payload['accounts'])


def test_async_dsar_flow_uses_executor_bridge(monkeypatch):
    called = {"used": False}

    async def _spy(operation, fn, /, *args, **kwargs):
        called["used"] = True
        return fn(*args, **kwargs)

    monkeypatch.setattr(dsar_service, "_run_blocking_repo_call", _spy)

    req = asyncio.run(dsar_service.register_request(DSARRequestCreate(subject_identity={"email": "bridge@y.com"}), tenant_id=TENANT_ALPHA, requester_user_id='user-a'))
    pkg = asyncio.run(dsar_service.launch_export_pipeline(req))
    refreshed = db.dsar_requests.get(req.id, tenant_id=TENANT_ALPHA)
    completed = asyncio.run(dsar_service.reconcile_package(refreshed))

    assert called["used"] is True
    assert pkg.dsar_request_id == req.id
    assert completed.status == "complete"


def test_dsar_reconciliation_error_mapping_contract(monkeypatch):
    client = TestClient(app)

    async def _raise(_record):
        raise ValueError("forced")

    monkeypatch.setattr(dsar_service, "reconcile_package", _raise)
    payload = {"subject_identity": {"email": "x@example.com"}, "scope": ["accounts"]}
    response = client.post("/v1/privacy/dsar", json=payload, headers=auth_headers(TENANT_ALPHA, "user-a"))
    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid DSAR request"
