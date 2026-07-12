import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.core.database import db
from app.main import app
from app.models.schemas import DSARRequestCreate
from app.routers.privacy import (
    _resolve_idempotent_dsar_response,
    _store_idempotent_dsar_response,
)
from app.services import dsar_service

from .conftest import TENANT_ALPHA, TENANT_BETA, auth_headers


def test_dsar_endpoint_authorization_and_tenant_scope():
    client = TestClient(app)
    payload = {"subject_identity": {"email": "a@example.com"}, "scope": ["accounts"], "legal_basis": "gdpr_art_15", "requester_channel": "portal", "tenant_context": {"region": "us"}}
    assert client.post('/v1/privacy/dsar', json=payload).status_code == 401
    res = client.post('/v1/privacy/dsar', json=payload, headers=auth_headers(TENANT_ALPHA, 'user-a'))
    assert res.status_code == 202
    req_id = res.json()['request']['id']
    assert client.get(f'/v1/privacy/dsar/{req_id}', headers=auth_headers(TENANT_BETA, 'user-b')).status_code == 404


def test_sla_deadline_and_escalation_path():
    req = asyncio.run(dsar_service.register_request(DSARRequestCreate(subject_identity={"email": "x@y.com"}), tenant_id=TENANT_ALPHA, requester_user_id='user-a'))
    deadline = datetime.fromisoformat(req.sla_deadline_at)
    requested = datetime.fromisoformat(req.requested_at)
    assert deadline - requested == timedelta(days=30)
    asyncio.run(db.dsar_requests.update(req.id, tenant_id=TENANT_ALPHA, sla_deadline_at=(datetime.now(UTC)-timedelta(days=1)).isoformat()))
    escalated = asyncio.run(dsar_service.maybe_escalate(asyncio.run(db.dsar_requests.get(req.id, tenant_id=TENANT_ALPHA))))
    assert escalated.status == 'escalated'
    assert escalated.escalated_at is not None


async def test_download_url_expiry_and_access_control():
    req = await dsar_service.register_request(DSARRequestCreate(subject_identity={"email": "x@y.com"}), tenant_id=TENANT_ALPHA, requester_user_id='user-a')
    pkg = await dsar_service.launch_export_pipeline(req)
    token_url = dsar_service.issue_download_url(pkg)
    token = token_url.split('token=')[1]
    dsar_service.validate_download_access(pkg, requester_user_id='user-a', token=token)
    try:
        dsar_service.validate_download_access(pkg, requester_user_id='user-b', token=token)
        assert False
    except PermissionError:
        pass
    await db.dsar_packages.update(pkg.id, tenant_id=TENANT_ALPHA, expires_at=(datetime.now(UTC)-timedelta(seconds=1)).isoformat())
    expired = await db.dsar_packages.get(pkg.id, tenant_id=TENANT_ALPHA)
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
    pa = asyncio.run(db.dsar_packages.get(ra['request']['package_id'], tenant_id=TENANT_ALPHA))
    pb = asyncio.run(db.dsar_packages.get(rb['request']['package_id'], tenant_id=TENANT_BETA))
    assert all(item['tenant_id'] == TENANT_ALPHA for item in pa.export_payload['accounts'])
    assert all(item['tenant_id'] == TENANT_BETA for item in pb.export_payload['accounts'])


def test_async_dsar_flow_uses_async_repository_calls():
    req = asyncio.run(dsar_service.register_request(DSARRequestCreate(subject_identity={"email": "bridge@y.com"}), tenant_id=TENANT_ALPHA, requester_user_id='user-a'))
    pkg = asyncio.run(dsar_service.launch_export_pipeline(req))
    refreshed = asyncio.run(db.dsar_requests.get(req.id, tenant_id=TENANT_ALPHA))
    completed = asyncio.run(dsar_service.reconcile_package(refreshed))

    assert pkg.dsar_request_id == req.id
    assert completed.status == "complete"


def test_dsar_create_persists_request_before_response():
    client = TestClient(app)
    payload = {"subject_identity": {"email": "persisted@example.com"}}
    response = client.post('/v1/privacy/dsar', json=payload, headers=auth_headers(TENANT_ALPHA, 'user-a'))
    assert response.status_code == 202
    request_id = response.json()["request"]["id"]
    persisted = asyncio.run(db.dsar_requests.get(request_id, tenant_id=TENANT_ALPHA))
    assert persisted is not None
    assert persisted.tenant_id == TENANT_ALPHA


