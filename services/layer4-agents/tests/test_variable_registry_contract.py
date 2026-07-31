from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from layer4_agents.interfaces.variable_registry import (
    ResolutionContext,
    Variable,
    VariableDataType,
    VariableSearchCriteria,
    VariableSourceBinding,
    VariableSourceType,
    VariableValidationRule,
)
from layer4_agents.services.variable_registry_service import Neo4jVariableRegistry

NOW = datetime(2026, 7, 1, tzinfo=UTC)


class Result:
    def __init__(self, *, single=None, data=None):
        self.single_value = single
        self.data_value = [] if data is None else data

    async def single(self):
        return self.single_value

    async def data(self):
        return self.data_value


class Session:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def run(self, query, **params):
        self.calls.append((query, params))
        return self.results.pop(0)


class Driver:
    def __init__(self, sessions):
        self.sessions = list(sessions)
        self.used = []

    def session(self):
        value = self.sessions.pop(0)
        self.used.append(value)
        return value


def node(**overrides):
    value = {
        "id": "revenue",
        "name": "Annual Revenue",
        "description": "Revenue",
        "dataType": "decimal",
        "industry": "technology",
        "applicableFormulas": ["roi"],
        "applicablePacks": ["saas"],
        "createdAt": NOW.isoformat(),
        "updatedAt": NOW.isoformat(),
        "version": "2.0.0",
        "isActive": True,
        "sourceType": "user_input",
        "sourceLocation": "workspace",
        "extractionQuery": "query",
        "transformation": "transform",
        "fallbackValue": "10",
        "isRequired": False,
        "validationRules": [
            {"ruleType": "range", "parameters": {"min": 0}, "errorMessage": "positive"},
            "malformed",
        ],
    }
    value.update(overrides)
    return value


