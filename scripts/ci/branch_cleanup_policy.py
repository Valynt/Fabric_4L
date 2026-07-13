#!/usr/bin/env python3
"""Fail-closed policy primitives for remote branch cleanup."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


ACTIVE_REFERENCE_ROOTS = (
    ".github/workflows",
    "config",
    "infra",
    "k8s",
    "monitoring",
)


class GitHubClient:
    """Small authenticated GitHub REST client for branch hygiene operations."""

    def __init__(
        self,
        repository: str,
        token: str,
        *,
        opener: Callable[[Request], Any] = urlopen,
    ) -> None:
        if repository.count("/") != 1:
            raise ValueError("repository must use owner/name form")
        if not token:
            raise ValueError("GITHUB_TOKEN is required")
        self.repository = repository
        self.owner = repository.split("/", 1)[0]
        self.base_url = f"https://api.github.com/repos/{repository}"
        self._opener = opener

        self._headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "fabric4l-branch-hygiene",
        }

    def _request(self, path: str, *, method: str = "GET") -> Any:
        request = Request(
            f"{self.base_url}{path}",
            method=method,
            headers=self._headers,
        )
        try:
            with self._opener(request) as response:
                body = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GitHub API {method} {path} failed with {exc.code}: {detail}"
            ) from exc
        if not body:
            return None
        return json.loads(body.decode("utf-8"))

    def list_branches(self) -> list[dict[str, Any]]:
        result = self._request("/branches?per_page=100")
        if not isinstance(result, list):
            raise RuntimeError("GitHub branches response was not a list")
        return result

    def commit_date(self, sha: str) -> datetime:
        result = self._request(f"/commits/{quote(sha, safe='')}")
        value = result["commit"]["committer"]["date"]
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    def open_pulls(self, branch: str) -> list[dict[str, Any]]:
        query = urlencode(
            {"head": f"{self.owner}:{branch}", "state": "open", "per_page": 100}
        )
        result = self._request(f"/pulls?{query}")
        if not isinstance(result, list):
            raise RuntimeError("GitHub pull request response was not a list")
        return result

    def compare_with_main(self, branch: str) -> dict[str, Any]:
        encoded = quote(branch, safe="")
        result = self._request(f"/compare/main...{encoded}")
        if not isinstance(result, dict):
            raise RuntimeError("GitHub comparison response was not an object")
        return result

    def get_branch(self, branch: str) -> dict[str, Any]:
        result = self._request(f"/branches/{quote(branch, safe='')}")
        if not isinstance(result, dict):
            raise RuntimeError("GitHub branch response was not an object")
        return result

    def deployments(self, branch: str) -> list[dict[str, Any]]:
        query = urlencode({"ref": branch, "per_page": 100})
        result = self._request(f"/deployments?{query}")
        if not isinstance(result, list):
            raise RuntimeError("GitHub deployments response was not a list")
        return result

    def delete_branch(self, branch: str) -> None:
        encoded = quote(branch, safe="")
        self._request(f"/git/refs/heads/{encoded}", method="DELETE")


@dataclass(frozen=True)
class BranchDecision:
    disposition: str
    eligible_for_manual_delete: bool
    reason: str


def derive_owner(branch: str) -> str:
    """Return the accountable owner bucket used in branch inventory."""
    namespace = branch.partition("/")[0]
    if namespace in {"agent", "copilot", "dependabot"}:
        return namespace
    return "bmsull560"


def find_active_references(repo_root: Path, branch: str) -> list[str]:
    """Find active workflow, deployment, or governance references to a branch."""
    references: list[str] = []
    for root_name in ACTIVE_REFERENCE_ROOTS:
        root = repo_root / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if branch in content:
                references.append(path.relative_to(repo_root).as_posix())
    return sorted(references)


def render_inventory_markdown(
    rows: list[dict[str, Any]], *, generated_at: str
) -> str:
    """Render the canonical branch-inventory table."""
    lines = [
        "# Branch Inventory",
        "",
        f"Generated at: {generated_at}",
        "",
        "| Owner | Branch | Head SHA | Age (days) | Last commit date | Ahead / Behind | Associated PR | Disposition | Reason |",
        "|---|---|---|---:|---|---:|---|---|---|",
    ]
    for row in rows:
        reason = str(row["reason"]).replace("|", "\\|")
        lines.append(
            f"| {row['owner']} | `{row['branch']}` | `{row['head_sha']}` | "
            f"{row['age_days']} | {row['last_commit_date']} | "
            f"{row['ahead_by']} / {row['behind_by']} | {row['associated_pr']} | "
            f"{row['disposition']} | {reason} |"
        )
    lines.append("")
    return "\n".join(lines)


def collect_inventory(
    client: Any,
    *,
    repo_root: Path,
    now: datetime,
    stale_days: int,
) -> list[dict[str, Any]]:
    """Collect and classify the current remote branch inventory."""
    rows: list[dict[str, Any]] = []
    for branch_info in client.list_branches():
        name = str(branch_info["name"])
        head_sha = str(branch_info["commit"]["sha"])
        commit_date = client.commit_date(head_sha)
        age_days = max(0, (now - commit_date).days)
        pulls = client.open_pulls(name)
        comparison = client.compare_with_main(name)
        ahead_by = int(comparison["ahead_by"])
        behind_by = int(comparison["behind_by"])
        decision = classify_branch(
            name=name,
            protected=bool(branch_info.get("protected", False)),
            ahead_by=ahead_by,
            has_open_pr=bool(pulls),
            stale=age_days >= stale_days,
        )
        associated_pr = ", ".join(f"#{pull['number']}" for pull in pulls) or "none"
        rows.append(
            {
                "owner": derive_owner(name),
                "branch": name,
                "head_sha": head_sha[:12],
                "age_days": age_days,
                "last_commit_date": commit_date.date().isoformat(),
                "ahead_by": ahead_by,
                "behind_by": behind_by,
                "associated_pr": associated_pr,
                "disposition": decision.disposition,
                "reason": decision.reason,
            }
        )
    return sorted(rows, key=lambda row: str(row["branch"]))


def classify_branch(
    *,
    name: str,
    protected: bool,
    ahead_by: int,
    has_open_pr: bool,
    stale: bool,
) -> BranchDecision:
    """Classify a branch without performing any mutation."""
    if name == "main" or name.startswith("release/") or protected:
        return BranchDecision("protected", False, "branch is protected by policy")
    if has_open_pr:
        return BranchDecision("active", False, "branch has an open pull request")
    if ahead_by > 0:
        return BranchDecision(
            "preserve", False, f"branch has {ahead_by} commit(s) not in main"
        )
    if ahead_by == 0:
        return BranchDecision(
            "merged-candidate", True, "branch is fully contained in main"
        )
    return BranchDecision(
        "review", False, "branch comparison is unavailable or incomplete"
    )


def execute_manual_deletion(
    *,
    branch: str,
    confirmation: str,
    get_branch: Callable[[str], dict[str, Any]],
    get_open_pulls: Callable[[str], list[dict[str, Any]]],
    compare_with_main: Callable[[str], dict[str, Any]],
    find_references: Callable[[str], list[str]],
    find_deployment_references: Callable[[str], list[dict[str, Any]]],
    delete_ref: Callable[[str], None],
) -> None:
    """Delete exactly one fully merged branch after every safety check passes."""
    expected = f"DELETE {branch}"
    if confirmation != expected:
        raise ValueError(f"confirmation must equal {expected}")

    branch_info = get_branch(branch)
    if branch == "main" or branch.startswith("release/") or branch_info.get(
        "protected", False
    ):
        raise ValueError(f"branch {branch} is protected")

    open_pulls = get_open_pulls(branch)
    if open_pulls:
        raise ValueError(f"branch {branch} has an open pull request")

    comparison = compare_with_main(branch)
    ahead_by = comparison.get("ahead_by")
    if not isinstance(ahead_by, int):
        raise ValueError("branch comparison did not return an integer ahead_by")
    if ahead_by > 0:
        raise ValueError(f"branch {branch} has {ahead_by} commit(s) not in main")

    references = find_references(branch)
    if references:
        joined = ", ".join(references)
        raise ValueError(f"branch {branch} is referenced by active files: {joined}")

    deployments = find_deployment_references(branch)
    if deployments:
        raise ValueError(f"branch {branch} is referenced by a GitHub deployment")

    delete_ref(branch)


def _write_report(
    rows: list[dict[str, Any]],
    *,
    json_path: Path,
    markdown_path: Path,
    generated_at: str,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(
        render_inventory_markdown(rows, generated_at=generated_at),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("report", "delete"))
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).parents[2])
    parser.add_argument("--stale-days", type=int, default=30)
    parser.add_argument(
        "--output-json", type=Path, default=Path("artifacts/branch-inventory.json")
    )
    parser.add_argument(
        "--output-markdown", type=Path, default=Path("artifacts/branch-inventory.md")
    )
    parser.add_argument("--branch", default="")
    parser.add_argument("--confirmation", default="")
    args = parser.parse_args(argv)

    client = GitHubClient(args.repo, args.token)
    repo_root = args.repo_root.resolve()
    if args.mode == "report":
        now = datetime.now(timezone.utc)
        rows = collect_inventory(
            client,
            repo_root=repo_root,
            now=now,
            stale_days=args.stale_days,
        )
        _write_report(
            rows,
            json_path=args.output_json,
            markdown_path=args.output_markdown,
            generated_at=now.isoformat(),
        )
        print(f"Branch inventory generated for {len(rows)} branches.")
        return 0

    if not args.branch:
        parser.error("--branch is required in delete mode")
    execute_manual_deletion(
        branch=args.branch,
        confirmation=args.confirmation,
        get_branch=client.get_branch,
        get_open_pulls=client.open_pulls,
            compare_with_main=client.compare_with_main,
            find_references=lambda branch: find_active_references(repo_root, branch),
            find_deployment_references=client.deployments,
            delete_ref=client.delete_branch,
    )
    print(f"Deleted fully merged branch: {args.branch}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
