from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

import layer4_agents.services.notification as notification_module
from layer4_agents.services.notification import (
    NotificationChannel,
    NotificationEvent,
    NotificationPreference,
    NotificationPriority,
    NotificationService,
)


def event(
    *,
    priority=NotificationPriority.NORMAL,
    channels=None,
    user_id="user",
    created_at=None,
):
    return NotificationEvent(
        event_id=f"event-{priority.value}",
        workflow_id="workflow",
        tenant_id="tenant",
        user_id=user_id,
        event_type="workflow_paused",
        title="Title",
        message="Message",
        priority=priority,
        channels=channels or [NotificationChannel.IN_APP],
        payload={"safe": "value"},
        created_at=created_at or datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_start_stop_manage_background_task_and_webhook_session(monkeypatch) -> None:
    closed = []

    class Session:
        async def close(self):
            closed.append(True)

    monkeypatch.setattr(notification_module.aiohttp, "ClientSession", Session)
    svc = NotificationService()
    await svc.start()
    assert svc._batch_task is not None and isinstance(svc._webhook_session, Session)
    await svc.stop()
    assert svc._batch_task is None and svc._webhook_session is None and closed == [True]
    await svc.stop()


def test_callbacks_preferences_defaults_threshold_and_partial_quiet_hours() -> None:
    svc = NotificationService(default_channels=[NotificationChannel.EMAIL])

    def callback(_event):
        return None

    svc.register_in_app_callback(callback)
    assert svc._in_app_callbacks == [callback]
    defaults = svc.get_user_preferences("new")
    assert defaults.channels == [NotificationChannel.EMAIL]
    defaults.channels.append(NotificationChannel.WEBHOOK)
    assert svc.default_channels == [NotificationChannel.EMAIL]

    pref = NotificationPreference(
        user_id="user",
        channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
        pause_severity_threshold=notification_module.PauseSeverity.CRITICAL,
    )
    svc.set_user_preferences(pref)
    assert not svc._is_quiet_hours_active("user")
    assert svc._get_channels_for_user("user", notification_module.PauseSeverity.INFO) == [
        NotificationChannel.IN_APP
    ]
    assert (
        svc._get_channels_for_user("user", notification_module.PauseSeverity.CRITICAL)
        == pref.channels
    )
    with pytest.raises(ValueError, match="configured together"):
        svc.set_user_preferences(
            NotificationPreference(
                user_id="partial-start",
                channels=[NotificationChannel.IN_APP],
                quiet_hours_start=9,
            )
        )
    with pytest.raises(ValueError, match="configured together"):
        svc.set_user_preferences(
            NotificationPreference(
                user_id="partial-end",
                channels=[NotificationChannel.IN_APP],
                quiet_hours_end=17,
            )
        )


@pytest.mark.asyncio
async def test_notification_factories_preserve_payload_priority_and_channels() -> None:
    svc = NotificationService()
    paused = await svc.notify_workflow_paused(
        "workflow",
        {
            "severity": "critical",
            "title": "Approval",
            "message": "Review",
            "reason": "risk",
            "required_inputs": [{"name": "decision"}],
        },
        user_id="user",
        tenant_id="tenant",
        channels=[NotificationChannel.EMAIL],
    )
    assert paused.priority == NotificationPriority.URGENT
    assert paused.channels == [NotificationChannel.EMAIL]
    assert paused.payload["required_inputs"] == ["decision"]

    fallback = await svc.notify_workflow_paused("workflow", {"severity": "unknown"})
    assert fallback.priority == NotificationPriority.HIGH
    completed = await svc.notify_workflow_completed(
        "workflow",
        "failed",
        result_summary={"reason": "safe"},
        channels=[NotificationChannel.WEBHOOK],
    )
    assert completed.title == "Workflow Failed"
    assert completed.payload == {"status": "failed", "result_summary": {"reason": "safe"}}
    checkpoint = await svc.notify_checkpoint_reached("workflow", "checkpoint", "review")
    assert checkpoint.priority == NotificationPriority.LOW
    assert checkpoint.channels == [NotificationChannel.IN_APP]
    assert svc._event_queue.qsize() == 4


@pytest.mark.asyncio
async def test_bounded_queue_drops_normal_and_urgent_evicts_low() -> None:
    svc = NotificationService()
    svc._event_queue = asyncio.Queue(maxsize=2)
    low = event(priority=NotificationPriority.LOW)
    high = event(priority=NotificationPriority.HIGH)
    await svc._event_queue.put(low)
    await svc._event_queue.put(high)

    normal = event(priority=NotificationPriority.NORMAL)
    assert not await svc._enqueue_event(normal)
    assert svc._dropped_count == 1

    urgent = event(priority=NotificationPriority.URGENT)
    assert await svc._enqueue_event(urgent)
    queued = [svc._event_queue.get_nowait(), svc._event_queue.get_nowait()]
    assert low not in queued and high in queued and urgent in queued


@pytest.mark.asyncio
async def test_urgent_is_dropped_when_full_without_low_priority() -> None:
    svc = NotificationService()
    svc._event_queue = asyncio.Queue(maxsize=1)
    await svc._event_queue.put(event(priority=NotificationPriority.HIGH))
    assert not await svc._enqueue_event(event(priority=NotificationPriority.URGENT))
    assert svc._dropped_count == 1


def test_priority_eviction_handles_empty_and_internal_errors(monkeypatch) -> None:
    svc = NotificationService()
    assert not svc._drop_oldest_by_priority(NotificationPriority.LOW)

    class BrokenQueue:
        def empty(self):
            raise RuntimeError("broken")

    svc._event_queue = BrokenQueue()
    assert not svc._drop_oldest_by_priority(NotificationPriority.LOW)


@pytest.mark.asyncio
async def test_batch_processor_drops_stale_and_processes_fresh() -> None:
    svc = NotificationService()
    svc._max_event_age_seconds = 1
    stale = event(created_at=datetime.now(UTC) - timedelta(seconds=5))
    fresh = event()
    await svc._event_queue.put(stale)
    await svc._event_queue.put(fresh)
    processed = asyncio.Event()

    async def process(value):
        assert value is fresh
        processed.set()

    svc._process_notification = process
    task = asyncio.create_task(svc._batch_processor())
    await asyncio.wait_for(processed.wait(), timeout=2)
    task.cancel()
    await task


@pytest.mark.asyncio
async def test_batch_processor_balances_queue_tasks_for_stale_and_processed_events() -> None:
    svc = NotificationService()
    svc._max_event_age_seconds = 1
    await svc._event_queue.put(event(created_at=datetime.now(UTC) - timedelta(seconds=5)))
    await svc._event_queue.put(event())
    processed = asyncio.Event()

    async def process(_value):
        processed.set()

    svc._process_notification = process
    task = asyncio.create_task(svc._batch_processor())
    await asyncio.wait_for(processed.wait(), timeout=2)
    await asyncio.wait_for(svc._event_queue.join(), timeout=2)
    task.cancel()
    await task


@pytest.mark.asyncio
async def test_priority_eviction_balances_drained_queue_tasks() -> None:
    svc = NotificationService()
    low = event(priority=NotificationPriority.LOW)
    high = event(priority=NotificationPriority.HIGH)
    await svc._event_queue.put(low)
    await svc._event_queue.put(high)

    assert svc._drop_oldest_by_priority(NotificationPriority.LOW)
    remaining = svc._event_queue.get_nowait()
    svc._event_queue.task_done()
    assert remaining is high
    await asyncio.wait_for(svc._event_queue.join(), timeout=2)


@pytest.mark.asyncio
async def test_process_notification_dispatches_channels_and_tracks_failures() -> None:
    svc = NotificationService()
    calls = []

    async def success(value):
        calls.append(value)

    async def fail(_value):
        raise RuntimeError("offline")

    svc._send_in_app = success
    svc._send_email = success
    svc._send_webhook = fail
    svc._send_slack = success
    svc._send_teams = success
    value = event(
        channels=[
            NotificationChannel.IN_APP,
            NotificationChannel.EMAIL,
            NotificationChannel.WEBHOOK,
            NotificationChannel.PUSH,
            NotificationChannel.SLACK,
            NotificationChannel.TEAMS,
        ]
    )
    await svc._process_notification(value)
    assert len(calls) == 4
    assert value.delivered[NotificationChannel.WEBHOOK] is False
    assert all(
        value.delivered[channel]
        for channel in value.channels
        if channel != NotificationChannel.WEBHOOK
    )

    async def cancel(_value):
        raise asyncio.CancelledError

    svc._send_in_app = cancel
    with pytest.raises(asyncio.CancelledError):
        await svc._process_notification(event())


@pytest.mark.asyncio
async def test_in_app_callbacks_support_sync_async_failures_and_cancellation() -> None:
    svc = NotificationService()
    calls = []

    def sync(value):
        calls.append(("sync", value.event_id))

    async def async_callback(value):
        calls.append(("async", value.event_id))

    def fail(_value):
        raise RuntimeError("callback failed")

    svc._in_app_callbacks = [sync, async_callback, fail]
    await svc._send_in_app(event())
    assert [call[0] for call in calls] == ["sync", "async"]

    async def cancel(_value):
        raise asyncio.CancelledError

    svc._in_app_callbacks = [cancel]
    with pytest.raises(asyncio.CancelledError):
        await svc._send_in_app(event())


@pytest.mark.asyncio
async def test_email_requires_user_and_address() -> None:
    svc = NotificationService()
    await svc._send_email(event(user_id=None))
    await svc._send_email(event())
    svc.set_user_preferences(
        NotificationPreference(
            user_id="user", channels=[NotificationChannel.EMAIL], email="user@example.test"
        )
    )
    await svc._send_email(event())


class Response:
    def __init__(self, status):
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


class Session:
    def __init__(self, statuses=(200,)):
        self.statuses = list(statuses)
        self.calls = []
        self.error = None

    def post(self, url, **kwargs):
        if self.error:
            raise self.error
        self.calls.append((url, kwargs))
        return Response(self.statuses.pop(0))


@pytest.mark.asyncio
async def test_webhook_builds_signed_payload_and_handles_status_errors() -> None:
    svc = NotificationService(webhook_secret="secret")
    await svc._send_webhook(event(user_id=None))
    await svc._send_webhook(event())
    svc.set_user_preferences(
        NotificationPreference(
            user_id="user",
            channels=[NotificationChannel.WEBHOOK],
            webhook_url="https://hooks.example.test/workflow",
        )
    )
    await svc._send_webhook(event())
    session = Session([204, 500])
    svc._webhook_session = session
    await svc._send_webhook(event())
    await svc._send_webhook(event())
    url, kwargs = session.calls[0]
    assert url == "https://hooks.example.test/workflow"
    assert kwargs["headers"]["X-Workflow-Signature"].startswith("sha256=")
    assert kwargs["headers"]["X-Workflow-Event"] == "workflow_paused"

    session.error = RuntimeError("offline")
    with pytest.raises(RuntimeError, match="offline"):
        await svc._send_webhook(event())
    session.error = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await svc._send_webhook(event())


@pytest.mark.asyncio
async def test_slack_payload_colors_statuses_errors_and_cancellation() -> None:
    svc = NotificationService()
    await svc._send_slack(event(user_id=None))
    await svc._send_slack(event())
    svc.set_user_preferences(
        NotificationPreference(
            user_id="user",
            channels=[NotificationChannel.SLACK],
            slack_webhook="https://hooks.example.test/slack",
        )
    )
    await svc._send_slack(event())
    session = Session([200, 500])
    svc._webhook_session = session
    await svc._send_slack(event(priority=NotificationPriority.URGENT))
    await svc._send_slack(event(priority=NotificationPriority.HIGH))
    assert session.calls[0][1]["json"]["attachments"][0]["color"] == "#ff0000"

    session.error = RuntimeError("offline")
    await svc._send_slack(event())
    session.error = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await svc._send_slack(event())


@pytest.mark.asyncio
async def test_teams_signature_and_singleton(monkeypatch) -> None:
    svc = NotificationService()
    await svc._send_teams(event())
    assert svc._generate_signature({"a": 1}) == ""
    signed = NotificationService(webhook_secret="secret")._generate_signature({"a": 1})
    assert signed.startswith("sha256=") and len(signed) == 71
    monkeypatch.setattr(notification_module, "_notification_service", None)
    first = notification_module.get_notification_service()
    assert notification_module.get_notification_service() is first
