from uuid import UUID, uuid4

from value_fabric.layer1.api import app_monolith as api
from value_fabric.layer1.shared.models import RawContent


def _assert_reason_code(response, expected: str) -> None:
    body = response.json()
    if "detail" in body and isinstance(body["detail"], dict):
        assert body["detail"].get("reason_code") == expected
        return
    assert expected in body.get("message", "")


def test_upload_accepts_file_and_persists_sanitized_binary_path(
    client, make_target, org_id, tmp_path, monkeypatch, db
):
    async def _scan_ok(**_kwargs):
        return True, "ok"

    target = make_target(org_id)
    monkeypatch.setenv("L1_UPLOAD_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr(api.process_scraping_job, "delay", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(api.malware_scanner_adapter, "scan", _scan_ok)

    response = client.post(
        "/api/v1/ingestion/uploads",
        data={"target_id": str(target.id)},
        files={"file": ("../../evil.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["reason_code"] == "UPLOAD_ACCEPTED"

    raw_content = db.query(RawContent).filter(RawContent.id == UUID(body["raw_content_id"])).one()
    assert "evil.txt" in raw_content.storage_binary_path
    assert ".." not in raw_content.storage_binary_path
    assert str(tmp_path) in raw_content.storage_binary_path


def test_upload_rejects_unsupported_mime(client, make_target, org_id):
    target = make_target(org_id)

    response = client.post(
        "/api/v1/ingestion/uploads",
        data={"target_id": str(target.id)},
        files={"file": ("payload.exe", b"malicious", "application/x-msdownload")},
    )

    assert response.status_code == 415
    _assert_reason_code(response, "UNSUPPORTED_MEDIA_TYPE")


def test_upload_rejects_oversized_file(client, make_target, org_id, monkeypatch):
    target = make_target(org_id)
    monkeypatch.setattr(api, "MAX_UPLOAD_FILE_SIZE_BYTES", 1)

    response = client.post(
        "/api/v1/ingestion/uploads",
        data={"target_id": str(target.id)},
        files={"file": ("big.txt", b"ab", "text/plain")},
    )

    assert response.status_code == 413
    _assert_reason_code(response, "FILE_TOO_LARGE")


def test_upload_rejects_malware_scan_failures(client, make_target, org_id, monkeypatch):
    async def _scan_fail(**_kwargs):
        return False, "infected"

    target = make_target(org_id)
    monkeypatch.setattr(api.malware_scanner_adapter, "scan", _scan_fail)

    response = client.post(
        "/api/v1/ingestion/uploads",
        data={"target_id": str(target.id)},
        files={"file": ("bad.txt", b"virus", "text/plain")},
    )

    assert response.status_code == 422
    _assert_reason_code(response, "MALWARE_SCAN_FAILED")


def test_upload_rejects_unknown_target(client, monkeypatch):
    async def _scan_ok(**_kwargs):
        return True, "ok"

    monkeypatch.setattr(api.process_scraping_job, "delay", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(api.malware_scanner_adapter, "scan", _scan_ok)

    response = client.post(
        "/api/v1/ingestion/uploads",
        data={"target_id": str(uuid4())},
        files={"file": ("ok.txt", b"safe", "text/plain")},
    )

    assert response.status_code == 404
    _assert_reason_code(response, "TARGET_NOT_FOUND")
