import pytest
from fastapi import BackgroundTasks

from layer2_extraction.api import main
from layer2_extraction.models.extraction_api import ExtractionRequest
from value_fabric.shared.error_handling.exceptions import AuthorizationError


class _Ctx:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        self.auth_source = "jwt"

    def is_auth_source_valid(self):
        return True


@pytest.mark.asyncio
async def test_extract_rejects_missing_tenant_before_job_write(monkeypatch):
    called = False

    async def _forbidden_set(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("job_store.set should not be called")

    monkeypatch.setattr(main.job_store, "set", _forbidden_set)

    req = ExtractionRequest(source_url="https://example.com", markdown_content="# demo")
    with pytest.raises(AuthorizationError) as exc:
        await main.extract(req, BackgroundTasks(), _Ctx(None))

    assert exc.value.status_code == 403
    assert exc.value.details["code"] == "tenant_context_required"
    assert called is False


@pytest.mark.asyncio
async def test_run_extraction_rejects_missing_tenant_before_any_persistence(monkeypatch):
    exists_called = False
    quarantine_called = False

    async def _exists(*args, **kwargs):
        nonlocal exists_called
        exists_called = True
        return False

    async def _quarantine_put(*args, **kwargs):
        nonlocal quarantine_called
        quarantine_called = True
        raise AssertionError("quarantine_store.put should not be called")

    monkeypatch.setattr(main.job_store, "exists", _exists)
    monkeypatch.setattr(main.quarantine_store, "put", _quarantine_put)

    with pytest.raises(AuthorizationError) as exc:
        await main.run_extraction(
            job_id="job-1",
            source_url="https://example.com",
            content="hello",
            config={"model_version": "m", "schema_version": "s", "prompt_version": "p"},
        )

    assert exc.value.status_code == 403
    assert exc.value.details["code"] == "tenant_context_required"
    assert exists_called is False
    assert quarantine_called is False


@pytest.mark.asyncio
async def test_extract_and_ingest_rejects_missing_tenant_before_job_or_idempotency_write(monkeypatch):
    set_called = False
    idem_called = False

    async def _set(*args, **kwargs):
        nonlocal set_called
        set_called = True
        raise AssertionError("job_store.set should not be called")

    async def _set_idem(*args, **kwargs):
        nonlocal idem_called
        idem_called = True
        raise AssertionError("idempotency mapping should not be written")

    monkeypatch.setattr(main.job_store, "set", _set)
    monkeypatch.setattr(main.job_store, "set_job_id_for_idempotency_key", _set_idem)

    req = ExtractionRequest(source_url="https://example.com", markdown_content="# demo")
    with pytest.raises(AuthorizationError) as exc:
        await main.extract_and_ingest(req, BackgroundTasks(), _Ctx(""))

    assert exc.value.status_code == 403
    assert exc.value.details["code"] == "tenant_context_required"
    assert set_called is False
    assert idem_called is False
