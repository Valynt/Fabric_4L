from __future__ import annotations

import asyncio

import pytest

from layer4_agents.models.tool_schemas import (
    FetchInteractionHistoryInput,
    GetProspectDataInput,
    GetProspectDataOutput,
    ScoreLeadInput,
    UpdateOpportunityInput,
)
from layer4_agents.tools.crm_tools import (
    FetchInteractionHistoryTool,
    GetProspectDataTool,
    ScoreLeadTool,
    UpdateOpportunityTool,
)


class Response:
    def __init__(self, status_code=200, data=None, *, text="error", headers=None):
        self.status_code = status_code
        self.data = data or {}
        self.text = text
        self.headers = headers or {}

    def json(self):
        return self.data


class Client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def get(self, url):
        self.calls.append(("GET", url, None))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response

    async def patch(self, url, json):
        self.calls.append(("PATCH", url, json))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def prospect_input(**kwargs):
    values = {
        "prospect_id": "001000000000001",
        "data_types": ["profile", "opportunities", "interactions"],
        "prospect_data": {},
    }
    values.update(kwargs)
    return GetProspectDataInput(**values)


def config(crm_type="salesforce"):
    return {
        "crm_type": crm_type,
        "crm_api_key": "key",
        "crm_instance_url": "https://crm.test",
    }


def test_salesforce_id_validation_blocks_injection() -> None:
    assert GetProspectDataTool._validate_sfdc_id("001000000000001") == "001000000000001"
    assert GetProspectDataTool._soql_safe_id("001000000000001AAA").isalnum()
    for value in ("", "abc' OR 1=1", "too-short"):
        with pytest.raises(ValueError, match="Invalid prospect_id"):
            GetProspectDataTool._validate_sfdc_id(value)


@pytest.mark.asyncio
async def test_inline_prospect_fallback_preserves_custom_fields() -> None:
    result = await GetProspectDataTool().execute(
        prospect_input(
            prospect_id="prospect",
            prospect_data={"name": "Acme", "employees": 100, "custom": "value"},
        )
    )
    assert result.profile["name"] == "Acme"
    assert result.profile["company_size"] == 100
    assert result.custom_fields == {"custom": "value"}


@pytest.mark.asyncio
async def test_salesforce_profile_opportunities_and_interactions() -> None:
    tool = GetProspectDataTool(config())
    tool._client = Client(
        [
            Response(
                200,
                {
                    "Name": "Acme",
                    "Industry": "Manufacturing",
                    "BillingCity": "Austin",
                    "BillingState": "TX",
                    "NumberOfEmployees": 1200,
                    "AnnualRevenue": 1_000_000,
                    "Website": "https://acme.test",
                    "Type": "Customer",
                },
                headers={"Sforce-Limit-Info": "api-usage=1/100"},
            ),
            Response(
                200,
                {
                    "records": [
                        {
                            "Id": "opp",
                            "Name": "Deal",
                            "StageName": "Open",
                            "Amount": 500000,
                            "Probability": 75,
                            "CloseDate": "2026-12-31",
                        }
                    ]
                },
            ),
            Response(
                200,
                {
                    "records": [
                        {
                            "Id": "task",
                            "Subject": "Call",
                            "ActivityDate": "2026-01-01",
                            "Status": "Done",
                        }
                    ]
                },
            ),
        ]
    )
    result = await tool.execute(prospect_input())
    assert result.profile["headquarters"] == "Austin, TX"
    assert result.opportunities[0]["probability"] == 0.75
    assert result.interactions[0]["type"] == "task"


class Metrics:
    def __init__(self):
        self.calls = []

    def increment_crm_salesforce_rate_limit(self, tenant):
        self.calls.append(tenant)


@pytest.mark.asyncio
async def test_salesforce_pagination_rate_limit_and_page_cap(monkeypatch) -> None:
    metrics = Metrics()
    monkeypatch.setattr("layer4_agents.tools.crm_tools.get_metrics", lambda: metrics)
    tool = GetProspectDataTool(config())
    client = Client(
        [
            Response(200, {"records": [{"Id": "one"}], "nextRecordsUrl": "/next"}),
            Response(429),
        ]
    )
    records, truncated = await tool._execute_soql_query(client, "SELECT Id", max_pages=3)
    assert records == [{"Id": "one"}] and truncated
    assert metrics.calls == ["unknown"]

    capped = Client([Response(200, {"records": [], "nextRecordsUrl": "/next"})])
    assert (await tool._execute_soql_query(capped, "SELECT Id", max_pages=1))[1]
    failed = Client([Response(500)])
    assert (await tool._execute_soql_query(failed, "SELECT Id"))[1]