def test_dsar_reconciliation_error_mapping_contract(monkeypatch):
    client = TestClient(app)

    async def _raise(_record):
        raise ValueError("forced")

    monkeypatch.setattr(dsar_service, "reconcile_package", _raise)
    payload = {"subject_identity": {"email": "x@example.com"}, "scope": ["accounts"]}
    response = client.post("/v1/privacy/dsar", json=payload, headers=auth_headers(TENANT_ALPHA, "user-a"))
    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Invalid DSAR request"


def test_tenant_export_payload_runs_table_queries_concurrently():
    """Verify _tenant_export_payload calls the three tenant-scoped tables concurrently."""
    calls: dict[str, bool] = {}

    def _slow_list(tenant_id: str, table_name: str):
        calls[table_name] = True
        __import__("time").sleep(0.05)
        return []

    monkeypatch_targets = {
        "accounts": dsar_service.db.accounts,
        "evidence": dsar_service.db.evidence,
        "hypotheses": dsar_service.db.hypotheses,
    }
    for name, table in monkeypatch_targets.items():
        table.list = lambda tenant_id, name=name: _slow_list(tenant_id, name)

    async def _run():
        start = asyncio.get_running_loop().time()
        await dsar_service._tenant_export_payload(tenant_id=TENANT_ALPHA)
        return asyncio.get_running_loop().time() - start

    elapsed = asyncio.run(_run())
    assert "accounts" in calls
    assert "evidence" in calls
    assert "hypotheses" in calls
    # Three ~50ms blocking calls run concurrently; sequential would be >150ms.
    assert elapsed < 0.15


def test_dsar_service_responsive_under_moderate_parallel_load(monkeypatch):
    async def _slow_export(*, tenant_id: str):
        await asyncio.sleep(0.01)
        return {"accounts": [], "evidence": [], "hypotheses": []}

    monkeypatch.setattr(dsar_service, "_tenant_export_payload", _slow_export)

    async def _submit():
        loop = asyncio.get_running_loop()
        started = loop.time()
        payload = DSARRequestCreate(subject_identity={"email": "parallel@y.com"})
        await asyncio.gather(
            *[
                dsar_service.register_request(
                    payload,
                    tenant_id=TENANT_ALPHA,
                    requester_user_id=f"user-{i}",
                )
                for i in range(12)
            ]
        )
        return loop.time() - started

    elapsed = asyncio.run(_submit())
    assert elapsed < 1.0


def test_dsar_create_is_idempotent():
    """Retrying a DSAR with the same Idempotency-Key returns the same request."""
    client = TestClient(app)
    payload = {"subject_identity": {"email": "idempotent@example.com"}, "scope": ["accounts"]}
    idem_key = "dsar-idem-001"

    r1 = client.post(
        "/v1/privacy/dsar",
        json=payload,
        headers={**auth_headers(TENANT_ALPHA, "user-a"), "Idempotency-Key": idem_key},
    )
    assert r1.status_code == 202
    request_id_1 = r1.json()["request"]["id"]

    r2 = client.post(
        "/v1/privacy/dsar",
        json=payload,
        headers={**auth_headers(TENANT_ALPHA, "user-a"), "Idempotency-Key": idem_key},
    )
    assert r2.status_code == 202
    request_id_2 = r2.json()["request"]["id"]
    assert request_id_1 == request_id_2


def test_dsar_idempotency_rejects_different_payload():
    """Same Idempotency-Key with a different payload returns 409."""
    client = TestClient(app)
    idem_key = "dsar-idem-002"

    r1 = client.post(
        "/v1/privacy/dsar",
        json={"subject_identity": {"email": "first@example.com"}, "scope": ["accounts"]},
        headers={**auth_headers(TENANT_ALPHA, "user-a"), "Idempotency-Key": idem_key},
    )
    assert r1.status_code == 202

    r2 = client.post(
        "/v1/privacy/dsar",
        json={"subject_identity": {"email": "second@example.com"}, "scope": ["accounts"]},
        headers={**auth_headers(TENANT_ALPHA, "user-a"), "Idempotency-Key": idem_key},
    )
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "CONFLICT"
    assert "different payload" in r2.json()["error"]["message"].lower()


