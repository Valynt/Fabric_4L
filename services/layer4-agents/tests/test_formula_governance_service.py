from __future__ import annotations

from datetime import UTC, datetime

import pytest

from layer4_agents.interfaces.formula_governance import (
    ActivationRequest,
    DeprecationRequest,
    FormulaStatus,
)
from layer4_agents.services.formula_governance_service import Neo4jFormulaGovernanceService


class Fetch:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0) if self.responses else []


def activation(formula_id="formula"):
    return ActivationRequest(
        formula_id=formula_id,
        version="2.0.0",
        requested_by="user",
        justification="validated",
    )


def deprecation(formula_id="formula"):
    return DeprecationRequest(
        formula_id=formula_id,
        replacement_formula_id="replacement",
        deprecation_date=datetime.now(UTC),
        reason="superseded",
        requested_by="user",
    )


@pytest.mark.asyncio
async def test_governance_reads_versions_dependencies_and_tenant(monkeypatch) -> None:
    fetch = Fetch(
        [
            [
                {
                    "f": {
                        "version": "2.0.0",
                        "status": "approved",
                        "owner": "finance",
                        "department": "sales",
                        "reviewCycleDays": 30,
                        "approvedAt": "2026-01-01T00:00:00+00:00",
                        "lastReviewedAt": "2026-01-02T00:00:00+00:00",
                        "nextReviewAt": "2026-02-01T00:00:00+00:00",
                    },
                    "versions": [
                        {"version": "1.0.0", "status": "draft", "createdBy": "a"},
                        {
                            "version": "2.0.0",
                            "status": "approved",
                            "createdAt": "2026-01-01T00:00:00+00:00",
                            "createdBy": "b",
                            "changeSummary": "update",
                            "previousVersion": "1.0.0",
                        },
                        None,
                    ],
                    "outgoing_deps": [{"id": "dep", "type": "outgoing"}, {"id": None}],
                    "incoming_deps": [{"id": "caller", "type": "incoming"}, {"id": None}],
                }
            ]
        ]
    )
    monkeypatch.setattr(
        "layer4_agents.services.formula_governance_service.fetch_tenant_validated_records", fetch
    )
    result = await Neo4jFormulaGovernanceService(object()).get_governance("formula", "tenant")
    assert result.current_version == "2.0.0"
    assert [version.version for version in result.versions] == ["2.0.0", "1.0.0"]
    assert fetch.calls[0]["params"]["tenant_id"] == "tenant"


@pytest.mark.asyncio
async def test_governance_missing_formula(monkeypatch) -> None:
    monkeypatch.setattr(
        "layer4_agents.services.formula_governance_service.fetch_tenant_validated_records",
        Fetch([[]]),
    )
    assert await Neo4jFormulaGovernanceService(object()).get_governance("missing", "tenant") is None


@pytest.mark.asyncio
async def test_create_and_list_versions(monkeypatch) -> None:
    fetch = Fetch(
        [
            [{"current_version": "1.0.0"}],
            [
                {
                    "fv": {
                        "version": "2.0.0",
                        "createdAt": "2026-01-01T00:00:00+00:00",
                        "createdBy": "user",
                        "changeSummary": "change",
                        "previousVersion": "1.0.0",
                    }
                }
            ],
            [
                {"fv": {"version": "2.0.0", "status": "draft", "createdBy": "user"}},
                {
                    "fv": {
                        "version": "1.0.0",
                        "status": "retired",
                        "createdAt": "2025-01-01T00:00:00+00:00",
                        "createdBy": "user",
                    }
                },
            ],
        ]
    )
    monkeypatch.setattr(
        "layer4_agents.services.formula_governance_service.fetch_tenant_validated_records", fetch
    )
    service = Neo4jFormulaGovernanceService(object())
    version = await service.create_version("formula", "tenant", "2.0.0", "change", "user")
    assert version.previous_version == "1.0.0"
    assert len(await service.list_versions("formula", "tenant", include_retired=True)) == 2
    with pytest.raises(ValueError, match="Invalid semver"):
        await service.create_version("formula", "tenant", "two", "change", "user")


@pytest.mark.asyncio
async def test_create_version_requires_created_record(monkeypatch) -> None:
    monkeypatch.setattr(
        "layer4_agents.services.formula_governance_service.fetch_tenant_validated_records",
        Fetch([[], []]),
    )
    with pytest.raises(ValueError, match="Failed to create"):
        await Neo4jFormulaGovernanceService(object()).create_version(
            "formula", "tenant", "1.0.0", "change", "user"
        )


@pytest.mark.parametrize(
    ("status", "expected", "requires_approval"),
    [
        (None, "Formula not found", False),
        ("active", "already active", False),
        ("under_review", "Cannot activate", True),
    ],
)
@pytest.mark.asyncio
async def test_activation_guards(monkeypatch, status, expected, requires_approval) -> None:
    records = [] if status is None else [{"status": status, "current_version": "1.0.0"}]
    monkeypatch.setattr(
        "layer4_agents.services.formula_governance_service.fetch_tenant_validated_records",
        Fetch([records]),
    )
    result = await Neo4jFormulaGovernanceService(object()).activate(activation(), "tenant")
    assert result.success is False
    assert expected in result.error_message
    assert result.requires_approval is requires_approval


