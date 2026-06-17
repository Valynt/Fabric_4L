from __future__ import annotations

"""Integration tools for notifications, tasks, meetings, and CRM exports."""
import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from ..models.tool_schemas import (
    CreateTaskInput,
    CreateTaskOutput,
    ExportToCRMInput,
    ExportToCRMOutput,
    ScheduleMeetingInput,
    ScheduleMeetingOutput,
    SendNotificationInput,
    SendNotificationOutput,
    ToolCategory,
)
from .registry import BaseTool

logger = logging.getLogger(__name__)


class SendNotificationTool(BaseTool):
    """Send notifications via email, Slack, or Teams using production APIs."""

    name = "send_notification"
    category = ToolCategory.INTEGRATION
    description = "Sends notifications via email, Slack, or Microsoft Teams"
    input_schema = SendNotificationInput
    output_schema = SendNotificationOutput
    timeout_seconds = 15
    requires_auth = True

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        # Email config (SendGrid)
        self.sendgrid_api_key = config.get("sendgrid_api_key") if config else None
        self.from_email = (
            config.get("from_email", "notifications@valuefabric.io")
            if config
            else "notifications@valuefabric.io"
        )
        # Slack config
        self.slack_bot_token = config.get("slack_bot_token") if config else None
        # Teams config
        self.teams_webhook_url = config.get("teams_webhook_url") if config else None
        self._client = None

    def _get_client(self):
        """Get HTTP client with connection pooling and timeout configuration."""
        if self._client is None:
            # Connection pooling limits for boundary resilience
            limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
            timeout = httpx.Timeout(30.0, connect=10.0)
            self._client = httpx.AsyncClient(timeout=timeout, limits=limits)
        return self._client

    async def execute(self, input_data: SendNotificationInput) -> SendNotificationOutput:
        """Send notification via specified channel."""
        channel = input_data.channel

        if channel == "email":
            return await self._send_email(input_data)
        elif channel == "slack":
            return await self._send_slack(input_data)
        elif channel == "teams":
            return await self._send_teams(input_data)
        else:
            return SendNotificationOutput(
                success=False, message_id=None, error=f"Unsupported channel: {channel}"
            )

    async def _send_email(self, input_data: SendNotificationInput) -> SendNotificationOutput:
        """Send email via SendGrid."""
        client = self._get_client()

        try:
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                "Authorization": f"Bearer {self.sendgrid_api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "personalizations": [{"to": [{"email": input_data.recipient}]}],
                "from": {"email": self.from_email},
                "subject": input_data.subject,
                "content": [{"type": "text/plain", "value": input_data.message}],
            }

            response = await client.post(url, headers=headers, json=payload)
            success = response.status_code == 202

            return SendNotificationOutput(
                success=success,
                message_id=response.headers.get("X-Message-Id") if success else None,
                error=response.text if not success else None,
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return SendNotificationOutput(success=False, message_id=None, error="EMAIL_SEND_ERROR")

    async def _send_slack(self, input_data: SendNotificationInput) -> SendNotificationOutput:
        """Send Slack message via API."""
        client = self._get_client()

        try:
            # recipient is channel ID or user ID
            url = "https://slack.com/api/chat.postMessage"
            headers = {"Authorization": f"Bearer {self.slack_bot_token}"}

            payload = {
                "channel": input_data.recipient,
                "text": f"*{input_data.subject}*\n{input_data.message}",
            }

            response = await client.post(url, headers=headers, data=payload)
            data = response.json()
            success = data.get("ok", False)

            return SendNotificationOutput(
                success=success,
                message_id=data.get("ts") if success else None,
                error=data.get("error") if not success else None,
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Slack send failed: {e}")
            return SendNotificationOutput(success=False, message_id=None, error="EMAIL_SEND_ERROR")

    async def _send_teams(self, input_data: SendNotificationInput) -> SendNotificationOutput:
        """Send Teams message via webhook."""
        client = self._get_client()

        try:
            payload = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "title": input_data.subject,
                "text": input_data.message,
            }

            response = await client.post(self.teams_webhook_url, json=payload)
            success = response.status_code == 200

            return SendNotificationOutput(
                success=success, message_id=None, error=response.text if not success else None
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Teams send failed: {e}")
            return SendNotificationOutput(success=False, message_id=None, error="EMAIL_SEND_ERROR")


class CreateTaskTool(BaseTool):
    """Create tasks in project management systems (Asana, Monday, ClickUp)."""

    name = "create_task"
    category = ToolCategory.INTEGRATION
    description = "Creates tasks in project management systems"
    input_schema = CreateTaskInput
    output_schema = CreateTaskOutput
    timeout_seconds = 10
    requires_auth = True

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.pm_provider = config.get("pm_provider", "asana") if config else "asana"
        self.api_key = config.get("pm_api_key") if config else None
        self.workspace_id = config.get("pm_workspace_id") if config else None
        self.project_id = config.get("pm_project_id") if config else None
        self._client = None

    def _get_client(self):
        """Get HTTP client."""
        if self._client is None:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            self._client = httpx.AsyncClient(headers=headers, timeout=30.0)
        return self._client

    async def execute(self, input_data: CreateTaskInput) -> CreateTaskOutput:
        """Create task in PM system."""
        client = self._get_client()

        try:
            if self.pm_provider == "asana":
                return await self._create_asana_task(client, input_data)
            elif self.pm_provider == "monday":
                return await self._create_monday_task(client, input_data)
            elif self.pm_provider == "clickup":
                return await self._create_clickup_task(client, input_data)
            else:
                raise ValueError(f"Unsupported PM provider: {self.pm_provider}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Task creation failed: {e}")
            return CreateTaskOutput(task_id="", success=False, url="", error="TASK_CREATE_ERROR")

    async def _create_asana_task(
        self, client: httpx.AsyncClient, input_data: CreateTaskInput
    ) -> CreateTaskOutput:
        """Create task in Asana."""
        url = "https://app.asana.com/api/1.0/tasks"

        payload = {
            "data": {
                "name": input_data.title,
                "notes": input_data.description,
                "projects": [self.project_id] if self.project_id else [],
                "assignee": input_data.assignee,
                "due_on": input_data.due_date,
            }
        }

        response = await client.post(url, json=payload)
        data = response.json()

        if response.status_code == 201:
            task_id = data.get("data", {}).get("gid")
            return CreateTaskOutput(
                task_id=task_id,
                success=True,
                url=f"https://app.asana.com/0/{self.project_id}/{task_id}",
                error=None,
            )
        else:
            return CreateTaskOutput(task_id="", success=False, url="", error=data.get("errors"))

    async def _create_monday_task(
        self, client: httpx.AsyncClient, input_data: CreateTaskInput
    ) -> CreateTaskOutput:
        """Create task in Monday.com."""
        url = "https://api.monday.com/v2"

        # Monday uses GraphQL
        query = f"""
        mutation {{
            create_item(
                board_id: {self.project_id},
                item_name: "{input_data.title}"
            ) {{
                id
            }}
        }}
        """

        payload = {"query": query}
        response = await client.post(url, json=payload)
        data = response.json()

        if "data" in data and "create_item" in data["data"]:
            task_id = data["data"]["create_item"]["id"]
            return CreateTaskOutput(
                task_id=task_id,
                success=True,
                url=f"https://monday.com/boards/{self.project_id}/{task_id}",
                error=None,
            )
        else:
            return CreateTaskOutput(
                task_id="", success=False, url="", error=str(data.get("errors"))
            )

    async def _create_clickup_task(
        self, client: httpx.AsyncClient, input_data: CreateTaskInput
    ) -> CreateTaskOutput:
        """Create task in ClickUp."""
        url = f"https://api.clickup.com/api/v2/list/{self.project_id}/task"

        payload = {
            "name": input_data.title,
            "description": input_data.description,
            "assignees": [input_data.assignee] if input_data.assignee else [],
            "due_date": input_data.due_date,
        }

        response = await client.post(url, json=payload)
        data = response.json()

        if response.status_code == 200:
            task_id = data.get("id")
            return CreateTaskOutput(
                task_id=task_id,
                success=True,
                url=f"https://app.clickup.com/t/{task_id}",
                error=None,
            )
        else:
            return CreateTaskOutput(task_id="", success=False, url="", error=data.get("err"))


class ScheduleMeetingTool(BaseTool):
    """Schedule meetings using calendar APIs (Google Calendar, Outlook)."""

    name = "schedule_meeting"
    category = ToolCategory.INTEGRATION
    description = "Schedules meetings with attendees using calendar APIs"
    input_schema = ScheduleMeetingInput
    output_schema = ScheduleMeetingOutput
    timeout_seconds = 20
    requires_auth = True

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.calendar_provider = config.get("calendar_provider", "google") if config else "google"
        self.api_key = config.get("calendar_api_key") if config else None
        self.access_token = config.get("calendar_access_token") if config else None
        self._client = None

    def _get_client(self):
        """Get HTTP client."""
        if self._client is None:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            self._client = httpx.AsyncClient(headers=headers, timeout=30.0)
        return self._client

    async def execute(self, input_data: ScheduleMeetingInput) -> ScheduleMeetingOutput:
        """Schedule meeting via calendar API."""
        client = self._get_client()

        try:
            if self.calendar_provider == "google":
                return await self._schedule_google_meeting(client, input_data)
            elif self.calendar_provider == "outlook":
                return await self._schedule_outlook_meeting(client, input_data)
            else:
                raise ValueError(f"Unsupported calendar provider: {self.calendar_provider}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Meeting scheduling failed: {e}")
            return ScheduleMeetingOutput(
                meeting_id="", scheduled_time="", calendar_link="", success=False, error="MEETING_SCHEDULE_ERROR"
            )

    async def _schedule_google_meeting(
        self, client: httpx.AsyncClient, input_data: ScheduleMeetingInput
    ) -> ScheduleMeetingOutput:
        """Schedule meeting via Google Calendar API."""
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

        # Parse duration
        duration_minutes = input_data.duration_minutes or 30
        start_time = input_data.preferred_time or datetime.now(UTC).isoformat()

        end_time = datetime.fromisoformat(start_time.replace("Z", "+00:00")) + timedelta(
            minutes=duration_minutes
        )

        payload = {
            "summary": input_data.subject,
            "description": input_data.description,
            "start": {"dateTime": start_time, "timeZone": "UTC"},
            "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
            "attendees": [{"email": email} for email in input_data.attendees],
            "conferenceData": {
                "createRequest": {"requestId": f"meet-{datetime.now(UTC).timestamp()}"}
            },
        }

        response = await client.post(url, json=payload, params={"conferenceDataVersion": 1})
        data = response.json()

        if response.status_code == 200:
            return ScheduleMeetingOutput(
                meeting_id=data.get("id"),
                scheduled_time=start_time,
                calendar_link=data.get("htmlLink"),
                success=True,
                error=None,
            )
        else:
            return ScheduleMeetingOutput(
                meeting_id="",
                scheduled_time="",
                calendar_link="",
                success=False,
                error=data.get("error", {}).get("message", "Unknown error"),
            )

    async def _schedule_outlook_meeting(
        self, client: httpx.AsyncClient, input_data: ScheduleMeetingInput
    ) -> ScheduleMeetingOutput:
        """Schedule meeting via Microsoft Graph API."""
        url = "https://graph.microsoft.com/v1.0/me/events"

        duration_minutes = input_data.duration_minutes or 30
        start_time = input_data.preferred_time or datetime.now(UTC).isoformat()
        end_time = datetime.fromisoformat(start_time.replace("Z", "+00:00")) + timedelta(
            minutes=duration_minutes
        )

        payload = {
            "subject": input_data.subject,
            "body": {"contentType": "text", "content": input_data.description},
            "start": {"dateTime": start_time, "timeZone": "UTC"},
            "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
            "attendees": [
                {"emailAddress": {"address": email}, "type": "required"}
                for email in input_data.attendees
            ],
        }

        response = await client.post(url, json=payload)
        data = response.json()

        if response.status_code == 201:
            return ScheduleMeetingOutput(
                meeting_id=data.get("id"),
                scheduled_time=start_time,
                calendar_link=data.get("webLink"),
                success=True,
                error=None,
            )
        else:
            return ScheduleMeetingOutput(
                meeting_id="",
                scheduled_time="",
                calendar_link="",
                success=False,
                error=data.get("error", {}).get("message", "Unknown error"),
            )


class ExportToCRMTool(BaseTool):
    """Export notes, documents, or activities to CRM (Salesforce/HubSpot)."""

    name = "export_to_crm"
    category = ToolCategory.INTEGRATION
    description = "Exports notes, documents, or activities to CRM systems"
    input_schema = ExportToCRMInput
    output_schema = ExportToCRMOutput
    timeout_seconds = 15
    requires_auth = True

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.crm_type = config.get("crm_type", "salesforce") if config else "salesforce"
        self.api_key = config.get("crm_api_key") if config else None
        self.instance_url = config.get("crm_instance_url") if config else None
        self._client = None

    def _get_client(self):
        """Get HTTP client with auth headers."""
        if self._client is None:
            headers = {}
            if self.crm_type == "salesforce" or self.crm_type == "hubspot":
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(headers=headers, timeout=30.0)
        return self._client

    async def execute(self, input_data: ExportToCRMInput) -> ExportToCRMOutput:
        """Export to CRM."""
        client = self._get_client()

        try:
            if self.crm_type == "salesforce":
                return await self._export_to_salesforce(client, input_data)
            elif self.crm_type == "hubspot":
                return await self._export_to_hubspot(client, input_data)
            else:
                raise ValueError(f"Unsupported CRM type: {self.crm_type}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"CRM export failed: {e}")
            return ExportToCRMOutput(crm_record_id="", success=False, url="", error="CRM_EXPORT_ERROR")

    async def _export_to_salesforce(
        self, client: httpx.AsyncClient, input_data: ExportToCRMInput
    ) -> ExportToCRMOutput:
        """Export to Salesforce."""
        prospect_id = input_data.prospect_id
        entity_type = input_data.entity_type

        if entity_type == "note":
            url = f"{self.instance_url}/services/data/v58.0/sobjects/Note"
            payload = {
                "ParentId": prospect_id,
                "Title": input_data.entity_data.get("title", "Note from Value Fabric"),
                "Body": input_data.entity_data.get("content", ""),
            }
        elif entity_type == "task":
            url = f"{self.instance_url}/services/data/v58.0/sobjects/Task"
            payload = {
                "WhatId": prospect_id,
                "Subject": input_data.entity_data.get("title", "Task from Value Fabric"),
                "Description": input_data.entity_data.get("content", ""),
            }
        else:
            url = f"{self.instance_url}/services/data/v58.0/sobjects/ContentVersion"
            payload = {
                "Title": input_data.entity_data.get("title", "Document"),
                "PathOnClient": input_data.entity_data.get("filename", "document.pdf"),
                "VersionData": input_data.entity_data.get("content", ""),
            }

        response = await client.post(url, json=payload)
        data = response.json()

        if response.status_code in [200, 201]:
            record_id = data.get("id")
            return ExportToCRMOutput(
                crm_record_id=record_id,
                success=True,
                url=f"{self.instance_url}/{record_id}",
                error=None,
            )
        else:
            return ExportToCRMOutput(
                crm_record_id="", success=False, url="", error=data.get("message", "Export failed")
            )

    async def _export_to_hubspot(
        self, client: httpx.AsyncClient, input_data: ExportToCRMInput
    ) -> ExportToCRMOutput:
        """Export to HubSpot."""
        prospect_id = input_data.prospect_id
        entity_type = input_data.entity_type

        if entity_type == "note":
            url = "https://api.hubapi.com/engagements/v1/engagements"
            payload = {
                "engagement": {
                    "type": "NOTE",
                    "timestamp": int(datetime.now(UTC).timestamp() * 1000),
                },
                "associations": {"companyIds": [prospect_id]},
                "metadata": {"body": input_data.entity_data.get("content", "")},
            }
        elif entity_type == "task":
            url = "https://api.hubapi.com/engagements/v1/engagements"
            payload = {
                "engagement": {
                    "type": "TASK",
                    "timestamp": int(datetime.now(UTC).timestamp() * 1000),
                },
                "associations": {"companyIds": [prospect_id]},
                "metadata": {
                    "subject": input_data.entity_data.get("title", "Task"),
                    "body": input_data.entity_data.get("content", ""),
                },
            }
        else:
            # HubSpot file upload
            url = "https://api.hubapi.com/files/v3/files"
            payload = {
                "fileName": input_data.entity_data.get("filename", "document.pdf"),
                "folderPath": "/services-exports",
            }

        response = await client.post(url, json=payload)
        data = response.json()

        if response.status_code in [200, 201]:
            record_id = (
                data.get("engagement", {}).get("id") if "engagement" in data else data.get("id")
            )
            return ExportToCRMOutput(
                crm_record_id=str(record_id) if record_id else "",
                success=True,
                url=f"https://app.hubspot.com/contacts/{prospect_id}",
                error=None,
            )
        else:
            return ExportToCRMOutput(
                crm_record_id="",
                success=False,
                url="",
                error=str(data.get("message", "Export failed")),
            )
