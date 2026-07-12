"""Soft-delete lifecycle contract tests."""

from datetime import UTC, datetime, timezone

ACTIVE_QUERY_STATES = {"active", "pending", "suspended"}


def _soft_delete(record: dict, *, actor_id: str, request_id: str) -> dict:
    deleted = dict(record)
    deleted.update(
        {
            "status": "deleted",
            "deleted_at": datetime(2026, 6, 4, tzinfo=UTC).isoformat().replace("+00:00", "Z"),
            "deleted_by": actor_id,
            "deletion_request_id": request_id,
        }
    )
    return deleted


def _active_records(records: list[dict], tenant_id: str) -> list[dict]:
    return [
        record
        for record in records
        if record["tenant_id"] == tenant_id and record.get("status", "active") in ACTIVE_QUERY_STATES
    ]


def test_soft_delete_records_tombstone_metadata():
    record = {"id": "workspace_001", "tenant_id": "tenant_a", "status": "active"}
    deleted = _soft_delete(record, actor_id="user_admin", request_id="del_req_001")
    assert deleted["status"] == "deleted"
    assert deleted["deleted_at"] == "2026-06-04T00:00:00Z"
    assert deleted["deleted_by"] == "user_admin"
    assert deleted["deletion_request_id"] == "del_req_001"
    assert deleted["tenant_id"] == record["tenant_id"]


def test_soft_deleted_records_are_hidden_from_active_queries():
    active = {"id": "acct_active", "tenant_id": "tenant_a", "status": "active"}
    deleted = _soft_delete({"id": "acct_deleted", "tenant_id": "tenant_a", "status": "active"}, actor_id="u", request_id="r")
    foreign = {"id": "acct_foreign", "tenant_id": "tenant_b", "status": "active"}
    visible = _active_records([active, deleted, foreign], tenant_id="tenant_a")
    assert visible == [active]


def test_soft_delete_does_not_remove_referential_anchor():
    deleted = _soft_delete({"id": "user_001", "tenant_id": "tenant_a", "status": "active"}, actor_id="u", request_id="r")
    audit_event = {"event": "user.deleted", "tenant_id": "tenant_a", "actor_id": deleted["id"]}
    assert audit_event["actor_id"] == "user_001"
    assert deleted["id"] == "user_001"
