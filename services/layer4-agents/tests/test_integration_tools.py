from __future__ import annotations

import asyncio
from typing import Any

import pytest

from layer4_agents.models.tool_schemas import (
    CreateTaskInput,
    ExportToCRMInput,
    ScheduleMeetingInput,
    SendNotificationInput,
)
from layer4_agents.tools.integration_tools import (
    CreateTaskTool,
    ExportToCRMTool,
    ScheduleMeetingTool,
    SendNotificationTool,
)


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        data: dict[str, Any] | None = None,
        *,
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._data = data or {}
        self.text = text
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        return self._data


class FakeClient:
    def __init__(self, *responses: FakeResponse | BaseException) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def post(self, url: str | None, **kwargs: Any) -> FakeResponse:
        self.calls.append((str(url), kwargs))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def notification_input(channel: str = "email") -> SendNotificationInput:
    return SendNotificationInput(
        channel=channel,
        recipients=["one@example.com", "two@example.com"],
        subject="Decision ready",
        message="Review the attached evidence.",
    )


def task_input() -> CreateTaskInput:
    return CreateTaskInput(
        title="Review evidence",
        description="Validate source quality",
        assignee="user-1",
        due_date="2026-08-02",
        priority="high",
    )


def meeting_input() -> ScheduleMeetingInput:
    return ScheduleMeetingInput(
        title="Evidence review",
        attendees=["one@example.com", "two@example.com"],
        duration_minutes=45,
        preferred_times=["2026-08-02T10:00:00Z"],
        description="Review source quality",
    )


def crm_input(entity_type: str = "note") -> ExportToCRMInput:
    return ExportToCRMInput(
        entity_type=entity_type,
        entity_data={"title": "Evidence", "content": "Validated", "filename": "evidence.pdf"},
        prospect_id="prospect-1",
    )


@pytest.mark.asyncio
async def test_email_notification_uses_all_manifest_recipients() -> None:
    client = FakeClient(FakeResponse(202, headers={"X-Message-Id": "message-1"}))
    tool = SendNotificationTool({"sendgrid_api_key": "key", "from_email": "from@example.com"})
    tool._client = client

    result = await tool.execute(notification_input())

    assert result.success is True
    assert result.message_id == "message-1"
    assert result.error is None
    assert client.calls[0][1]["json"]["personalizations"] == [
        {"to": [{"email": "one@example.com"}, {"email": "two@example.com"}]}
    ]


@pytest.mark.asyncio
async def test_email_notification_preserves_safe_provider_error() -> None:
    client = FakeClient(FakeResponse(400, text="invalid recipient"))
    tool = SendNotificationTool()
    tool._client = client

    result = await tool.execute(notification_input())

    assert result.model_dump() == {
        "success": False,
        "message_id": None,
        "error": "invalid recipient",
    }


@pytest.mark.asyncio
async def test_slack_notification_uses_first_recipient_as_channel() -> None:
    client = FakeClient(FakeResponse(200, {"ok": True, "ts": "123.4"}))
    tool = SendNotificationTool({"slack_bot_token": "token"})
    tool._client = client

    result = await tool.execute(notification_input("slack"))

    assert result.success is True
    assert result.message_id == "123.4"
    assert client.calls[0][1]["data"]["channel"] == "one@example.com"


@pytest.mark.asyncio
async def test_slack_notification_returns_provider_error() -> None:
    client = FakeClient(FakeResponse(200, {"ok": False, "error": "channel_not_found"}))
    tool = SendNotificationTool()
    tool._client = client

    result = await tool.execute(notification_input("slack"))

    assert result.success is False
    assert result.error == "channel_not_found"


@pytest.mark.asyncio
async def test_teams_notification_returns_http_error() -> None:
    client = FakeClient(FakeResponse(500, text="webhook rejected"))
    tool = SendNotificationTool({"teams_webhook_url": "https://teams.example/hook"})
    tool._client = client

    result = await tool.execute(notification_input("teams"))

    assert result.success is False
    assert result.error == "webhook rejected"
    assert client.calls[0][0] == "https://teams.example/hook"


@pytest.mark.asyncio
async def test_notification_network_error_is_safely_classified() -> None:
    client = FakeClient(RuntimeError("token=secret"))
    tool = SendNotificationTool()
    tool._client = client

    result = await tool.execute(notification_input())

    assert result.success is False
    assert result.error == "EMAIL_SEND_ERROR"