@pytest.mark.asyncio
async def test_salesforce_partial_result_messages_and_profile_rate_limit() -> None:
    tool = GetProspectDataTool(config())
    tool._client = Client([Response(429), Response(500), Response(500)])
    result = await tool.execute(prospect_input())
    assert "opportunity pagination truncated" in result.error
    assert "interaction pagination truncated" in result.error


@pytest.mark.asyncio
async def test_hubspot_maps_profile_deals_and_engagement_types() -> None:
    tool = GetProspectDataTool(config("hubspot"))
    engagements = []
    for kind, metadata in (
        ("EMAIL", {"subject": "Email", "from": {"rawEmail": "sender@test"}}),
        ("CALL", {"durationMilliseconds": 120000, "body": "notes"}),
        ("MEETING", {"title": "Review", "durationMillis": 60000}),
        ("TASK", {"subject": "Follow up", "body": "todo"}),
    ):
        engagements.append(
            {
                "engagement": {"id": kind, "type": kind, "createdAt": 1, "active": True},
                "metadata": metadata,
            }
        )
    tool._client = Client(
        [
            Response(
                200,
                {
                    "properties": {
                        "name": "Acme",
                        "industry": "Tech",
                        "country": "US",
                        "numberofemployees": "500",
                        "annualrevenue": "10",
                        "domain": "acme.test",
                    }
                },
            ),
            Response(200, {"results": [{"toObjectId": 1}, {"toObjectId": 2}]}),
            Response(
                200,
                {
                    "properties": {
                        "dealname": "Deal",
                        "dealstage": "open",
                        "amount": "100",
                        "probability": "50",
                        "pipeline": "sales",
                    }
                },
            ),
            Response(404),
            Response(200, {"results": engagements}),
        ]
    )
    result = await tool.execute(prospect_input(prospect_id="company"))
    assert result.profile["domain"] == "acme.test"
    assert result.opportunities[0]["probability"] == 0.5
    assert [item["type"] for item in result.interactions] == ["email", "call", "meeting", "task"]
    assert result.interactions[1]["duration_minutes"] == 2


@pytest.mark.parametrize("crm_type", ["unknown", "salesforce"])
@pytest.mark.asyncio
async def test_get_prospect_structured_errors_and_cancellation(crm_type) -> None:
    tool = GetProspectDataTool(config(crm_type))
    if crm_type == "unknown":
        result = await tool.execute(prospect_input())
        assert "Unsupported CRM" in result.error
    else:
        tool._client = Client([RuntimeError("offline")])
        result = await tool.execute(prospect_input(data_types=["profile"]))
        assert "offline" in result.error
        tool._client = Client([asyncio.CancelledError()])
        with pytest.raises(asyncio.CancelledError):
            await tool.execute(prospect_input(data_types=["profile"]))


@pytest.mark.parametrize(
    ("crm_type", "status", "expected"),
    [("salesforce", 204, True), ("hubspot", 200, True), ("hubspot", 500, False)],
)
@pytest.mark.asyncio
async def test_update_opportunity_contract(crm_type, status, expected) -> None:
    tool = UpdateOpportunityTool(config(crm_type))
    tool._client = Client([Response(status, text="rejected")])
    result = await tool.execute(UpdateOpportunityInput(opportunity_id="opp", updates={"amount": 3}))
    assert result.success is expected
    assert result.updated_fields == ["amount"]
    if crm_type == "hubspot":
        assert tool._client.calls[0][2] == {"properties": {"amount": "3"}}


@pytest.mark.asyncio
async def test_update_opportunity_errors_and_cancellation() -> None:
    result = await UpdateOpportunityTool(config("unknown")).execute(
        UpdateOpportunityInput(opportunity_id="opp", updates={})
    )
    assert "Unsupported CRM" in result.error
    tool = UpdateOpportunityTool(config())
    tool._client = Client([RuntimeError("offline")])
    assert (
        "offline"
        in (await tool.execute(UpdateOpportunityInput(opportunity_id="opp", updates={}))).error
    )
    tool._client = Client([asyncio.CancelledError()])
    with pytest.raises(asyncio.CancelledError):
        await tool.execute(UpdateOpportunityInput(opportunity_id="opp", updates={}))


