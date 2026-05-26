from uuid import uuid4

from value_fabric.layer1.shared.models import JobStatus, ScrapingJob


def test_execute_target_replays_same_tenant_idempotency_key(client, db, org_id, make_target, monkeypatch):
    target = make_target(org_id)
    monkeypatch.setattr("value_fabric.layer1.api.app_monolith.process_scraping_job.delay", lambda *a, **k: None)

    payload = {"priority": 5, "idempotency_key": "exec-dup-1"}
    r1 = client.post(f"/api/v1/ingestion/targets/{target.id}/execute", json=payload)
    r2 = client.post(f"/api/v1/ingestion/targets/{target.id}/execute", json=payload)

    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.json()["job_id"] == r2.json()["job_id"]
    assert db.query(ScrapingJob).filter(ScrapingJob.tenant_id == org_id).count() == 1


def test_retry_job_replays_same_tenant_with_header(client, db, org_id, user_id, make_target, monkeypatch):
    target = make_target(org_id)
    failed_job = ScrapingJob(
        tenant_id=org_id,
        target_id=target.id,
        created_by=user_id,
        configuration={},
        status=JobStatus.FAILED.value,
    )
    db.add(failed_job)
    db.commit()
    db.refresh(failed_job)

    monkeypatch.setattr("value_fabric.layer1.api.app_monolith.process_scraping_job.delay", lambda *a, **k: None)

    r1 = client.post(f"/api/v1/ingestion/jobs/{failed_job.id}/retry", json={}, headers={"Idempotency-Key": "retry-dup-1"})
    r2 = client.post(f"/api/v1/ingestion/jobs/{failed_job.id}/retry", json={}, headers={"Idempotency-Key": "retry-dup-1"})

    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.json()["new_job_id"] == r2.json()["new_job_id"]