@pytest.mark.parametrize("created", [True, False])
@pytest.mark.asyncio
async def test_activation_success_and_write_failure(monkeypatch, created) -> None:
    fetch = Fetch(
        [[{"status": "approved", "current_version": "1.0.0"}], [{"f": {}}] if created else []]
    )
    monkeypatch.setattr(
        "layer4_agents.services.formula_governance_service.fetch_tenant_validated_records", fetch
    )
    result = await Neo4jFormulaGovernanceService(object()).activate(activation(), "tenant")
    assert result.success is created
    assert result.new_status is (FormulaStatus.ACTIVE if created else FormulaStatus.APPROVED)


@pytest.mark.parametrize(
    ("status", "success", "message"),
    [
        (None, False, "not found"),
        ("deprecated", False, "already deprecated"),
        ("active", True, None),
    ],
)
@pytest.mark.asyncio
async def test_deprecation_transitions(monkeypatch, status, success, message) -> None:
    records = [] if status is None else [{"status": status}]
    monkeypatch.setattr(
        "layer4_agents.services.formula_governance_service.fetch_tenant_validated_records",
        Fetch([records, []]),
    )
    result = await Neo4jFormulaGovernanceService(object()).deprecate(deprecation(), "tenant")
    assert result.success is success
    if message:
        assert message in result.error_message


@pytest.mark.asyncio
async def test_dependencies_support_both_directions(monkeypatch) -> None:
    fetch = Fetch([[{"dep_id": "dep"}], [{"other_id": "caller"}]])
    monkeypatch.setattr(
        "layer4_agents.services.formula_governance_service.fetch_tenant_validated_records", fetch
    )
    deps = await Neo4jFormulaGovernanceService(object()).get_dependencies(
        "formula", "tenant", "both"
    )
    assert [(d.source_formula_id, d.target_formula_id) for d in deps] == [
        ("formula", "dep"),
        ("caller", "formula"),
    ]


@pytest.mark.parametrize(
    ("record", "can_activate", "error", "warning"),
    [
        (None, False, "Formula not found", None),
        (
            {"version_exists": False, "status": "retired", "inactive_deps": 2},
            False,
            "does not exist",
            "inactive",
        ),
        (
            {"version_exists": True, "status": "active", "inactive_deps": 0},
            True,
            None,
            "already active",
        ),
    ],
)
@pytest.mark.asyncio
async def test_validate_activation(monkeypatch, record, can_activate, error, warning) -> None:
    monkeypatch.setattr(
        "layer4_agents.services.formula_governance_service.fetch_tenant_validated_records",
        Fetch([[] if record is None else [record]]),
    )
    result = await Neo4jFormulaGovernanceService(object()).validate_activation(
        "formula", "tenant", "2.0.0"
    )
    assert result.can_activate is can_activate
    if error:
        assert any(error in item for item in result.errors)
    if warning:
        assert any(warning in item for item in result.warnings)


class Metrics:
    def __init__(self):
        self.calls = []

    def inc_formula_approval_pending(self, tenant):
        self.calls.append(("inc", tenant))

    def dec_formula_approval_pending(self, tenant):
        self.calls.append(("dec", tenant))


@pytest.mark.asyncio
async def test_submit_approve_reject_workflow_and_metrics(monkeypatch) -> None:
    metrics = Metrics()
    fetch = Fetch(
        [
            [{"tenant_id": "tenant"}],
            [{"status": "draft"}],
            [],
            [{"tenant_id": "tenant"}],
            [{"tenant_id": "tenant"}],
            [{"tenant_id": "tenant"}],
            [{"tenant_id": "tenant"}],
        ]
    )
    monkeypatch.setattr(
        "layer4_agents.services.formula_governance_service.fetch_tenant_validated_records", fetch
    )
    monkeypatch.setattr(
        "layer4_agents.services.formula_governance_service.get_metrics", lambda: metrics
    )
    service = Neo4jFormulaGovernanceService(object())
    assert (await service.submit_for_review("formula", "tenant", "1.0.0", "user")).success
    assert (await service.approve("formula", "tenant", "1.0.0", "admin", "ok")).success
    assert (await service.reject("formula", "tenant", "1.0.0", "admin", "fix")).success
    assert metrics.calls == [("inc", "tenant"), ("dec", "tenant"), ("dec", "tenant")]


@pytest.mark.parametrize("operation", ["approve", "reject"])
@pytest.mark.asyncio
async def test_approval_write_failure(monkeypatch, operation) -> None:
    monkeypatch.setattr(
        "layer4_agents.services.formula_governance_service.fetch_tenant_validated_records",
        Fetch([[{"tenant_id": "tenant"}], []]),
    )
    service = Neo4jFormulaGovernanceService(object())
    args = ("formula", "tenant", "1.0.0", "admin", "comment")
    result = await getattr(service, operation)(*args)
    assert result.success is False


@pytest.mark.parametrize(
    ("records", "expected"),
    [([], "Formula not found"), ([{"status": "active"}], "expected draft")],
)
@pytest.mark.asyncio
async def test_transition_status_guards(monkeypatch, records, expected) -> None:
    monkeypatch.setattr(
        "layer4_agents.services.formula_governance_service.fetch_tenant_validated_records",
        Fetch([records]),
    )
    result = await Neo4jFormulaGovernanceService(object())._transition_status(
        "formula", "1.0.0", FormulaStatus.DRAFT, FormulaStatus.UNDER_REVIEW, "user", "tenant"
    )
    assert result.success is False and expected in result.error_message


def test_semver_helpers() -> None:
    service = Neo4jFormulaGovernanceService(object())
    assert service._is_valid_semver("1.2.3-beta+build")
    assert not service._is_valid_semver("1.2")
    assert service._semver_key("2.10.3") == (2, 10, 3)
    assert service._semver_key("invalid") == (0, 0, 0)
