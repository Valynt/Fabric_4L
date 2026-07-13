from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

import pytest


MODULE_PATH = Path("scripts/ci/branch_cleanup_policy.py")
policy: Any = None
if MODULE_PATH.exists():
    spec = importlib.util.spec_from_file_location("branch_cleanup_policy", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    policy = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = policy
    spec.loader.exec_module(policy)


def _classify(**overrides: Any) -> Any:
    assert policy is not None, "branch_cleanup_policy.py must exist"
    values = {
        "name": "copilot/topic",
        "protected": False,
        "ahead_by": 0,
        "has_open_pr": False,
        "stale": False,
    }
    values.update(overrides)
    return policy.classify_branch(**values)


def test_branches_ahead_of_main_are_preserved() -> None:
    decision = _classify(name="copilot/unique-work", ahead_by=2, stale=True)

    assert decision.disposition == "preserve"
    assert decision.eligible_for_manual_delete is False
    assert decision.reason == "branch has 2 commit(s) not in main"


def test_open_pr_is_not_deletion_candidate_due_to_age() -> None:
    decision = _classify(
        name="feature/old-but-active",
        ahead_by=1,
        has_open_pr=True,
        stale=True,
    )

    assert decision.disposition == "active"
    assert decision.eligible_for_manual_delete is False
    assert decision.reason == "branch has an open pull request"


@pytest.mark.parametrize(
    ("name", "protected"),
    [("main", False), ("protected/topic", True), ("release/2026.07", False)],
)
def test_protected_baseline_and_release_branches_are_excluded(
    name: str, protected: bool
) -> None:
    decision = _classify(name=name, protected=protected, stale=True)

    assert decision.disposition == "protected"
    assert decision.eligible_for_manual_delete is False


def test_fully_merged_branch_is_reported_for_manual_deletion() -> None:
    decision = _classify(name="copilot/already-merged", ahead_by=0)

    assert decision.disposition == "merged-candidate"
    assert decision.eligible_for_manual_delete is True
    assert decision.reason == "branch is fully contained in main"


def test_manual_deletion_requires_exact_branch_confirmation() -> None:
    assert policy is not None, "branch_cleanup_policy.py must exist"
    deleted = False

    def delete_ref(_: str) -> None:
        nonlocal deleted
        deleted = True

    with pytest.raises(
        ValueError, match=r"confirmation must equal DELETE copilot/already-merged"
    ):
        policy.execute_manual_deletion(
            branch="copilot/already-merged",
            confirmation="DELETE something-else",
            get_branch=lambda _: {"protected": False},
            get_open_pulls=lambda _: [],
            compare_with_main=lambda _: {"ahead_by": 0},
            find_references=lambda _: [],
            find_deployment_references=lambda _: [],
            delete_ref=delete_ref,
        )

    assert deleted is False


def test_remote_api_failure_fails_closed_without_deleting() -> None:
    assert policy is not None, "branch_cleanup_policy.py must exist"
    deleted = False

    def compare_failure(_: str) -> dict[str, int]:
        raise RuntimeError("compare API unavailable")

    def delete_ref(_: str) -> None:
        nonlocal deleted
        deleted = True

    with pytest.raises(RuntimeError, match="compare API unavailable"):
        policy.execute_manual_deletion(
            branch="copilot/already-merged",
            confirmation="DELETE copilot/already-merged",
            get_branch=lambda _: {"protected": False},
            get_open_pulls=lambda _: [],
            compare_with_main=compare_failure,
            find_references=lambda _: [],
            find_deployment_references=lambda _: [],
            delete_ref=delete_ref,
        )

    assert deleted is False


def test_manual_deletion_runs_only_after_all_checks_pass() -> None:
    assert policy is not None, "branch_cleanup_policy.py must exist"
    calls: list[str] = []

    def record(name: str, result: Any):
        def callback(_: str) -> Any:
            calls.append(name)
            return result

        return callback

    policy.execute_manual_deletion(
        branch="copilot/already-merged",
        confirmation="DELETE copilot/already-merged",
        get_branch=record("branch", {"protected": False}),
        get_open_pulls=record("pulls", []),
        compare_with_main=record("compare", {"ahead_by": 0}),
        find_references=record("references", []),
        find_deployment_references=record("deployments", []),
        delete_ref=record("delete", None),
    )

    assert calls == [
        "branch",
        "pulls",
        "compare",
        "references",
        "deployments",
        "delete",
    ]


@pytest.mark.parametrize(
    ("open_pulls", "ahead_by", "references", "deployments", "message"),
    [
        ([{"number": 1}], 0, [], [], "open pull request"),
        ([], 1, [], [], "not in main"),
        ([], 0, ["workflow.yml"], [], "referenced by active files"),
        ([], 0, [], [{"id": 42}], "referenced by a GitHub deployment"),
    ],
)
def test_manual_deletion_rejects_unsafe_branch_state(
    open_pulls: list[dict[str, int]],
    ahead_by: int,
    references: list[str],
    deployments: list[dict[str, int]],
    message: str,
) -> None:
    assert policy is not None, "branch_cleanup_policy.py must exist"

    with pytest.raises(ValueError, match=message):
        policy.execute_manual_deletion(
            branch="copilot/candidate",
            confirmation="DELETE copilot/candidate",
            get_branch=lambda _: {"protected": False},
            get_open_pulls=lambda _: open_pulls,
            compare_with_main=lambda _: {"ahead_by": ahead_by},
            find_references=lambda _: references,
            find_deployment_references=lambda _: deployments,
            delete_ref=lambda _: pytest.fail("unsafe branch was deleted"),
        )


def test_deployment_api_failure_fails_closed_without_deleting() -> None:
    assert policy is not None, "branch_cleanup_policy.py must exist"

    def deployment_failure(_: str) -> list[dict[str, int]]:
        raise RuntimeError("deployment API unavailable")

    with pytest.raises(RuntimeError, match="deployment API unavailable"):
        policy.execute_manual_deletion(
            branch="copilot/candidate",
            confirmation="DELETE copilot/candidate",
            get_branch=lambda _: {"protected": False},
            get_open_pulls=lambda _: [],
            compare_with_main=lambda _: {"ahead_by": 0},
            find_references=lambda _: [],
            find_deployment_references=deployment_failure,
            delete_ref=lambda _: pytest.fail("unsafe branch was deleted"),
        )


def test_find_active_references_scans_runtime_governance_paths(tmp_path: Path) -> None:
    assert policy is not None, "branch_cleanup_policy.py must exist"
    workflow = tmp_path / ".github" / "workflows" / "deploy.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("branch: feature/retained\n", encoding="utf-8")
    historical = tmp_path / "docs" / "history.md"
    historical.parent.mkdir(parents=True)
    historical.write_text("feature/retained\n", encoding="utf-8")

    references = policy.find_active_references(tmp_path, "feature/retained")

    assert references == [".github/workflows/deploy.yml"]


def test_render_inventory_markdown_contains_required_governance_fields() -> None:
    assert policy is not None, "branch_cleanup_policy.py must exist"
    rows = [
        {
            "owner": "copilot",
            "branch": "copilot/example",
            "head_sha": "abc123",
            "age_days": 4,
            "last_commit_date": "2026-07-09",
            "ahead_by": 2,
            "behind_by": 5,
            "associated_pr": "none",
            "disposition": "preserve",
            "reason": "branch has 2 commit(s) not in main",
        }
    ]

    markdown = policy.render_inventory_markdown(rows, generated_at="2026-07-13")

    assert "Generated at: 2026-07-13" in markdown
    assert "| Owner | Branch | Head SHA | Age (days) |" in markdown
    assert "| copilot | `copilot/example` | `abc123` | 4 |" in markdown
    assert "branch has 2 commit(s) not in main" in markdown


def test_report_owner_is_derived_from_branch_namespace() -> None:
    assert policy is not None, "branch_cleanup_policy.py must exist"

    assert policy.derive_owner("dependabot/pip/example") == "dependabot"
    assert policy.derive_owner("copilot/example") == "copilot"
    assert policy.derive_owner("agent/example") == "agent"
    assert policy.derive_owner("fix/human-change") == "bmsull560"


def test_collect_inventory_combines_remote_branch_pr_and_comparison_state(
    tmp_path: Path,
) -> None:
    assert policy is not None, "branch_cleanup_policy.py must exist"

    class FakeClient:
        def list_branches(self) -> list[dict[str, Any]]:
            return [
                {
                    "name": "copilot/unique",
                    "protected": False,
                    "commit": {"sha": "abc123"},
                },
                {
                    "name": "main",
                    "protected": True,
                    "commit": {"sha": "def456"},
                },
            ]

        def commit_date(self, sha: str) -> datetime:
            assert sha in {"abc123", "def456"}
            return datetime(2026, 7, 10, tzinfo=timezone.utc)

        def open_pulls(self, branch: str) -> list[dict[str, Any]]:
            return [{"number": 77}] if branch == "copilot/unique" else []

        def compare_with_main(self, branch: str) -> dict[str, int]:
            return {"ahead_by": 2, "behind_by": 4} if branch != "main" else {
                "ahead_by": 0,
                "behind_by": 0,
            }

    rows = policy.collect_inventory(
        FakeClient(),
        repo_root=tmp_path,
        now=datetime(2026, 7, 13, tzinfo=timezone.utc),
        stale_days=30,
    )

    assert rows[0] == {
        "owner": "copilot",
        "branch": "copilot/unique",
        "head_sha": "abc123",
        "age_days": 3,
        "last_commit_date": "2026-07-10",
        "ahead_by": 2,
        "behind_by": 4,
        "associated_pr": "#77",
        "disposition": "active",
        "reason": "branch has an open pull request",
    }
    assert rows[1]["branch"] == "main"
    assert rows[1]["disposition"] == "protected"


def test_github_client_deletes_only_encoded_head_ref() -> None:
    assert policy is not None, "branch_cleanup_policy.py must exist"
    requests: list[Any] = []

    class FakeResponse:
        headers: dict[str, str] = {}

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def read(self) -> bytes:
            return b"{}"

    def opener(request: Any) -> FakeResponse:
        requests.append(request)
        return FakeResponse()

    client = policy.GitHubClient("owner/repo", "secret", opener=opener)

    client.delete_branch("copilot/topic")

    assert len(requests) == 1
    assert requests[0].get_method() == "DELETE"
    assert requests[0].full_url.endswith("/git/refs/heads/copilot%2Ftopic")
    assert requests[0].headers["Authorization"] == "Bearer secret"
