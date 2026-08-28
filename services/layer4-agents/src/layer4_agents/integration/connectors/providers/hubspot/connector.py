from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

import httpx

from .....models.account import CRMProvider
from ...core.connector import CRMConnector, CRMWriteConnector
from ...core.errors import CRMError, classify_httpx_exception
from ...core.types import CanonicalRecord, CRMModel, CRMOperationResult, SyncCursor

logger = logging.getLogger(__name__)

API_VERSION = "v3"


class HubSpotConnector(CRMConnector, CRMWriteConnector):
    """HubSpot-specific CRM connector.

    Encapsulates authentication, HTTP transport, and response mapping for the
    HubSpot CRM and Engagements APIs.
    """

    provider: CRMProvider = CRMProvider.HUBSPOT

    def __init__(
        self, config: dict[str, Any], client: httpx.AsyncClient | None = None
    ) -> None:
        self.access_token = config.get("crm_api_key") or config.get("api_key")
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
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_payload: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Make a HubSpot API request and translate httpx errors."""
        client = self._get_client()
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
        return response

    async def test_connection(self, *, timeout: float | None = None) -> dict[str, Any]:
        """Validate that the access token can reach the HubSpot API."""
        if not self.access_token:
            return {
                "success": False,
                "message": "Missing API key in credentials",
                "error_code": "MISSING_CREDENTIALS",
            }

        try:
            response = await self._request(
                "GET",
                f"https://api.hubapi.com/account-info/{API_VERSION}/details",
                timeout=timeout,
            )
        except CRMError as e:
            return {
                "success": False,
                "message": "HubSpot connection failed",
                "error_code": type(e).__name__.upper(),
            }

        if response.status_code == 200:
            data = response.json()
            portal_name = data.get("portalName", "Unknown")
            return {
                "success": True,
                "message": f"Connected to HubSpot: {portal_name}",
                "details": {
                    "accounts_accessible": True,
                    "opportunities_accessible": True,
                    "portal_name": portal_name,
                    "api_version": API_VERSION,
                },
            }
        if response.status_code == 401:
            return {
                "success": False,
                "message": "Authentication failed - API key may be invalid",
                "error_code": "AUTH_FAILED",
            }
        return {
            "success": False,
            "message": f"HubSpot API error: {response.status_code}",
            "error_code": f"API_ERROR_{response.status_code}",
        }

    async def get_account(
        self,
        remote_id: str,
        *,
        include: set[CRMModel] | None = None,
        timeout: float | None = None,
    ) -> CanonicalRecord | None:
        """Fetch a HubSpot Company by ID and return a canonical record."""
        url = f"https://api.hubapi.com/crm/{API_VERSION}/objects/companies/{remote_id}"
        response = await self._request("GET", url, timeout=timeout)
        if response.status_code != 200:
            return None

        data = response.json()
        props = data.get("properties", {})
        canonical = {
            "name": props.get("name"),
            "industry": props.get("industry"),
            "region": props.get("state") or props.get("country"),
            "company_size": props.get("numberofemployees"),
            "annual_revenue": props.get("annualrevenue"),
            "website": props.get("website"),
            "headquarters": props.get("address"),
            "employees": props.get("numberofemployees"),
            "domain": props.get("domain"),
            "segment": props.get("type") or props.get("hs_lead_status"),
        }
        return CanonicalRecord(
            model=CRMModel.ACCOUNT,
            remote_id=remote_id,
            canonical=canonical,
            supplemental={k: v for k, v in props.items() if k not in canonical},
        )

    async def list_opportunities(
        self,
        account_remote_id: str,
        *,
        cursor: SyncCursor | None = None,
        limit: int = 100,
        timeout: float | None = None,
    ) -> tuple[list[CanonicalRecord], SyncCursor]:
        """Fetch deals associated with a HubSpot company."""
        associations_url = (
            f"https://api.hubapi.com/crm/{API_VERSION}/objects/companies/"
            f"{account_remote_id}/associations/deals"
        )
        assoc_response = await self._request("GET", associations_url, timeout=timeout)
        if assoc_response.status_code != 200:
            return [], SyncCursor()

        assoc_data = assoc_response.json()
        deal_ids = [r.get("toObjectId") for r in assoc_data.get("results", [])]

        async def _fetch_deal(deal_id: str) -> CanonicalRecord | None:
            deal_url = f"https://api.hubapi.com/crm/{API_VERSION}/objects/deals/{deal_id}"
            deal_response = await self._request("GET", deal_url, timeout=timeout)
            if deal_response.status_code != 200:
                return None
            props = deal_response.json().get("properties", {})
            canonical = {
                "name": props.get("dealname", "Untitled Deal"),
                "stage": props.get("dealstage", "unknown"),
                "value": float(props.get("amount", 0)) if props.get("amount") else 0,
                "probability": float(props.get("probability", 0)) / 100 if props.get("probability") else 0,
                "close_date": props.get("closedate"),
                "pipeline": props.get("pipeline"),
            }
            return CanonicalRecord(
                model=CRMModel.OPPORTUNITY,
                remote_id=str(deal_id),
                canonical=canonical,
                supplemental={k: v for k, v in props.items() if k not in canonical},
            )

        deal_results = await asyncio.gather(
            *[_fetch_deal(str(did)) for did in deal_ids[:50]]
        )
        records = [d for d in deal_results if d is not None]
        return records, SyncCursor()

    async def list_interactions(
        self,
        account_remote_id: str,
        *,
        since_date: str | None = None,
        cursor: SyncCursor | None = None,
        limit: int = 100,
        timeout: float | None = None,
    ) -> tuple[list[CanonicalRecord], SyncCursor]:
        """Fetch engagements associated with a HubSpot company."""
        url = (
            f"https://api.hubapi.com/engagements/v1/engagements/associated/COMPANY/"
            f"{account_remote_id}/paged"
        )
        response = await self._request("GET", url, timeout=timeout)
        if response.status_code != 200:
            return [], SyncCursor()

        data = response.json()
        records = []
        for eng in data.get("results", [])[:limit]:
            metadata = eng.get("engagement", {})
            eng_type = metadata.get("type", "unknown").lower()
            canonical = {
                "type": eng_type,
                "date": metadata.get("createdAt"),
                "subject": metadata.get("subject", ""),
                "outcome": "completed" if metadata.get("active") else "pending",
            }
            if eng_type == "email":
                email_meta = eng.get("metadata", {})
                canonical["subject"] = email_meta.get("subject", "Email")
                from_data = email_meta.get("from")
                canonical["sender"] = (
                    from_data.get("rawEmail") if isinstance(from_data, dict) else None
                )
            elif eng_type == "call":
                call_meta = eng.get("metadata", {})
                duration = call_meta.get("durationMilliseconds")
                canonical["duration_minutes"] = duration // 60000 if duration else None
                canonical["notes"] = call_meta.get("body", "")
            elif eng_type == "meeting":
                meeting_meta = eng.get("metadata", {})
                canonical["subject"] = meeting_meta.get("title", "Meeting")
                duration = meeting_meta.get("durationMillis")
                canonical["duration_minutes"] = duration // 60000 if duration else None
            elif eng_type == "task":
                task_meta = eng.get("metadata", {})
                canonical["subject"] = task_meta.get("subject", "Task")
                canonical["notes"] = task_meta.get("body", "")

            records.append(
                CanonicalRecord(
                    model=CRMModel.ENGAGEMENT,
                    remote_id=str(metadata.get("id", "")),
                    canonical=canonical,
                    supplemental={k: v for k, v in eng.items() if k not in {"engagement", "metadata", "associations"}},
                )
            )
        return records, SyncCursor()

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
        """Update a HubSpot deal."""
        url = f"https://api.hubapi.com/crm/{API_VERSION}/objects/deals/{remote_id}"
        properties = {k: str(v) for k, v in fields.items()}
        try:
            response = await self._request(
                "PATCH",
                url,
                json_payload={"properties": properties},
                timeout=timeout,
            )
        except CRMError as e:
            return CRMOperationResult(
                success=False,
                remote_id=remote_id,
                error_code=type(e).__name__,
                error_message=str(e),
            )

        success = response.status_code == 200
        return CRMOperationResult(
            success=success,
            remote_id=remote_id,
            error_message=None if success else response.text,
        )
