"""Authenticated API adapter used by the ValuePact CLI."""

from __future__ import annotations

from typing import Any

import httpx

from valuefabric.errors import (
    APIError,
    AuthenticationError,
    ConnectionError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)


class ValuePactApiClient:
    """Small remote adapter; server-side APIs remain the security boundary."""

    def __init__(
        self,
        *,
        api_url: str,
        token: str,
        request_id: str | None = None,
        command_name: str | None = None,
        cli_version: str | None = None,
    ) -> None:
        if not api_url.startswith(("http://", "https://")):
            raise ValueError("VALUEPACT_API_URL must start with http:// or https://")
        self.api_url = api_url.rstrip("/")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        if request_id:
            headers["X-Request-ID"] = request_id
        if command_name:
            headers["X-ValuePact-Command"] = command_name
        if cli_version:
            headers["X-ValuePact-CLI-Version"] = cli_version
        self._client = httpx.Client(base_url=self.api_url, headers=headers, timeout=30.0)
        self._identity_cache: dict[str, Any] | None = None

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = self._client.request(method, path, params=params, json=json)
            response.raise_for_status()
            if response.content:
                return response.json()
            return {}
        except httpx.RequestError as exc:
            raise ConnectionError(f"Failed to connect to {self.api_url}: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            self._raise_api_error(exc)

    def _raise_api_error(self, exc: httpx.HTTPStatusError) -> None:
        response = exc.response
        try:
            body = response.json()
        except ValueError:
            body = None
        detail = body.get("detail") if isinstance(body, dict) else None
        message = detail or f"API error ({response.status_code})"
        if response.status_code == 400:
            raise ValidationError(message, response_body=body) from exc
        if response.status_code == 401:
            raise AuthenticationError(message, response_body=body) from exc
        if response.status_code == 403:
            raise PermissionError(message) from exc
        if response.status_code == 404:
            raise NotFoundError(message, response_body=body) from exc
        if response.status_code == 429:
            raise RateLimitError(message, response_body=body) from exc
        raise APIError(message, status_code=response.status_code, response_body=body) from exc

    def identity(self) -> dict[str, Any]:
        if self._identity_cache is None:
            payload = dict(self.request("GET", "/v1/users/me"))
            actor_id = payload.get("actor_id") or payload.get("id") or payload.get("user_id")
            payload["actor_id"] = str(actor_id) if actor_id is not None else ""
            payload.setdefault("actor_type", "user")
            if "tenant_id" in payload and payload["tenant_id"] is not None:
                payload["tenant_id"] = str(payload["tenant_id"])
            self._identity_cache = payload
        return dict(self._identity_cache)

    def verify_tenant_access(self, tenant_id: str, *, scopes: set[str]) -> dict[str, Any]:
        identity = self.identity()
        role = str(identity.get("role") or "")
        authorized = str(identity.get("tenant_id") or "") == tenant_id or role == "super_admin"
        if not authorized:
            raise PermissionError("The current identity is not authorized for this tenant.")
        identity_scopes = set(identity.get("scopes") or [])
        return {"authorized": True, "scopes": sorted(identity_scopes | scopes)}

    def health(self) -> dict[str, Any]:
        return dict(self.request("GET", "/health"))

    def list_tenants(self) -> Any:
        return self.request("GET", "/v1/tenants")

    def get_tenant(self, tenant_id: str) -> Any:
        identity = self.identity()
        if str(identity.get("tenant_id") or "") == tenant_id:
            return self.request("GET", "/v1/tenants/current/settings")
        return self.request("GET", f"/v1/tenants/{tenant_id}")

    def list_workspaces(self, tenant_id: str) -> Any:
        return self.request("GET", "/v1/workflows/types")

    def get_workspace(self, tenant_id: str, workspace_id: str) -> Any:
        payload = self.list_workspaces(tenant_id)
        workspaces = payload.get("workflows", payload) if isinstance(payload, dict) else payload
        if isinstance(workspaces, list):
            for workspace in workspaces:
                if isinstance(workspace, dict) and workspace.get("type") == workspace_id:
                    return workspace
        raise NotFoundError(f"Workspace workflow type not found: {workspace_id}")

    def execute_workspace(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        request_id: str,
        actor_id: str,
        input_payload: dict[str, Any],
        dry_run: bool,
    ) -> Any:
        if dry_run:
            return {
                "tenant_id": tenant_id,
                "workspace_id": workspace_id,
                "status": "dry_run",
                "request_id": request_id,
                "input": input_payload,
            }
        return self.request(
            "POST",
            "/v1/workflows",
            json={
                "workflow_type": workspace_id,
                "tenant_id": tenant_id,
                "user_id": actor_id,
                "inputs": input_payload,
                "priority": "NORMAL",
                "input": input_payload,
                "workflow_id": request_id,
                "request_id": request_id,
            },
        )

    def list_executions(self, tenant_id: str) -> Any:
        return self.request("GET", "/v1/workflows/active")

    def get_execution(self, tenant_id: str, execution_id: str) -> Any:
        return self.request("GET", f"/v1/workflows/{execution_id}")

    def execution_logs(self, tenant_id: str, execution_id: str) -> Any:
        return self.request("GET", f"/v1/workflows/{execution_id}/events")

    def cancel_execution(self, tenant_id: str, execution_id: str, request_id: str) -> Any:
        return self.request(
            "POST",
            f"/v1/workflows/{execution_id}/pause",
            json={
                "tenant_id": tenant_id,
                "request_id": request_id,
                "reason": "Cancelled from ValuePact CLI",
            },
        )

    def list_audit_events(self, tenant_id: str, since: str | None) -> Any:
        params: dict[str, Any] = {}
        if since:
            params["since"] = since
        return self.request("GET", f"/v1/tenants/{tenant_id}/audit-log", params=params)

    def close(self) -> None:
        self._client.close()
