from uuid import uuid4

import pytest

from layer5_ground_truth.observability.governance_alerts import (
    AlertHandler,
    AlertSeverity,
    AlertType,
    GovernanceAlert,
    GovernanceAlertManager,
)


class RecordingHandler(AlertHandler):
    def __init__(self):
        self.alerts: list[GovernanceAlert] = []

    async def handle_alert(self, alert: GovernanceAlert) -> bool:
        self.alerts.append(alert)
        return True


class ExplodingHandler(AlertHandler):
    async def handle_alert(self, alert: GovernanceAlert) -> bool:
        raise RuntimeError("boom")


class PartialHandler(AlertHandler):
    pass


class NonCompliantHandler:
    async def handle_alert(self, alert: GovernanceAlert) -> bool:
        return True


@pytest.fixture
def sample_alert() -> GovernanceAlert:
    return GovernanceAlert(
        alert_type=AlertType.POLICY_VIOLATION,
        severity=AlertSeverity.HIGH,
        tenant_id=uuid4(),
        entity_type="policy",
        entity_id=uuid4(),
        message="Policy violation detected",
    )


def test_add_handler_rejects_non_compliant_handler_type() -> None:
    manager = GovernanceAlertManager()

    with pytest.raises(TypeError, match="must be an AlertHandler"):
        manager.add_handler(NonCompliantHandler())


def test_partial_handler_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError, match="abstract"):
        PartialHandler()


@pytest.mark.asyncio
async def test_emit_alert_isolates_handler_failure(sample_alert: GovernanceAlert, caplog: pytest.LogCaptureFixture) -> None:
    manager = GovernanceAlertManager()
    good_handler = RecordingHandler()
    bad_handler = ExplodingHandler()

    manager.handlers = [bad_handler, good_handler]

    with caplog.at_level("ERROR"):
        await manager.emit_alert(sample_alert)

    assert len(good_handler.alerts) == 1
    assert good_handler.alerts[0].message == sample_alert.message
    assert "Alert handler failed" in caplog.text


@pytest.mark.asyncio
async def test_emit_alert_fans_out_to_all_handlers(sample_alert: GovernanceAlert) -> None:
    manager = GovernanceAlertManager()
    handler_one = RecordingHandler()
    handler_two = RecordingHandler()

    manager.handlers = [handler_one, handler_two]
    await manager.emit_alert(sample_alert)

    assert len(handler_one.alerts) == 1
    assert len(handler_two.alerts) == 1
    assert handler_one.alerts[0].to_dict() == handler_two.alerts[0].to_dict()