@pytest.mark.parametrize("crm_type", ["salesforce", "hubspot"])
@pytest.mark.asyncio
async def test_interaction_history_mapping_and_summary(crm_type) -> None:
    tool = FetchInteractionHistoryTool(config(crm_type))
    if crm_type == "salesforce":
        data = {
            "records": [
                {"Id": "1", "Type": "Meeting", "ActivityDate": "2026-01-01", "Status": "positive"},
                {"Id": "2", "Type": "Email", "ActivityDate": "2026-01-02", "Status": "positive"},
            ]
        }
    else:
        data = {
            "results": [
                {
                    "engagement": {
                        "id": "1",
                        "type": "CALL",
                        "createdAt": 1,
                        "subject": "Call",
                        "active": True,
                    }
                }
            ]
        }
    tool._client = Client([Response(200, data)])
    result = await tool.execute(
        FetchInteractionHistoryInput(
            prospect_id="001000000000001" if crm_type == "salesforce" else "company",
            interaction_types=["Meeting"],
            since_date="2026-01-01",
            limit=10,
        )
    )
    assert result.total_count
    assert "Recent activity" in result.summary
    if crm_type == "salesforce":
        assert "strong interest" in result.summary


@pytest.mark.parametrize(
    "kwargs",
    [
        {"since_date": "01/01/2026"},
        {"interaction_types": ["Email' OR 1=1"]},
    ],
)
@pytest.mark.asyncio
async def test_salesforce_interaction_filters_reject_injection(kwargs) -> None:
    tool = FetchInteractionHistoryTool(config())
    tool._client = Client([])
    result = await tool.execute(
        FetchInteractionHistoryInput(prospect_id="001000000000001", **kwargs)
    )
    assert result.error


@pytest.mark.parametrize("prospect_id", ["", "abc' OR 1=1", "too-short"])
@pytest.mark.asyncio
async def test_salesforce_interactions_reject_invalid_prospect_id_before_query(
    prospect_id: str,
) -> None:
    tool = FetchInteractionHistoryTool(config())
    client = Client([])
    tool._client = client

    result = await tool.execute(FetchInteractionHistoryInput(prospect_id=prospect_id))

    assert "Invalid prospect_id format" in result.error
    assert client.calls == []


@pytest.mark.asyncio
async def test_interaction_unknown_error_empty_and_cancellation() -> None:
    unknown = await FetchInteractionHistoryTool(config("unknown")).execute(
        FetchInteractionHistoryInput(prospect_id="company")
    )
    assert "Unsupported CRM" in unknown.error
    tool = FetchInteractionHistoryTool(config("hubspot"))
    tool._client = Client([RuntimeError("offline")])
    assert (
        "offline" in (await tool.execute(FetchInteractionHistoryInput(prospect_id="company"))).error
    )
    assert tool._generate_summary([]) == "No recent interactions recorded"
    tool._client = Client([asyncio.CancelledError()])
    with pytest.raises(asyncio.CancelledError):
        await tool.execute(FetchInteractionHistoryInput(prospect_id="company"))


@pytest.mark.parametrize(
    ("profile", "interactions", "opportunities", "custom", "grade"),
    [
        (
            {"employees": 1200, "industry": "manufacturing"},
            [{"outcome": "positive"}] * 3,
            [{"value": 500000}],
            {"budget_approved": True},
            "A",
        ),
        ({"employees": 600, "industry": "technology"}, [], [{"value": 100000}], {}, "C"),
        ({"employees": 150, "industry": "other"}, [], [{"value": 50000}], {}, "D"),
        ({"employees": 10, "industry": "other"}, [], [], {}, "F"),
    ],
)
@pytest.mark.asyncio
async def test_lead_scoring_bands(
    monkeypatch, profile, interactions, opportunities, custom, grade
) -> None:
    async def execute(_self, _input):
        return GetProspectDataOutput(
            profile=profile,
            interactions=interactions,
            opportunities=opportunities,
            custom_fields=custom,
        )

    monkeypatch.setattr(GetProspectDataTool, "execute", execute)
    result = await ScoreLeadTool({}).execute(ScoreLeadInput(prospect_id="prospect"))
    assert result.grade == grade
    assert result.recommendations
