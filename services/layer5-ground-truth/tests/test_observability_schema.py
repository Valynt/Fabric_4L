from pathlib import Path
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import httpx
import pytest

from layer5_ground_truth.integration.layer3_client import Layer3Client
from layer5_ground_truth.models.truth_object import (
    MaturityLevel,
    TruthObject,
    TruthStatus,
)
from layer5_ground_truth.services.state_machine import (
    InvalidTransitionError,
    ValidationStateMachine,
)
from tests.conftest import TEST_ORG_ID

REQUIRED_LOG_KEYS = (
    "request_id",
    "tenant_id",
    "truth_object_id",
    "transition",
    "sync_status",
)


def test_layer5_structured_log_keys_present_in_runtime_paths() -> None:
    """Guardrail: representative Layer 5 paths must emit required structured keys."""
    runtime_files = [
        Path("src/layer5_ground_truth/services/state_machine.py"),
        Path("src/layer5_ground_truth/integration/layer3_client.py"),
    ]
    for rel_path in runtime_files:
        content = (Path(__file__).resolve().parents[1] / rel_path).read_text()
        for key in REQUIRED_LOG_KEYS:
            assert (
                f'"{key}"' in content
            ), f"missing structured log key {key} in {rel_path}"


def test_layer5_observability_metric_schema_is_defined() -> None:
    """Guardrail: schema metric names/labels remain stable unless explicitly reviewed."""
    content = (
        Path(__file__).resolve().parents[1] / "src/metrics/prometheus_metrics.py"
    ).read_text()
    assert "validation_latency_seconds" in content
    assert "validation_transition_failures_total" in content
    assert "kg_sync_outcomes_total" in content
    assert '["transition"]' in content
    assert '["transition", "reason"]' in content
    assert '["sync_status", "transition"]' in content


def _make_truth(status: TruthStatus) -> TruthObject:
    return TruthObject(
        id=uuid.uuid4(),
        tenant_id=TEST_ORG_ID,
        claim="observability test claim",
        claim_type="efficiency_gain",
        confidence=0.9,
        status=status.value,
        maturity_level=MaturityLevel.EXTRACTED.value,
        freshness=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_invalid_transition_emits_failure_metric_and_structured_warning(
    caplog, monkeypatch
) -> None:
    sm = ValidationStateMachine()
    truth = _make_truth(TruthStatus.VALIDATED)

    class DummyMetrics:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        def increment_validation_transition_failure(
            self, transition: str, reason: str
        ) -> None:
            self.calls.append((transition, reason))

    metrics = DummyMetrics()
    monkeypatch.setattr(
        "layer5_ground_truth.services.state_machine.get_metrics", lambda: metrics
    )

    with pytest.raises(InvalidTransitionError):
        sm._assert_transition(truth, TruthStatus.VALIDATED)  # noqa: SLF001

    assert metrics.calls == [("validated->validated", "invalid_transition")]
    warning = next(
        rec for rec in caplog.records if rec.msg == "validation transition rejected"
    )
    assert warning.request_id is None
    assert warning.tenant_id == str(TEST_ORG_ID)
    assert warning.truth_object_id == str(truth.id)
    assert warning.transition == "validated->validated"
    assert warning.sync_status == "not_attempted"


@pytest.mark.asyncio
async def test_validation_latency_metric_emitted_on_success(monkeypatch) -> None:
    sm = ValidationStateMachine()
    truth = _make_truth(TruthStatus.PROPOSED)

    class FakeResult:
        rowcount = 1

    class FakeDB:
        def add(self, _obj) -> None:
            return None

        async def execute(self, _stmt):
            return FakeResult()

        async def flush(self) -> None:
            return None

    class DummyMetrics:
        def __init__(self) -> None:
            self.latency_calls: list[str] = []

        def increment_validations(self, from_status: str, to_status: str) -> None:
            return None

        def observe_validation_latency(self, transition: str, duration: float) -> None:
            assert duration >= 0
            self.latency_calls.append(transition)

    metrics = DummyMetrics()
    monkeypatch.setattr(
        "layer5_ground_truth.services.state_machine.get_metrics", lambda: metrics
    )
    await sm._apply_transition(  # noqa: SLF001
        FakeDB(),
        truth,
        TruthStatus.VALIDATED,
        actor="obs-test",
        actor_type="system",
        source_count=2,
    )
    assert metrics.latency_calls == ["proposed->validated"]


@pytest.mark.asyncio
async def test_sync_partial_failure_emits_retry_and_audit_safe_events(
    monkeypatch, caplog
) -> None:
    class DummyMetrics:
        def __init__(self) -> None:
            self.sync_outcomes: list[tuple[str, str]] = []

        def increment_kg_sync(self, status: str) -> None:
            return None

        def increment_kg_sync_outcome(self, sync_status: str, transition: str) -> None:
            self.sync_outcomes.append((sync_status, transition))

    metrics = DummyMetrics()
    monkeypatch.setattr(
        "layer5_ground_truth.integration.layer3_client.get_metrics", lambda: metrics
    )
    monkeypatch.setattr(
        "layer5_ground_truth.integration.layer3_client.asyncio.sleep", AsyncMock()
    )

    async def post_side_effect(*_args, **_kwargs):
        post_side_effect.count += 1
        if post_side_effect.count < 3:
            raise httpx.ConnectError(
                "transient network issue",
                request=httpx.Request("POST", "http://layer3.test/api/v1/nodes"),
            )
        raise httpx.ConnectError("final failure")

    post_side_effect.count = 0
    mock_client = AsyncMock()
    mock_client.post.side_effect = post_side_effect
    async_client_cm = AsyncMock()
    async_client_cm.__aenter__.return_value = mock_client
    monkeypatch.setattr(
        "layer5_ground_truth.integration.layer3_client.httpx.AsyncClient",
        lambda **kwargs: async_client_cm,
    )

    client = Layer3Client()
    client._settings.layer3_sync_enabled = True
    client._client = mock_client
    result = await client.sync_truth_object(
        truth_object_id=uuid.uuid4(),
        tenant_id=TEST_ORG_ID,
        claim="claim",
        claim_type="efficiency_gain",
        confidence=0.85,
        status="validated",
        maturity_level=4,
    )
    assert result is None
    assert ("exception", "validated->kg_sync") in metrics.sync_outcomes
    assert any("retrying in" in rec.getMessage() for rec in caplog.records)
    outcome_log = next(rec for rec in caplog.records if rec.msg == "kg sync outcome")
    assert outcome_log.request_id is None
    assert outcome_log.tenant_id == str(TEST_ORG_ID)
    assert outcome_log.transition == "validated->kg_sync"
    assert outcome_log.sync_status == "failed"
