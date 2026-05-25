from pathlib import Path


def test_layer5_validation_events_enforces_privileged_insert_and_append_only() -> None:
    source = Path(
        "services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions/010_enforce_append_only_audit_events.py"
    ).read_text()

    assert "validation_events is append-only" in source
    assert "inserts require privileged service account role" in source
    assert "trg_validation_events_no_update" in source
    assert "trg_validation_events_no_delete" in source
    assert "trg_validation_events_privileged_insert" in source
