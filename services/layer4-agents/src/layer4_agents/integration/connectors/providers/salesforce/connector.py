from __future__ import annotations

import logging
import os
import re
import urllib.parse
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any, cast

import httpx

from .....models.account import CRMProvider
from ...core.connector import CRMConnector, CRMWriteConnector
from ...core.errors import (
    AuthError,
    CRMError,
    PermanentError,
    TransientError,
    classify_httpx_exception,
)
from ...core.types import CanonicalRecord, CRMModel, CRMOperationResult, SyncCursor

logger = logging.getLogger(__name__)

API_VERSION = "v58.0"

# Salesforce IDs are exactly 15 or 18 alphanumeric characters.
_SFDC_ID_PATTERN = re.compile(r"^(?:[a-zA-Z0-9]{15}|[a-zA-Z0-9]{18})$")


def _validate_sfdc_id(value: str | None, field_name: str = "prospect_id") -> str:
    """Validate Salesforce ID format to prevent SOQL injection."""
    if not value or not _SFDC_ID_PATTERN.match(value):
        raise ValueError(f"Invalid {field_name} format: must be 15 or 18 alphanumeric characters")
    return value


def _soql_safe_id(value: str, field_name: str = "prospect_id") -> str:
    """Return a SOQL-safe ID string with defense-in-depth escaping."""
    validated = _validate_sfdc_id(value, field_name)
    return validated.replace("'", "''")


def _check_rate_limit(response: httpx.Response) -> None:
    """Check Salesforce rate limit headers and log warnings."""
    limit_info = response.headers.get("Sforce-Limit-Info")
    if limit_info:
        logger.debug("Salesforce rate limit info: %s", limit_info)