@pytest.mark.asyncio
async def test_notification_cancellation_propagates() -> None:
    client = FakeClient(asyncio.CancelledError())
    tool = SendNotificationTool()
    tool._client = client

    with pytest.raises(asyncio.CancelledError):
        await tool.execute(notification_input())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "status", "data", "expected_id", "url_fragment"),
    [
        ("asana", 201, {"data": {"gid": "asana-1"}}, "asana-1", "app.asana.com"),
        ("monday", 200, {"data": {"create_item": {"id": "monday-1"}}}, "monday-1", "monday.com"),
        ("clickup", 200, {"id": "clickup-1"}, "clickup-1", "app.clickup.com"),
    ],
)
async def test_task_provider_success(
    provider: str,
    status: int,
    data: dict[str, Any],
    expected_id: str,
    url_fragment: str,
) -> None:
    client = FakeClient(FakeResponse(status, data))
    tool = CreateTaskTool({"pm_provider": provider, "pm_project_id": "project-1"})
    tool._client = client

    result = await tool.execute(task_input())

    assert result.success is True
    assert result.task_id == expected_id
    assert url_fragment in str(result.url)
    assert result.error is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "status", "data", "expected_error"),
    [
        ("asana", 400, {"errors": ["invalid"]}, "['invalid']"),
        ("monday", 200, {"errors": ["invalid"]}, "['invalid']"),
        ("clickup", 400, {"err": "invalid"}, "invalid"),
    ],
)
async def test_task_provider_failure(
    provider: str, status: int, data: dict[str, Any], expected_error: str
) -> None:
    client = FakeClient(FakeResponse(status, data))
    tool = CreateTaskTool({"pm_provider": provider, "pm_project_id": "project-1"})
    tool._client = client

    result = await tool.execute(task_input())

    assert result.success is False
    assert result.error == expected_error


@pytest.mark.asyncio
async def test_unsupported_task_provider_fails_closed() -> None:
    tool = CreateTaskTool({"pm_provider": "unknown"})
    tool._client = FakeClient(FakeResponse(200))

    result = await tool.execute(task_input())

    assert result.success is False
    assert result.error == "TASK_CREATE_ERROR"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "status", "data", "expected_id", "link_key"),
    [
        (
            "google",
            200,
            {"id": "google-1", "htmlLink": "https://calendar/google-1"},
            "google-1",
            "htmlLink",
        ),
        (
            "outlook",
            201,
            {"id": "outlook-1", "webLink": "https://calendar/outlook-1"},
            "outlook-1",
            "webLink",
        ),
    ],
)
async def test_calendar_provider_success(
    provider: str,
    status: int,
    data: dict[str, Any],
    expected_id: str,
    link_key: str,
) -> None:
    client = FakeClient(FakeResponse(status, data))
    tool = ScheduleMeetingTool({"calendar_provider": provider})
    tool._client = client

    result = await tool.execute(meeting_input())

    assert result.success is True
    assert result.meeting_id == expected_id
    assert result.scheduled_time == "2026-08-02T10:00:00Z"
    assert result.calendar_link == data[link_key]
    assert result.error is None
    assert (
        client.calls[0][1]["json"]["subject" if provider == "outlook" else "summary"]
        == "Evidence review"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["google", "outlook"])
async def test_calendar_provider_failure(provider: str) -> None:
    client = FakeClient(FakeResponse(400, {"error": {"message": "invalid slot"}}))
    tool = ScheduleMeetingTool({"calendar_provider": provider})
    tool._client = client

    result = await tool.execute(meeting_input())

    assert result.success is False
    assert result.error == "invalid slot"


@pytest.mark.asyncio
async def test_unsupported_calendar_provider_fails_closed() -> None:
    tool = ScheduleMeetingTool({"calendar_provider": "unknown"})
    tool._client = FakeClient(FakeResponse(200))

    result = await tool.execute(meeting_input())

    assert result.success is False
    assert result.error == "MEETING_SCHEDULE_ERROR"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("crm_type", "entity_type", "status", "data", "expected_id"),
    [
        ("salesforce", "note", 201, {"id": "sf-note"}, "sf-note"),
        ("salesforce", "activity", 201, {"id": "sf-task"}, "sf-task"),
        ("salesforce", "document", 201, {"id": "sf-file"}, "sf-file"),
        ("hubspot", "note", 200, {"engagement": {"id": "hs-note"}}, "hs-note"),
        ("hubspot", "activity", 200, {"engagement": {"id": "hs-task"}}, "hs-task"),
        ("hubspot", "document", 200, {"id": "hs-file"}, "hs-file"),
    ],
)
async def test_crm_export_success(
    crm_type: str,
    entity_type: str,
    status: int,
    data: dict[str, Any],
    expected_id: str,
) -> None:
    client = FakeClient(FakeResponse(status, data))
    tool = ExportToCRMTool(
        {
            "crm_type": crm_type,
            "crm_instance_url": "https://salesforce.example",
            "crm_api_key": "key",
        }
    )
    tool._client = client

    result = await tool.execute(crm_input(entity_type))

    assert result.success is True
    assert result.crm_record_id == expected_id
    assert result.error is None
    if entity_type == "activity":
        assert (
            "Task" in client.calls[0][0]
            or client.calls[0][1]["json"]["engagement"]["type"] == "TASK"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("crm_type", ["salesforce", "hubspot"])
async def test_crm_export_failure(crm_type: str) -> None:
    client = FakeClient(FakeResponse(400, {"message": "rejected"}))
    tool = ExportToCRMTool({"crm_type": crm_type, "crm_instance_url": "https://salesforce.example"})
    tool._client = client

    result = await tool.execute(crm_input())

    assert result.success is False
    assert result.error == "rejected"


@pytest.mark.asyncio
async def test_unsupported_crm_provider_fails_closed() -> None:
    tool = ExportToCRMTool({"crm_type": "unknown"})
    tool._client = FakeClient(FakeResponse(200))

    result = await tool.execute(crm_input())

    assert result.success is False
    assert result.error == "CRM_EXPORT_ERROR"