def variable(source=True):
    return Variable(
        variable_id="revenue",
        name="Annual Revenue",
        description="Revenue",
        data_type=VariableDataType.DECIMAL,
        source_binding=(
            VariableSourceBinding(
                source_type=VariableSourceType.USER_INPUT,
                source_location="workspace",
                extraction_query="query",
                transformation="transform",
                fallback_value="10",
                is_required=False,
            )
            if source
            else None
        ),
        validation_rules=[VariableValidationRule("range", {"min": 0}, "positive")],
        industry="technology",
        applicable_formulas=["roi"],
        applicable_packs=["saas"],
        created_at=NOW,
        version="2.0.0",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("with_source", [True, False])
async def test_register_variable_serializes_source_rules_and_sets_created_at(with_source) -> None:
    stored = node(createdAt="2026-07-02T00:00:00+00:00")
    session = Session([Result(single={"v": stored})])
    registry = Neo4jVariableRegistry(Driver([session]))
    value = variable(with_source)
    result = await registry.register_variable(value)
    assert result is value and result.created_at == datetime.fromisoformat(stored["createdAt"])
    query, params = session.calls[0]
    assert "CREATE (v:Variable" in query
    assert params["validation_rules"][0]["ruleType"] == "range"
    if with_source:
        assert params["source_type"] == "user_input" and params["is_required"] is False
    else:
        assert params["source_type"] is None and params["is_required"] is True


@pytest.mark.asyncio
async def test_register_variable_requires_returned_record() -> None:
    registry = Neo4jVariableRegistry(Driver([Session([Result(single=None)])]))
    with pytest.raises(ValueError, match="Failed to register"):
        await registry.register_variable(variable())


@pytest.mark.asyncio
async def test_get_variable_reconstructs_complete_contract_and_missing() -> None:
    registry = Neo4jVariableRegistry(
        Driver([Session([Result(single={"v": node()})]), Session([Result(single=None)])])
    )
    value = await registry.get_variable("revenue")
    assert value.variable_id == "revenue" and value.data_type == VariableDataType.DECIMAL
    assert value.source_binding.source_type == VariableSourceType.USER_INPUT
    assert value.source_binding.is_required is False
    assert len(value.validation_rules) == 1 and value.validation_rules[0].rule_type == "range"
    assert value.updated_at == NOW and value.version == "2.0.0"
    assert await registry.get_variable("missing") is None


@pytest.mark.asyncio
async def test_get_variable_defaults_optional_properties() -> None:
    minimal = {"id": "id", "name": "Name", "dataType": "string"}
    registry = Neo4jVariableRegistry(Driver([Session([Result(single={"v": minimal})])]))
    value = await registry.get_variable("id")
    assert value.description == "" and value.source_binding is None
    assert value.applicable_formulas == [] and value.applicable_packs == []
    assert value.version == "1.0.0" and value.is_active
    assert value.created_at.tzinfo is not None


@pytest.mark.asyncio
async def test_update_variable_allows_known_fields_and_source_binding() -> None:
    update_session = Session([Result(single={"v": node()})])
    get_session = Session([Result(single={"v": node(name="Updated")})])
    registry = Neo4jVariableRegistry(Driver([update_session, get_session]))
    source = VariableSourceBinding(VariableSourceType.CRM_FIELD, "Account.Revenue")
    result = await registry.update_variable(
        "revenue",
        {
            "name": "Updated",
            "description": "New",
            "dataType": "integer",
            "industry": "finance",
            "applicableFormulas": ["f"],
            "applicablePacks": ["p"],
            "isActive": False,
            "source_binding": source,
            "ignored": "value",
        },
    )
    query, params = update_session.calls[0]
    assert "v.name = $name" in query and "ignored" not in params
    assert params["source_type"] == "crm_field" and params["source_location"] == "Account.Revenue"
    assert result.name == "Updated"


@pytest.mark.asyncio
async def test_update_variable_raises_when_missing() -> None:
    registry = Neo4jVariableRegistry(Driver([Session([Result(single=None)])]))
    with pytest.raises(ValueError, match="not found"):
        await registry.update_variable("missing", {})


@pytest.mark.asyncio
async def test_search_variables_builds_all_filters_and_reconstructs_rows() -> None:
    session = Session([Result(data=[{"v": node()}, {"v": node(id="simple", sourceType=None)}])])
    registry = Neo4jVariableRegistry(Driver([session]))
    values = await registry.search_variables(
        VariableSearchCriteria(
            industry="technology",
            pack_id="saas",
            formula_id="roi",
            data_type=VariableDataType.DECIMAL,
            source_type=VariableSourceType.USER_INPUT,
            is_active=False,
        )
    )
    assert [value.variable_id for value in values] == ["revenue", "simple"]
    assert values[0].source_binding is not None and values[1].source_binding is None
    query, params = session.calls[0]
    for field in ("industry", "pack_id", "formula_id", "data_type", "source_type", "is_active"):
        assert field in params
    assert "v.industry = $industry" in query
    assert "$pack_id IN v.applicablePacks" in query
    assert "$formula_id IN v.applicableFormulas" in query
    assert "ORDER BY v.name" in query

    empty_session = Session([Result(data=[])])
    registry = Neo4jVariableRegistry(Driver([empty_session]))
    assert await registry.search_variables(VariableSearchCriteria(is_active=None)) == []
    assert "WHERE 1=1" in empty_session.calls[0][0]


@pytest.mark.asyncio
async def test_resolve_variable_user_input_fallback_and_missing() -> None:
    registry = Neo4jVariableRegistry(Driver([]))
    context = ResolutionContext(workspace_id="42", entity_id="account")

    async def found(_id):
        return Variable(
            variable_id="id",
            name="Name",
            description="",
            data_type=VariableDataType.INTEGER,
            source_binding=VariableSourceBinding(VariableSourceType.USER_INPUT, "workspace"),
        )

    registry.get_variable = found
    value = await registry.resolve_variable("id", context)
    assert value.value == 42 and value.workspace_id == "42" and value.entity_id == "account"

    async def fallback(_id):
        return Variable(
            variable_id="id",
            name="Name",
            description="",
            data_type=VariableDataType.STRING,
            source_binding=VariableSourceBinding(
                VariableSourceType.API_CALL, "api", fallback_value="fallback"
            ),
        )

    registry.get_variable = fallback
    assert (await registry.resolve_variable("id", context)).value == "fallback"

    async def missing(_id):
        return None

    registry.get_variable = missing
    with pytest.raises(ValueError, match="not found"):
        await registry.resolve_variable("missing", context)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source_type", "message"),
    [
        (VariableSourceType.CRM_FIELD, "CRM integration"),
        (VariableSourceType.BENCHMARK_LOOKUP, "Benchmark integration"),
        (VariableSourceType.FORMULA_CALCULATION, "Formula calculation service"),
        (VariableSourceType.GROUND_TRUTH, "Ground-truth integration"),
    ],
)
async def test_resolve_variable_fails_closed_for_unconfigured_sources(source_type, message) -> None:
    registry = Neo4jVariableRegistry(Driver([]))

    async def found(_id):
        return Variable(
            variable_id="id",
            name="Name",
            description="",
            data_type=VariableDataType.STRING,
            source_binding=VariableSourceBinding(source_type, "location"),
        )

    registry.get_variable = found
    with pytest.raises(ValueError, match=message):
        await registry.resolve_variable("id", ResolutionContext(workspace_id="workspace"))


@pytest.mark.asyncio
async def test_resolve_batch_keeps_successes_records_failures_and_propagates_cancel() -> None:
    registry = Neo4jVariableRegistry(Driver([]))
    context = ResolutionContext(workspace_id="workspace")

    async def resolve(var_id, _context):
        if var_id == "bad":
            raise RuntimeError("offline")
        if var_id == "cancel":
            raise asyncio.CancelledError
        return object()

    registry.resolve_variable = resolve
    results = await registry.resolve_variables_batch(["good", "bad"], context)
    assert results["good"] is not None
    assert results["bad"].value is None and results["bad"].confidence == 0
    with pytest.raises(asyncio.CancelledError):
        await registry.resolve_variables_batch(["cancel"], context)
