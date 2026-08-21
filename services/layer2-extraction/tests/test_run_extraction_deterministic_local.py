"""Characterization tests for ``run_extraction``'s deterministic local branch.

The ``model_version="e2e-local-extraction-model"`` branch of ``run_extraction``
builds deterministic, locally-synthesized artifacts without invoking an LLM. It
is the only branch of the pipeline that persists validated entities and writes an
RDF file using fully deterministic IDs. Existing route tests monkeypatch the whole
``run_extraction`` function away, so this branch was never executed by the test
suite. These tests characterize its intended behavior.

Covered behaviors:
- The deterministic branch builds 4 entities (capability, use case, persona,
  value driver) plus one ``enables`` relationship.
- The job transitions to ``completed`` with the correct entity/relationship
  counts when ``mark_pipeline_complete=True``.
- ``completed_at`` is set and ``broadcast_pipeline_complete`` fires only when
  ``mark_pipeline_complete=True``.
- Generated IDs are stable across idempotent re-runs (same content + tenant).
- Invalid artifacts fail closed: validation rejects, the job is marked failed,
  and an error / failed-completion broadcast is emitted.

All layer-2 side dependencies (job store, websocket manager, metrics, RDF output
dir) are replaced with in-memory/recording doubles so the branch runs headlessly.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from layer2_extraction.api import main as api_main
from layer2_extraction.integration.job_store import InMemoryJobStore
from layer2_extraction.models import PredicateType


DETERMINISTIC_CONFIG = {
    "tenant_id": "tenant-analyze",
    "model_version": "e2e-local-extraction-model",
    "schema_version": "value-fabric-extraction-v1",
    "prompt_version": "test-prompt-v1",
    "ingestion_id": "ing-1",
    "value_pack_id": "default",
    "chunk_size": 200,
    "chunk_overlap": 20,
    "confidence_threshold": 0.8,
}


class RecordingMetrics:
    """Records metric interactions instead of depending on the global instance."""

    def __init__(self) -> None:
        self.outcomes: list[dict] = []

    def record_extraction_outcome(self, **kwargs) -> None:
        self.outcomes.append(kwargs)

    def record_retry(self, **kwargs) -> None:
        pass


class RecordingWSManager:
    """Records websocket broadcasts without a live connection."""

    def __init__(self) -> None:
        self.stage_starts: list[dict] = []
        self.stage_completes: list[dict] = []
        self.pipeline_completes: list[dict] = []
        self.errors: list[dict] = []

    async def broadcast(self, *args, **kwargs) -> None:
        pass

    async def broadcast_stage_start(self, **kwargs) -> None:
        self.stage_starts.append(kwargs)

    async def broadcast_stage_complete(self, **kwargs) -> None:
        self.stage_completes.append(kwargs)

    async def broadcast_stage_progress(self, **kwargs) -> None:
        pass

    async def broadcast_ingestion_status(self, **kwargs) -> None:
        pass

    async def broadcast_pipeline_complete(self, **kwargs) -> None:
        self.pipeline_completes.append(kwargs)

    async def broadcast_error(self, **kwargs) -> None:
        self.errors.append(kwargs)

    def register(self, *args, **kwargs) -> None:
        pass

    def unregister(self, *args, **kwargs) -> None:
        pass


@pytest.fixture
def deterministic_local_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict:
    """Wire deterministic-branch dependencies to controlled doubles."""
    job_store = InMemoryJobStore()
    monkeypatch.setattr(api_main, "job_store", job_store)

    ws = RecordingWSManager()
    monkeypatch.setattr(api_main, "_ws_manager", ws)

    metrics = RecordingMetrics()
    monkeypatch.setattr(api_main, "get_metrics", lambda: metrics)

    rdf_output_dir = tmp_path / "rdf"
    rdf_output_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("RDF_OUTPUT_DIR", str(rdf_output_dir))

    return {
        "job_store": job_store,
        "ws": ws,
        "metrics": metrics,
        "rdf_output_dir": rdf_output_dir,
    }


async def _run_and_load(
    env: dict,
    job_id: str,
    content: str,
    *,
    config: dict,
    mark_pipeline_complete: bool = True,
):
    artifacts = await api_main.run_extraction(
        job_id=job_id,
        source_url=f"https://example.com/{job_id}",
        content=content,
        config=config,
        mark_pipeline_complete=mark_pipeline_complete,
    )
    job = await env["job_store"].get(job_id)
    return artifacts, job


async def test_deterministic_local_branch_completes_job_with_counts(
    deterministic_local_env: dict,
) -> None:
    """The deterministic branch persists a completed job with exact counts."""
    env = deterministic_local_env
    artifacts, job = await _run_and_load(
        env,
        "job-ok",
        "Test Header\n\nLocal extraction content for characterization.",
        config=dict(DETERMINISTIC_CONFIG),
    )

    # Deterministic artifact shape: 4 entities + 1 enables relationship.
    result = artifacts.result
    assert len(result.capabilities) == 1
    assert len(result.use_cases) == 1
    assert len(result.personas) == 1
    assert len(result.value_drivers) == 1
    assert len(artifacts.relationships) == 1
    assert artifacts.relationships[0].canonical_predicate == PredicateType.ENABLES

    # Job reaches completed with matching counts.
    assert job is not None
    assert job.extraction_status == "completed"
    assert job.entities_extracted == 4
    assert job.relationships_extracted == 1
    assert job.completed_at is not None

    # RDF file is written under the configured output directory.
    rdf_file = env["rdf_output_dir"] / f"{job.job_id}.ttl"
    assert rdf_file.exists()
    turtle = rdf_file.read_text()
    assert "valuefabric" in turtle
    assert "enables" in turtle

    # The pipeline-complete broadcast fired exactly once with the RDF path.
    events = [e for e in env["ws"].pipeline_completes if e["job_id"] == "job-ok"]
    assert len(events) == 1
    assert events[0]["status"] == "completed"
    assert events[0]["entities_extracted"] == 4
    assert events[0]["relationships_extracted"] == 1
    assert os.path.normpath(events[0]["rdf_path"]) == os.path.normpath(str(rdf_file))


async def test_deterministic_local_branch_skips_completion_marker_when_disabled(
    deterministic_local_env: dict,
) -> None:
    """mark_pipeline_complete=False leaves completed_at unset and omits the broadcast."""
    env = deterministic_local_env
    artifacts, job = await _run_and_load(
        env,
        "job-2",
        content="Second local extraction content.",
        config=dict(DETERMINISTIC_CONFIG),
        mark_pipeline_complete=False,
    )

    assert artifacts is not None
    assert job is not None
    assert job.extraction_status == "completed"
    assert job.completed_at is None
    assert not any(e["job_id"] == "job-2" for e in env["ws"].pipeline_completes)


async def test_deterministic_local_branch_is_idempotent_across_runs(
    deterministic_local_env: dict,
) -> None:
    """Identical content+tenant yields identical entity IDs across separate jobs."""
    env = deterministic_local_env
    artifacts_a, _ = await _run_and_load(
        env, "job-3a", "Shared deterministic content.", config=dict(DETERMINISTIC_CONFIG)
    )
    artifacts_b, _ = await _run_and_load(
        env, "job-3b", "Shared deterministic content.", config=dict(DETERMINISTIC_CONFIG)
    )

    ids_a = [e.id for e in artifacts_a.result.get_all_entities()]
    ids_b = [e.id for e in artifacts_b.result.get_all_entities()]
    assert len(ids_a) == 4
    assert ids_a == ids_b


async def test_deterministic_local_branch_fails_closed_on_invalid_artifacts(
    deterministic_local_env: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A raised validation error fails the job closed and propagates."""
    env = deterministic_local_env
    real_build = api_main._build_e2e_local_extraction_artifacts

    def invalid_artifacts(**kwargs):
        artifacts = real_build(**kwargs)
        artifacts.result.tenant_id = ""  # Violate mandatory metadata.
        return artifacts

    monkeypatch.setattr(api_main, "_build_e2e_local_extraction_artifacts", invalid_artifacts)

    raised = None
    try:
        await api_main.run_extraction(
            job_id="job-invalid",
            source_url="https://example.com/job-invalid",
            content="Invalid content intended to fail validation.",
            config=dict(DETERMINISTIC_CONFIG),
        )
    except Exception as exc:  # noqa: BLE001 - intentionally characterizing failure.
        raised = exc

    assert raised is not None, "expected validation to reject the broken artifact"
    job = await env["job_store"].get("job-invalid")
    assert job is not None
    assert job.extraction_status == "failed"
    # Failure path emits an error broadcast and a failed pipeline-complete event.
    assert any(e["job_id"] == "job-invalid" for e in env["ws"].errors)
    assert any(
        e["job_id"] == "job-invalid" and e["status"] == "failed"
        for e in env["ws"].pipeline_completes
    )