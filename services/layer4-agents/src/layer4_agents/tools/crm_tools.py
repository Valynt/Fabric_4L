from __future__ import annotations

"""CRM tools for Salesforce/HubSpot integration."""


import asyncio
import logging
import re
import urllib.parse
from typing import Any

import httpx

# Salesforce IDs are exactly 15 or 18 alphanumeric characters.
_SFDC_ID_PATTERN = re.compile(r"^(?:[a-zA-Z0-9]{15}|[a-zA-Z0-9]{18})$")

from ..metrics import get_metrics
from ..models.tool_schemas import (
    FetchInteractionHistoryInput,
    FetchInteractionHistoryOutput,
    GetProspectDataInput,
    GetProspectDataOutput,
    ScoreLeadInput,
    ScoreLeadOutput,
    ToolCategory,
    UpdateOpportunityInput,
    UpdateOpportunityOutput,
)
from .registry import BaseTool

logger = logging.getLogger(__name__)


class _SalesforceIdSafetyMixin:
    @staticmethod
    def _validate_sfdc_id(value: str, field_name: str = "prospect_id") -> str:
        """Validate Salesforce ID format to prevent SOQL injection."""
        if not value or not _SFDC_ID_PATTERN.match(value):
            raise ValueError(
                f"Invalid {field_name} format: must be 15 or 18 alphanumeric characters"
            )
        return value

    @classmethod
    def _soql_safe_id(cls, value: str, field_name: str = "prospect_id") -> str:
        """Return a SOQL-safe ID string with defense-in-depth escaping."""
        validated = cls._validate_sfdc_id(value, field_name)
        return validated.replace("'", "''")


