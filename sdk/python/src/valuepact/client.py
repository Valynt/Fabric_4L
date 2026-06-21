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
        return dict(self.request("GET", "/v1/auth/cli/whoami"))

    def verify_tenant_access(self, tenant_id: str, *, scopes: set[str]) -> dict[str, Any]:
        payload = self.request(
            "POST",
            "/v1/auth/cli/tenant-access",
            json={"tenant_id": tenant_id, "required_scopes": sorted(scopes)},
        )
        if not payload.get("authorized", False):
            raise PermissionError("The current identity is not authorized for this tenant.")
        return dict(payload)

    def health(self) -> dict[str, Any]:
        return dict(self.request("GET", "/health"))

    def list_tenants(self) -> Any:
        return self.request("GET", "/v1/tenants")

    def get_tenant(self, tenant_id: str) -> Any:
        return self.request("GET", f"/v1/tenants/{tenant_id}")

    def list_workspaces(self, tenant_id: str) -> Any:
        return self.request("GET", "/v1/workspaces", params={"tenant_id": tenant_id})

    def get_workspace(self, tenant_id: str, workspace_id: str) -> Any:
        return self.request(
            "GET",
            f"/v1/workspaces/{workspace_id}",
            params={"tenant_id": tenant_id},
        )

    def execute_workspace(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        request_id: str,
        input_payload: dict[str, Any],
        dry_run: bool,
    ) -> Any:
        return self.request(
            "POST",
            f"/v1/workspaces/{workspace_id}/executions",
            json={
                "tenant_id": tenant_id,
                "input": input_payload,
                "request_id": request_id,
                "dry_run": dry_run,
            },
        )

    def list_executions(self, tenant_id: str) -> Any:
        return self.request("GET", "/v1/executions", params={"tenant_id": tenant_id})

    def get_execution(self, tenant_id: str, execution_id: str) -> Any:
        return self.request(
            "GET",
            f"/v1/executions/{execution_id}",
            params={"tenant_id": tenant_id},
        )

    def execution_logs(self, tenant_id: str, execution_id: str) -> Any:
        return self.request(
            "GET",
            f"/v1/executions/{execution_id}/logs",
            params={"tenant_id": tenant_id},
        )

    def cancel_execution(self, tenant_id: str, execution_id: str, request_id: str) -> Any:
        return self.request(
            "POST",
            f"/v1/executions/{execution_id}/cancel",
            json={"tenant_id": tenant_id, "request_id": request_id},
        )

    def list_audit_events(self, tenant_id: str, since: str | None) -> Any:
        params = {"tenant_id": tenant_id}
        if since:
            params["since"] = since
        return self.request("GET", "/v1/audit/events", params=params)

    def close(self) -> None:
        self._client.close()