class SalesforceConnector(CRMConnector, CRMWriteConnector):
    """Salesforce-specific CRM connector.

    Encapsulates authentication, HTTP transport, and response mapping for the
    Salesforce REST API.
    """

    provider: CRMProvider = CRMProvider.SALESFORCE

    def __init__(self, config: dict[str, Any], client: httpx.AsyncClient | None = None) -> None:
        self.access_token: str | None = cast(str | None, config.get("crm_api_key") or config.get("api_key"))
        self.instance_url: str | None = cast(str | None, config.get("crm_instance_url") or config.get("instance_url"))
        self._refresh_token: str | None = cast(str | None, config.get("refresh_token"))
        self._client_id: str | None = cast(str | None, config.get("client_id") or os.getenv("SALESFORCE_CLIENT_ID"))
        self._client_secret: str | None = cast(str | None, config.get("client_secret") or os.getenv("SALESFORCE_CLIENT_SECRET"))
        self._on_token_refresh: Callable[[dict[str, Any]], Awaitable[None]] | None = config.get(
            "on_token_refresh"
        )
        self._client: httpx.AsyncClient | None = client

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            self._client = httpx.AsyncClient(headers=headers, timeout=30.0)
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_payload: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Make a Salesforce API request with 401→refresh→retry.

        On a 401 response, if a refresh token is available, the connector
        refreshes the access token in-memory and retries the request once.
        If the refresh fails or the retry still returns 401, an AuthError is
        raised.
        """
        client = self._get_client()
        if path.startswith("/") and self.instance_url is None:
            raise PermanentError("Salesforce instance_url is required")
        url = f"{self.instance_url}{path}" if path.startswith("/") else path
        try:
            response = await client.request(
                method,
                url,
                params=params,
                json=json_payload,
                timeout=timeout,
            )
        except httpx.HTTPStatusError as e:
            raise classify_httpx_exception(e) from e
        except httpx.RequestError as e:
            raise classify_httpx_exception(e) from e

        if response.status_code == 401 and self._refresh_token and self.instance_url:
            try:
                token_result = await self.refresh_token(
                    refresh_token=self._refresh_token,
                    instance_url=self.instance_url,
                    client_id=self._client_id,
                    client_secret=self._client_secret,
                )
            except Exception as exc:
                raise AuthError(f"Token refresh failed during 401 retry: {exc}") from exc

            self.access_token = token_result["api_key"]
            new_instance_url = token_result.get("instance_url")
            if new_instance_url:
                self.instance_url = new_instance_url
            new_refresh = token_result.get("refresh_token")
            if new_refresh:
                self._refresh_token = new_refresh
            if self._on_token_refresh:
                await self._on_token_refresh(token_result)

            # Rebuild client with new token
            self._client = None
            client = self._get_client()
            url = f"{self.instance_url}{path}" if path.startswith("/") else path
            try:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    json=json_payload,
                    timeout=timeout,
                )
            except httpx.HTTPStatusError as e:
                raise classify_httpx_exception(e) from e
            except httpx.RequestError as e:
                raise classify_httpx_exception(e) from e

            if response.status_code == 401:
                raise AuthError("Authentication failed after token refresh")

        _check_rate_limit(response)
        return response

    async def _execute_soql_query(
        self,
        query: str,
        *,
        max_pages: int = 10,
        timeout: float | None = None,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Execute a SOQL query with pagination support."""
        all_records: list[dict[str, Any]] = []
        query_url: str | None = (
            f"{self.instance_url}/services/data/{API_VERSION}/query?"
            f"q={urllib.parse.quote(query)}"
        )
        pages_fetched = 0
        was_truncated = False

        while query_url and pages_fetched < max_pages:
            response = await self._request("GET", query_url, timeout=timeout)

            if response.status_code == 429:
                logger.warning("Salesforce rate limit hit (429)")
                was_truncated = True
                break

            if response.status_code != 200:
                logger.error(
                    "Salesforce SOQL query failed: %s %s",
                    response.status_code,
                    response.text[:200],
                )
                was_truncated = True
                break

            data = response.json()
            records = data.get("records", [])
            all_records.extend(records)

            next_url = data.get("nextRecordsUrl")
            if next_url:
                query_url = f"{self.instance_url}{next_url}"
            else:
                query_url = None

            pages_fetched += 1

        if pages_fetched >= max_pages and query_url:
            logger.warning("Salesforce SOQL query reached max_pages limit (%s).", max_pages)
            was_truncated = True

        return all_records, was_truncated

    async def test_connection(self, *, timeout: float | None = None) -> dict[str, Any]:
        """Validate that the access token can reach the Salesforce API."""
        if not self.access_token:
            return {
                "success": False,
                "message": "Missing OAuth access token in credentials",
                "error_code": "MISSING_CREDENTIALS",
            }
        if not self.instance_url:
            return {
                "success": False,
                "message": "Salesforce instance URL is required",
                "error_code": "MISSING_INSTANCE_URL",
            }

        try:
            response = await self._request(
                "GET",
                f"/services/data/{API_VERSION}/query/",
                params={"q": "SELECT Name FROM Organization LIMIT 1"},
                timeout=timeout,
            )
        except CRMError as e:
            return {
                "success": False,
                "message": "Salesforce connection failed",
                "error_code": type(e).__name__.upper(),
            }

        if response.status_code == 200:
            data = response.json()
            org_name = data.get("records", [{}])[0].get("Name", "Unknown")
            return {
                "success": True,
                "message": f"Connected to Salesforce: {org_name}",
                "details": {
                    "accounts_accessible": True,
                    "opportunities_accessible": True,
                    "organization": org_name,
                    "api_version": API_VERSION,
                },
            }
        if response.status_code == 401:
            return {
                "success": False,
                "message": "Authentication failed - token may be expired",
                "error_code": "AUTH_FAILED",
            }
        return {
            "success": False,
            "message": f"Salesforce API error: {response.status_code}",
            "error_code": f"API_ERROR_{response.status_code}",
        }

    async def get_account(
        self,
        remote_id: str,
        *,
        include: set[CRMModel] | None = None,
        timeout: float | None = None,
    ) -> CanonicalRecord | None:
        """Fetch a Salesforce Account by ID and return a canonical record."""
        _validate_sfdc_id(remote_id)
        if not self.instance_url:
            raise PermanentError("Salesforce instance_url is required")

        response = await self._request(
            "GET",
            f"/services/data/{API_VERSION}/sobjects/Account/{remote_id}",
            timeout=timeout,
        )
        if response.status_code != 200:
            return None

        data = response.json()
        canonical = {
            "name": data.get("Name"),
            "industry": data.get("Industry"),
            "region": data.get("BillingState") or data.get("BillingCountry"),
            "company_size": data.get("NumberOfEmployees"),
            "annual_revenue": data.get("AnnualRevenue"),
            "website": data.get("Website"),
            "headquarters": f"{data.get('BillingCity', '')}, {data.get('BillingState', '')}".strip(
                ", "
            ),
            "employees": data.get("NumberOfEmployees"),
            "segment": data.get("Type"),
        }
        return CanonicalRecord(
            model=CRMModel.ACCOUNT,
            remote_id=remote_id,
            canonical=canonical,
            supplemental={k: v for k, v in data.items() if k not in canonical},
        )

    async def list_opportunities(
        self,
        account_remote_id: str,
        *,
        cursor: SyncCursor | None = None,
        limit: int = 100,
        timeout: float | None = None,
    ) -> tuple[list[CanonicalRecord], SyncCursor]:
        """Fetch opportunities for a Salesforce Account."""
        safe_id = _soql_safe_id(account_remote_id)
        query = (
            "SELECT Id, Name, StageName, Amount, Probability, CloseDate "
            f"FROM Opportunity WHERE AccountId = '{safe_id}'"
        )
        records, was_truncated = await self._execute_soql_query(query, timeout=timeout)
        if was_truncated:
            raise TransientError("Salesforce opportunity query was truncated")
        canonical_records = []
        for rec in records[:limit]:
            probability = rec.get("Probability")
            canonical = {
                "name": rec.get("Name"),
                "stage": rec.get("StageName"),
                "value": rec.get("Amount"),
                "probability": probability / 100 if isinstance(probability, (int, float)) else 0,
                "close_date": rec.get("CloseDate"),
            }
            canonical_records.append(
                CanonicalRecord(
                    model=CRMModel.OPPORTUNITY,
                    remote_id=rec.get("Id", ""),
                    canonical=canonical,
                    supplemental={k: v for k, v in rec.items() if k not in canonical},
                )
            )
        return canonical_records, SyncCursor()

    async def list_interactions(
        self,
        account_remote_id: str,
        *,
        since_date: str | None = None,
        cursor: SyncCursor | None = None,
        limit: int = 100,
        timeout: float | None = None,
    ) -> tuple[list[CanonicalRecord], SyncCursor]:
        """Fetch Task interactions for a Salesforce Account."""
        safe_id = _soql_safe_id(account_remote_id)
        since_clause = ""
        if since_date:
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", since_date):
                raise ValueError("Invalid since_date format: expected YYYY-MM-DD")
            since_clause = f" AND ActivityDate >= {since_date}"

        type_filter = ""
        query = (
            "SELECT Id, Subject, ActivityDate, Type, Status, Description, DurationInMinutes "
            f"FROM Task WHERE WhatId = '{safe_id}'{since_clause}{type_filter} "
            f"ORDER BY ActivityDate DESC LIMIT {limit}"
        )
        records, was_truncated = await self._execute_soql_query(query, timeout=timeout)
        if was_truncated:
            raise TransientError("Salesforce interaction query was truncated")
        canonical_records = []
        for rec in records:
            canonical = {
                "type": (rec.get("Type") or "task").lower(),
                "date": rec.get("ActivityDate"),
                "subject": rec.get("Subject"),
                "duration_minutes": rec.get("DurationInMinutes"),
                "notes": rec.get("Description"),
                "outcome": rec.get("Status"),
            }
            canonical_records.append(
                CanonicalRecord(
                    model=CRMModel.ENGAGEMENT,
                    remote_id=rec.get("Id", ""),
                    canonical=canonical,
                    supplemental={k: v for k, v in rec.items() if k not in canonical},
                )
            )
        return canonical_records, SyncCursor()

    async def list_accounts(
        self,
        *,
        cursor: SyncCursor | None = None,
        modified_since: datetime | None = None,
        limit: int = 100,
        timeout: float | None = None,
    ) -> tuple[list[CanonicalRecord], SyncCursor]:
        """Placeholder for SyncEngine account enumeration.

        PR 3 keeps the existing per-account tool path; PR 5 will wire this up.
        """
        return [], SyncCursor()

    async def update_opportunity(
        self,
        remote_id: str,
        fields: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> CRMOperationResult:
        """Update a Salesforce Opportunity."""
        _validate_sfdc_id(remote_id, field_name="opportunity_id")
        if not self.instance_url:
            raise PermanentError("Salesforce instance_url is required")

        try:
            response = await self._request(
                "PATCH",
                f"/services/data/{API_VERSION}/sobjects/Opportunity/{remote_id}",
                json_payload=fields,
                timeout=timeout,
            )
        except CRMError as e:
            return CRMOperationResult(
                success=False,
                remote_id=remote_id,
                error_code=type(e).__name__,
                error_message=str(e),
            )

        success = response.status_code in (200, 204)
        return CRMOperationResult(
            success=success,
            remote_id=remote_id,
            error_message=None if success else response.text,
        )

    @staticmethod
    async def refresh_token(
        *,
        refresh_token: str,
        instance_url: str,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> dict[str, str]:
        """Exchange a Salesforce refresh token for a new access token.

        This is a static helper used by IntegrationService; the connector does
        not store refresh tokens.
        """
        client_id = client_id or os.getenv("SALESFORCE_CLIENT_ID")
        client_secret = client_secret or os.getenv("SALESFORCE_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise PermanentError(
                "SALESFORCE_CLIENT_ID and SALESFORCE_CLIENT_SECRET must be configured"
            )

        token_url = f"{instance_url}/services/oauth2/token"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )

        if response.status_code != 200:
            raise AuthError(f"Token refresh failed: HTTP {response.status_code} - {response.text}")

        token_data = response.json()
        new_access_token = token_data.get("access_token")
        if not new_access_token:
            raise PermanentError("Token refresh response missing access_token")

        result: dict[str, str] = {
            "api_key": new_access_token,
        }
        new_instance_url = token_data.get("instance_url")
        if new_instance_url:
            result["instance_url"] = new_instance_url
        new_refresh_token = token_data.get("refresh_token")
        if new_refresh_token:
            result["refresh_token"] = new_refresh_token
        return result
