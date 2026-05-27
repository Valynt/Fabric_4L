from layer2_extraction.integration.quarantine_store import InMemoryQuarantineStore, QuarantineRecord


import pytest


@pytest.mark.asyncio
async def test_quarantine_records_are_traceable_and_listable_by_tenant():
    store = InMemoryQuarantineStore()
    await store.put(
        QuarantineRecord(
            quarantine_id="q-1",
            job_id="job-1",
            tenant_id="tenant-a",
            source_url="https://example.com",
            source_hash="h1",
            model_version="gpt-4o",
            schema_version="v1",
            prompt_template_version="entity_extraction_v1+relationship_extraction_v1",
            payload_json='{"bad":true}',
            validation_errors=["schema mismatch"],
        )
    )
    await store.put(
        QuarantineRecord(
            quarantine_id="q-2",
            job_id="job-2",
            tenant_id="tenant-b",
            source_url="https://example.com/2",
            source_hash="h2",
            model_version="gpt-4o",
            schema_version="v1",
            prompt_template_version="entity_extraction_v1+relationship_extraction_v1",
            payload_json='{"bad":true}',
            validation_errors=["schema mismatch 2"],
        )
    )

    row = await store.get_by_job(tenant_id="tenant-a", job_id="job-1")
    assert row is not None
    assert row.validation_errors == ["schema mismatch"]
    assert await store.get_by_job(tenant_id="tenant-a", job_id="job-2") is None

    listed = await store.list(tenant_id="tenant-a")
    assert [r.job_id for r in listed] == ["job-1"]