def test_dsar_idempotency_is_tenant_scoped():
    """Same key in different tenants creates independent DSARs."""
    client = TestClient(app)
    payload = {"subject_identity": {"email": "tenant-scoped@example.com"}, "scope": ["accounts"]}
    idem_key = "dsar-idem-003"

    r_a = client.post(
        "/v1/privacy/dsar",
        json=payload,
        headers={**auth_headers(TENANT_ALPHA, "user-a"), "Idempotency-Key": idem_key},
    )
    r_b = client.post(
        "/v1/privacy/dsar",
        json=payload,
        headers={**auth_headers(TENANT_BETA, "user-b"), "Idempotency-Key": idem_key},
    )
    assert r_a.status_code == 202
    assert r_b.status_code == 202
    assert r_a.json()["request"]["id"] != r_b.json()["request"]["id"]


class TestResolveIdempotentDsarResponse:
    """Unit tests for the idempotency helper isolated from the live endpoint."""

    def _make_request(self, service=None):
        return SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(idempotency_service=service)),
        )

    def _auth(self):
        return SimpleNamespace(sub="user-a")

    def test_returns_none_when_no_service_configured(self):
        request = self._make_request(service=None)
        payload = DSARRequestCreate(subject_identity={"email": "none@example.com"})
        result = asyncio.run(
            _resolve_idempotent_dsar_response(
                request=request,
                payload=payload,
                idempotency_key="key",
                tenant_id=TENANT_ALPHA,
                auth=self._auth(),
            )
        )
        assert result == (None, None, None)

    def test_returns_cached_response_on_replay(self):
        cached_body = {"request": {"id": "cached-id"}}
        service = Mock()
        service.check_replay.return_value = SimpleNamespace(body=cached_body)
        request = self._make_request(service=service)
        payload = DSARRequestCreate(subject_identity={"email": "replay@example.com"})

        body, idem_request, returned_service = asyncio.run(
            _resolve_idempotent_dsar_response(
                request=request,
                payload=payload,
                idempotency_key="replay-key",
                tenant_id=TENANT_ALPHA,
                auth=self._auth(),
            )
        )

        assert body == cached_body
        assert returned_service is service
        assert idem_request is not None
        service.check_replay.assert_called_once_with(idem_request, tenant_id=TENANT_ALPHA)

    def test_raises_409_on_idempotency_conflict(self):
        from value_fabric.shared.idempotency import IdempotencyConflictError

        service = Mock()
        service.check_replay.side_effect = IdempotencyConflictError("payload mismatch")
        request = self._make_request(service=service)
        payload = DSARRequestCreate(subject_identity={"email": "conflict@example.com"})

        try:
            asyncio.run(
                _resolve_idempotent_dsar_response(
                    request=request,
                    payload=payload,
                    idempotency_key="conflict-key",
                    tenant_id=TENANT_ALPHA,
                    auth=self._auth(),
                )
            )
        except Exception as exc:
            assert exc.status_code == 409
            assert exc.detail["error"] == "idempotency_conflict"
        else:
            raise AssertionError("Expected HTTPException to be raised")


class TestStoreIdempotentDsarResponse:
    """Unit tests for the idempotency storage helper."""

    def _auth(self):
        return SimpleNamespace(sub="user-a")

    def test_persists_record_through_service(self):
        service = Mock()
        idem_request = Mock()
        response = {"request": {"id": "new-id"}}

        asyncio.run(
            _store_idempotent_dsar_response(
                service=service,
                idem_request=idem_request,
                tenant_id=TENANT_ALPHA,
                auth=self._auth(),
                response=response,
            )
        )

        service.store_response.assert_called_once()
        args, kwargs = service.store_response.call_args
        assert args[0] is idem_request
        assert args[1].status_code == 202
        assert args[1].body == response
        assert kwargs == {"tenant_id": TENANT_ALPHA}

    def test_swallows_storage_exception(self):
        service = Mock()
        service.store_response.side_effect = RuntimeError("cache down")

        asyncio.run(
            _store_idempotent_dsar_response(
                service=service,
                idem_request=Mock(),
                tenant_id=TENANT_ALPHA,
                auth=self._auth(),
                response={"request": {"id": "new-id"}},
            )
        )

        service.store_response.assert_called_once()
