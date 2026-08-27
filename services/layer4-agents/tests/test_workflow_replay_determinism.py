from __future__ import annotations

"""Replay determinism tests for restart/retry checkpoint scenarios."""


try:
    from tests.utils.replay_assertions import (
        assert_semantically_equivalent_replay,
        normalize_checkpoint_snapshot,
    )
except (ImportError, ModuleNotFoundError):
    import importlib.util
    from pathlib import Path
    _helper_path = Path(__file__).resolve().parent / "utils" / "replay_assertions.py"
    _spec = importlib.util.spec_from_file_location("layer4_test_replay_assertions", _helper_path)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    assert_semantically_equivalent_replay = _mod.assert_semantically_equivalent_replay
    normalize_checkpoint_snapshot = _mod.normalize_checkpoint_snapshot


def _sample_checkpoint_state(*, status: str = "completed") -> dict:
    return {
        "serialization": {
            "format": "json",
            "version": "1.0",
        },
        "workflow": {
            "workflow_id": "08f9f6c8-90d3-4f85-a352-c1b60d950f16",
            "status": status,
            "state_transitions": [
                {"from": "queued", "to": "running"},
                {"from": "running", "to": status},
            ],
            "tool_decisions": [
                {"tool": "retrieve_context", "decision": "selected"},
                {"tool": "generate_output", "decision": "selected"},
            ],
            "structured_outputs": {
                "summary": "Deterministic output payload",
                "score": 89,
            },
        },
        "meta": {
            "created_at": "2026-05-12T11:22:33.456Z",
            "updated_at": "2026-05-12T11:22:33.457Z",
            "trace_id": "3b9a6f60-7ef7-46f5-8fd1-0d4b8f704fd9",
            "request_id": "4f66d833-58fb-46d8-a901-2e8793f0962c",
        },
    }


def test_normalize_checkpoint_snapshot_masks_nondeterministic_values() -> None:
    normalized = normalize_checkpoint_snapshot(_sample_checkpoint_state())

    assert normalized["meta"]["created_at"] == "<normalized:created_at>"
    assert normalized["meta"]["updated_at"] == "<normalized:updated_at>"
    assert normalized["meta"]["trace_id"] == "<normalized:trace_id>"
    assert normalized["workflow"]["status"] == "completed"


def test_ws3_replay_stable_after_restart_and_retry() -> None:
    baseline = _sample_checkpoint_state(status="completed")
    replayed_after_restart_and_retry = _sample_checkpoint_state(status="completed")
    replayed_after_restart_and_retry["meta"]["created_at"] = "2026-05-12T11:24:11.101Z"
    replayed_after_restart_and_retry["meta"]["updated_at"] = "2026-05-12T11:24:12.101Z"
    replayed_after_restart_and_retry["meta"]["trace_id"] = "e05fa8f4-c7d9-4a8f-a3ea-bf969ea31975"
    replayed_after_restart_and_retry["meta"]["request_id"] = "3fd4eb89-28d7-4b7f-a90c-b3f1e74eb299"

    assert_semantically_equivalent_replay(
        baseline_snapshot=baseline,
        replayed_snapshot=replayed_after_restart_and_retry,
    )