class GetProspectDataTool(_SalesforceIdSafetyMixin, BaseTool):
    """Retrieve prospect data from CRM (Salesforce/HubSpot)."""

    name = "get_prospect_data"
    category = ToolCategory.CRM
    description = "Retrieves prospect profile, interactions, and opportunities from CRM"
    input_schema = GetProspectDataInput
    output_schema = GetProspectDataOutput
    timeout_seconds = 15
    requires_auth = True

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.crm_type = config.get("crm_type", "salesforce") if config else "salesforce"
        self.api_key = config.get("crm_api_key") if config else None
        self.api_secret = config.get("crm_api_secret") if config else None
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

    @staticmethod
    def _check_salesforce_rate_limit(response: httpx.Response) -> None:
        """Check Salesforce rate limit headers and log warnings.

        Salesforce returns rate limit info in the Sforce-Limit-Info header.
        Example: api-usage=18/50000
        """
        limit_info = response.headers.get("Sforce-Limit-Info")
        if limit_info:
            logger.debug("Salesforce rate limit info: %s", limit_info)

    async def _execute_soql_query(
        self,
        client: httpx.AsyncClient,
        query: str,
        max_pages: int = 10,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Execute a SOQL query with pagination support.

        Args:
            client: HTTP client
            query: SOQL query string
            max_pages: Maximum number of pages to fetch (safety limit)

        Returns:
            Tuple of (combined records, was_truncated)
        """
        all_records: list[dict[str, Any]] = []
        query_url = f"{self.instance_url}/services/data/v58.0/query?q={urllib.parse.quote(query)}"
        pages_fetched = 0
        was_truncated = False

        while query_url and pages_fetched < max_pages:
            response = await client.get(query_url)

            # Check rate limits
            self._check_salesforce_rate_limit(response)

            if response.status_code == 429:
                logger.warning("Salesforce rate limit hit (429)")
                prom = get_metrics()
                if prom:
                    # Note: tenant_id is not available in the tool context;
                    # the metric will be recorded with 'unknown' tenant_tier.
                    prom.increment_crm_salesforce_rate_limit("unknown")
                # Return what we have so far rather than failing completely
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

            # Check for next page
            next_url = data.get("nextRecordsUrl")
            if next_url:
                query_url = f"{self.instance_url}{next_url}"
            else:
                query_url = None

            pages_fetched += 1

        if pages_fetched >= max_pages and query_url:
            logger.warning(
                "Salesforce SOQL query reached max_pages limit (%s). "
                "Some records may not have been fetched.",
                max_pages,
            )
            was_truncated = True

        return all_records, was_truncated

    async def execute(self, input_data: GetProspectDataInput) -> GetProspectDataOutput:
        """Get prospect data from CRM, falling back to inline prospect_data when unconfigured."""
        # Local / demo environments often have no live CRM.  Use the prospect_data
        # payload passed by the workflow as a synthetic profile so ROI calculations
        # can still run end-to-end without a Salesforce connection.
        if not self.instance_url:
            pd = input_data.prospect_data or {}
            return GetProspectDataOutput(
                profile={
                    "id": input_data.prospect_id,
                    "name": pd.get("name", " Prospect"),
                    "industry": pd.get("industry", ""),
                    "region": pd.get("region", ""),
                    "company_size": pd.get("company_size", pd.get("employees", 0)),
                    "annual_revenue": pd.get("annual_revenue", 0),
                    "website": pd.get("website", ""),
                    "headquarters": pd.get("headquarters", ""),
                    "employees": pd.get("employees", 0),
                    "segment": pd.get("segment", ""),
                },
                interactions=[],
                opportunities=[],
                custom_fields={k: v for k, v in pd.items() if k not in {
                    "name", "industry", "region", "company_size", "annual_revenue",
                    "website", "headquarters", "employees", "segment",
                }},
            )

        client = self._get_client()

        try:
            if self.crm_type == "salesforce":
                return await self._get_salesforce_data(client, input_data)
            elif self.crm_type == "hubspot":
                return await self._get_hubspot_data(client, input_data)
            else:
                # CONTRACT_EXCEPTION AP-7: Return structured error, don't raise
                return GetProspectDataOutput(
                    profile={},
                    interactions=[],
                    opportunities=[],
                    custom_fields={},
                    error=f"Unsupported CRM type: {self.crm_type}"
                )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("CRM data fetch failed: %s", e)
            return GetProspectDataOutput(
                profile={}, interactions=[], opportunities=[], custom_fields={},
                error=f"CRM data fetch failed: {e}"
            )

    async def _get_salesforce_data(
        self, client: httpx.AsyncClient, input_data: GetProspectDataInput
    ) -> GetProspectDataOutput:
        """Fetch data from Salesforce API."""
        # P0-1 FIX: Validate prospect_id is a valid Salesforce ID before any query
        prospect_id = self._validate_sfdc_id(input_data.prospect_id)

        result = GetProspectDataOutput()

        # Fetch account/profile
        if "profile" in input_data.data_types:
            account_url = f"{self.instance_url}/services/data/v58.0/sobjects/Account/{prospect_id}"
            response = await client.get(account_url)
            self._check_salesforce_rate_limit(response)
            if response.status_code == 200:
                data = response.json()
                result.profile = {
                    "id": prospect_id,
                    "name": data.get("Name"),
                    "industry": data.get("Industry"),
                    "region": data.get("BillingState") or data.get("BillingCountry"),
                    "company_size": data.get("NumberOfEmployees"),
                    "annual_revenue": data.get("AnnualRevenue"),
                    "website": data.get("Website"),
                    "headquarters": f"{data.get('BillingCity', '')}, {data.get('BillingState', '')}",
                    "employees": data.get("NumberOfEmployees"),
                    "segment": data.get("Type"),
                }
            elif response.status_code == 429:
                logger.warning("Salesforce rate limit hit during profile fetch")

        # Fetch opportunities with pagination
        if "opportunities" in input_data.data_types:
            safe_id = self._soql_safe_id(prospect_id)
            opp_query = f"SELECT Id, Name, StageName, Amount, Probability, CloseDate FROM Opportunity WHERE AccountId = '{safe_id}'"
            opp_records, opp_truncated = await self._execute_soql_query(client, opp_query)
            result.opportunities = [
                {
                    "id": rec.get("Id"),
                    "name": rec.get("Name"),
                    "stage": rec.get("StageName"),
                    "value": rec.get("Amount"),
                    "probability": rec.get("Probability") / 100
                    if rec.get("Probability")
                    else 0,
                    "close_date": rec.get("CloseDate"),
                }
                for rec in opp_records
            ]
            if opp_truncated:
                result.error = "Partial results: opportunity pagination truncated"

        # Fetch interactions (activities) with pagination
        if "interactions" in input_data.data_types:
            safe_id = self._soql_safe_id(prospect_id)
            task_query = f"SELECT Id, Subject, ActivityDate, Status, Description FROM Task WHERE WhatId = '{safe_id}' ORDER BY ActivityDate DESC"
            task_records, task_truncated = await self._execute_soql_query(client, task_query)
            result.interactions = [
                {
                    "id": rec.get("Id"),
                    "type": "task",
                    "date": rec.get("ActivityDate"),
                    "subject": rec.get("Subject"),
                    "outcome": rec.get("Status"),
                }
                for rec in task_records
            ]
            if task_truncated:
                existing_error = result.error or ""
                result.error = f"{existing_error}; Partial results: interaction pagination truncated".strip("; ")

        return result

    async def _get_hubspot_data(
        self, client: httpx.AsyncClient, input_data: GetProspectDataInput
    ) -> GetProspectDataOutput:
        """Fetch data from HubSpot API."""
        prospect_id = input_data.prospect_id

        result = GetProspectDataOutput()

        # HubSpot company endpoint
        if "profile" in input_data.data_types:
            url = f"https://api.hubapi.com/crm/v3/objects/companies/{prospect_id}"
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                props = data.get("properties", {})
                result.profile = {
                    "id": prospect_id,
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

        # Fetch opportunities (deals) associated with company
        if "opportunities" in input_data.data_types:
            # HubSpot CRM API v3 - get deals associated with company
            associations_url = (
                f"https://api.hubapi.com/crm/v3/objects/companies/{prospect_id}/associations/deals"
            )
            assoc_response = await client.get(associations_url)

            if assoc_response.status_code == 200:
                assoc_data = assoc_response.json()
                deal_ids = [r.get("toObjectId") for r in assoc_data.get("results", [])]

                # Fetch all deal details concurrently instead of sequentially
                async def _fetch_deal(deal_id: str) -> dict | None:
                    deal_url = f"https://api.hubapi.com/crm/v3/objects/deals/{deal_id}"
                    deal_response = await client.get(deal_url)
                    if deal_response.status_code != 200:
                        return None
                    props = deal_response.json().get("properties", {})
                    return {
                        "id": str(deal_id),
                        "name": props.get("dealname", "Untitled Deal"),
                        "stage": props.get("dealstage", "unknown"),
                        "value": float(props.get("amount", 0))
                        if props.get("amount")
                        else 0,
                        "probability": float(props.get("probability", 0)) / 100
                        if props.get("probability")
                        else 0,
                        "close_date": props.get("closedate"),
                        "pipeline": props.get("pipeline"),
                    }

                deal_responses = await asyncio.gather(
                    *[_fetch_deal(str(did)) for did in deal_ids[:50]]
                )
                opportunities = [d for d in deal_responses if d is not None]

                result.opportunities = opportunities

        # Fetch interactions (engagements) via v1 API
        if "interactions" in input_data.data_types:
            engagements_url = f"https://api.hubapi.com/engagements/v1/engagements/associated/COMPANY/{prospect_id}/paged"
            engagements_response = await client.get(engagements_url)

            if engagements_response.status_code == 200:
                engagements_data = engagements_response.json()
                interactions = []

                for eng in engagements_data.get("results", [])[:100]:  # Limit to 100
                    metadata = eng.get("engagement", {})
                    eng.get("associations", {})

                    # Determine interaction type and extract relevant data
                    eng_type = metadata.get("type", "unknown").lower()

                    interaction = {
                        "id": str(metadata.get("id", "")),
                        "type": eng_type,
                        "date": metadata.get("createdAt"),
                        "subject": metadata.get("subject", ""),
                        "outcome": "completed" if metadata.get("active") else "pending",
                    }

                    # Add type-specific details
                    if eng_type == "email":
                        email_meta = eng.get("metadata", {})
                        interaction["subject"] = email_meta.get("subject", "Email")
                        interaction["sender"] = (
                            email_meta.get("from", {}).get("rawEmail")
                            if isinstance(email_meta.get("from"), dict)
                            else None
                        )
                    elif eng_type == "call":
                        call_meta = eng.get("metadata", {})
                        interaction["duration_minutes"] = (
                            call_meta.get("durationMilliseconds", 0) // 60000
                            if call_meta.get("durationMilliseconds")
                            else None
                        )
                        interaction["notes"] = call_meta.get("body", "")
                    elif eng_type == "meeting":
                        meeting_meta = eng.get("metadata", {})
                        interaction["subject"] = meeting_meta.get("title", "Meeting")
                        interaction["duration_minutes"] = (
                            meeting_meta.get("durationMillis", 0) // 60000
                            if meeting_meta.get("durationMillis")
                            else None
                        )
                    elif eng_type == "task":
                        task_meta = eng.get("metadata", {})
                        interaction["subject"] = task_meta.get("subject", "Task")
                        interaction["notes"] = task_meta.get("body", "")

                    interactions.append(interaction)

                result.interactions = interactions

        return result


class UpdateOpportunityTool(BaseTool):
    """Update opportunity fields in CRM."""

    name = "update_opportunity"
    category = ToolCategory.CRM
    description = "Updates opportunity fields and optionally notifies owner"
    input_schema = UpdateOpportunityInput
    output_schema = UpdateOpportunityOutput
    timeout_seconds = 10
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

    async def execute(self, input_data: UpdateOpportunityInput) -> UpdateOpportunityOutput:
        """Update opportunity in CRM."""
        client = self._get_client()

        try:
            if self.crm_type == "salesforce":
                # Salesforce REST API PATCH
                url = f"{self.instance_url}/services/data/v58.0/sobjects/Opportunity/{input_data.opportunity_id}"
                response = await client.patch(url, json=input_data.updates)
                success = response.status_code in [200, 204]

            elif self.crm_type == "hubspot":
                # HubSpot API
                url = f"https://api.hubapi.com/crm/v3/objects/deals/{input_data.opportunity_id}"
                properties = {k: str(v) for k, v in input_data.updates.items()}
                response = await client.patch(url, json={"properties": properties})
                success = response.status_code == 200
            else:
                # CONTRACT_EXCEPTION AP-7: Return structured error, don't raise
                return UpdateOpportunityOutput(
                    success=False,
                    opportunity_id=input_data.opportunity_id,
                    updated_fields=[],
                    error=f"Unsupported CRM type: {self.crm_type}"
                )

            return UpdateOpportunityOutput(
                success=success,
                opportunity_id=input_data.opportunity_id,
                updated_fields=list(input_data.updates.keys()),
                error=None if success else response.text,
            )

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("CRM update failed: %s", e)
            return UpdateOpportunityOutput(
                success=False,
                opportunity_id=input_data.opportunity_id,
                updated_fields=[],
                error=f"CRM update failed: {e}"
            )


class FetchInteractionHistoryTool(_SalesforceIdSafetyMixin, BaseTool):
    """Fetch interaction history for a prospect from CRM."""

    name = "fetch_interaction_history"
    category = ToolCategory.CRM
    description = "Retrieves interaction history including emails, calls, meetings"
    input_schema = FetchInteractionHistoryInput
    output_schema = FetchInteractionHistoryOutput
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

    async def execute(
        self, input_data: FetchInteractionHistoryInput
    ) -> FetchInteractionHistoryOutput:
        """Fetch interaction history from CRM."""
        client = self._get_client()

        try:
            if self.crm_type == "salesforce":
                return await self._get_salesforce_interactions(client, input_data)
            elif self.crm_type == "hubspot":
                return await self._get_hubspot_interactions(client, input_data)
            else:
                # CONTRACT_EXCEPTION AP-7: Return structured error, don't raise
                return FetchInteractionHistoryOutput(
                    interactions=[],
                    total_count=0,
                    summary=f"Unsupported CRM type: {self.crm_type}",
                    error=f"Unsupported CRM type: {self.crm_type}"
                )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("CRM fetch failed: %s", e)
            return FetchInteractionHistoryOutput(
                interactions=[],
                total_count=0,
                summary="",
                error=f"CRM fetch failed: {e}"
            )

    async def _get_salesforce_interactions(
        self, client: httpx.AsyncClient, input_data: FetchInteractionHistoryInput
    ) -> FetchInteractionHistoryOutput:
        """Fetch interactions from Salesforce."""
        # P0-1 FIX: Validate prospect_id is a valid Salesforce ID before any query
        prospect_id = self._validate_sfdc_id(input_data.prospect_id)
        safe_id = self._soql_safe_id(prospect_id)

        # Build SOQL query
        since_clause = ""
        if input_data.since_date:
            # Validate date format (ISO 8601 or Salesforce date)
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", input_data.since_date):
                raise ValueError("Invalid since_date format: expected YYYY-MM-DD")
            since_clause = f" AND ActivityDate >= {input_data.since_date}"

        type_filter = ""
        if input_data.interaction_types:
            # Sanitize interaction types — allow only alphanumeric + space
            safe_types = []
            for t in input_data.interaction_types:
                if not re.match(r"^[\w\s]+$", t):
                    raise ValueError(f"Invalid interaction type: {t}")
                safe_types.append(t.replace("'", "''"))
            types_str = ",".join([f"'{t}'" for t in safe_types])
            type_filter = f" AND Type IN ({types_str})"

        query = f"""
            SELECT Id, Subject, ActivityDate, Type, Status, Description, DurationInMinutes
            FROM Task
            WHERE WhatId = '{safe_id}'{since_clause}{type_filter}
            ORDER BY ActivityDate DESC
            LIMIT {input_data.limit}
        """

        url = f"{self.instance_url}/services/data/v58.0/query?q={urllib.parse.quote(query)}"
        response = await client.get(url)

        interactions = []
        if response.status_code == 200:
            data = response.json()
            for rec in data.get("records", []):
                interactions.append(
                    {
                        "id": rec.get("Id"),
                        "type": rec.get("Type", "task").lower(),
                        "date": rec.get("ActivityDate"),
                        "subject": rec.get("Subject"),
                        "duration_minutes": rec.get("DurationInMinutes"),
                        "notes": rec.get("Description"),
                        "outcome": rec.get("Status"),
                    }
                )

        # Generate summary
        summary = self._generate_summary(interactions)

        return FetchInteractionHistoryOutput(
            interactions=interactions, total_count=len(interactions), summary=summary
        )

    async def _get_hubspot_interactions(
        self, client: httpx.AsyncClient, input_data: FetchInteractionHistoryInput
    ) -> FetchInteractionHistoryOutput:
        """Fetch interactions from HubSpot."""
        # HubSpot engagements API
        url = f"https://api.hubapi.com/engagements/v1/engagements/associated/COMPANY/{input_data.prospect_id}/paged"

        response = await client.get(url)
        interactions = []

        if response.status_code == 200:
            data = response.json()
            for eng in data.get("results", [])[: input_data.limit]:
                metadata = eng.get("engagement", {})
                interactions.append(
                    {
                        "id": metadata.get("id"),
                        "type": metadata.get("type", "unknown").lower(),
                        "date": metadata.get("createdAt"),
                        "subject": metadata.get("subject", ""),
                        "outcome": "completed" if metadata.get("active") else "pending",
                    }
                )

        summary = self._generate_summary(interactions)

        return FetchInteractionHistoryOutput(
            interactions=interactions, total_count=len(interactions), summary=summary
        )

    def _generate_summary(self, interactions: list[dict]) -> str:
        """Generate summary of interactions."""
        if not interactions:
            return "No recent interactions recorded"

        meeting_count = sum(1 for i in interactions if i.get("type") == "meeting")
        email_count = sum(1 for i in interactions if i.get("type") == "email")
        call_count = sum(1 for i in interactions if i.get("type") == "call")

        parts = [
            f"Recent activity: {meeting_count} meetings, {email_count} emails, {call_count} calls"
        ]

        positive_count = sum(1 for i in interactions if i.get("outcome") == "positive")
        if positive_count >= 2:
            parts.append("Multiple positive interactions indicate strong interest")

        return ". ".join(parts)


class ScoreLeadTool(BaseTool):
    """Score a lead based on profile and engagement data."""

    name = "score_lead"
    category = ToolCategory.CRM
    description = "Calculates lead score based on profile fit and engagement"
    input_schema = ScoreLeadInput
    output_schema = ScoreLeadOutput
    timeout_seconds = 10

    async def execute(self, input_data: ScoreLeadInput) -> ScoreLeadOutput:
        """Calculate lead score."""
        # Get prospect data with config
        prospect_tool = GetProspectDataTool(self.config)
        prospect_data = await prospect_tool.execute(
            GetProspectDataInput(prospect_id=input_data.prospect_id)
        )

        profile = prospect_data.profile
        interactions = prospect_data.interactions
        opportunities = prospect_data.opportunities

        # Calculate component scores
        factors = {}

        # Company size score
        employees = profile.get("employees", 0)
        if employees >= 1000:
            factors["company_size"] = 20
        elif employees >= 500:
            factors["company_size"] = 15
        elif employees >= 100:
            factors["company_size"] = 10
        else:
            factors["company_size"] = 5

        # Industry fit score
        industry = profile.get("industry", "").lower()
        high_fit_industries = ["manufacturing", "financial_services", "healthcare"]
        medium_fit_industries = ["technology", "retail"]

        if any(i in industry for i in high_fit_industries):
            factors["industry_fit"] = 15
        elif any(i in industry for i in medium_fit_industries):
            factors["industry_fit"] = 10
        else:
            factors["industry_fit"] = 5

        # Engagement score
        interaction_count = len(interactions)
        positive_signals = sum(1 for i in interactions if i.get("outcome") == "positive")

        factors["engagement"] = min(20, interaction_count * 5 + positive_signals * 5)

        # Opportunity value score
        if opportunities:
            max_value = max(opp.get("value", 0) for opp in opportunities)
            if max_value >= 500000:
                factors["opportunity_value"] = 20
            elif max_value >= 100000:
                factors["opportunity_value"] = 15
            elif max_value >= 50000:
                factors["opportunity_value"] = 10
            else:
                factors["opportunity_value"] = 5
        else:
            factors["opportunity_value"] = 0

        # Budget indicator
        custom_fields = prospect_data.custom_fields
        if custom_fields.get("budget_approved"):
            factors["budget_confirmed"] = 15
        else:
            factors["budget_confirmed"] = 0

        # Calculate total score
        total_score = sum(factors.values())

        # Determine grade
        if total_score >= 80:
            grade = "A"
        elif total_score >= 60:
            grade = "B"
        elif total_score >= 40:
            grade = "C"
        elif total_score >= 20:
            grade = "D"
        else:
            grade = "F"

        # Generate recommendations
        recommendations = []
        if factors["engagement"] < 10:
            recommendations.append("Increase engagement with targeted content")
        if factors["budget_confirmed"] == 0:
            recommendations.append("Confirm budget authority in next conversation")
        if factors["opportunity_value"] < 10:
            recommendations.append("Explore expansion opportunities")
        if grade in ["A", "B"]:
            recommendations.append("Prioritize for immediate follow-up")

        return ScoreLeadOutput(
            score=total_score,
            grade=grade,
            factors=factors,
            recommendations=recommendations if recommendations else ["Continue nurturing"],
        )
