#!/usr/bin/env python3
"""Verify change approval from authenticated GitHub data.

The gate deliberately does not read evidence from the checked-out revision.  A
review file in the revision is both self-attested and impossible to key by the
revision that contains it.  Instead, the GitHub API is the source of truth for
the pull request author, changed files, review decision, and submitted reviews.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
HIGH_RISK_PREFIXES = (".github/", "contracts/", "k8s/", "scripts/ci/", "config/ci/")


def _fail(errors: list[str], message: str) -> None:
    errors.append(message)
    print(f"POLICY FAIL: {message}", file=sys.stderr)


def _event_head(
    event_name: str, event: dict[str, Any], errors: list[str]
) -> str | None:
    if event_name == "pull_request":
        head = event.get("pull_request", {}).get("head", {}).get("sha")
    elif event_name == "merge_group":
        head = event.get("merge_group", {}).get("head_sha")
    else:
        _fail(
            errors,
            f"unsupported event {event_name!r}; expected pull_request or merge_group",
        )
        return None
    if not isinstance(head, str) or not SHA_RE.fullmatch(head):
        _fail(errors, f"event head SHA missing or malformed: {head!r}")
        return None
    return head


def _gh_json(arguments: list[str]) -> Any:
    process = subprocess.run(
        ["gh", "api", *arguments], capture_output=True, text=True, check=False
    )
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or "GitHub API request failed")
    decoder = json.JSONDecoder()
    documents: list[Any] = []
    remaining = process.stdout.lstrip()
    while remaining:
        document, offset = decoder.raw_decode(remaining)
        documents.append(document)
        remaining = remaining[offset:].lstrip()
    if len(documents) == 1:
        return documents[0]
    if all(isinstance(document, list) for document in documents):
        return [item for document in documents for item in document]
    raise RuntimeError("GitHub API returned an unexpected paginated response")


def _pull_numbers(
    event_name: str, event: dict[str, Any], repository: str, head: str
) -> list[int]:
    if event_name == "pull_request":
        number = event.get("pull_request", {}).get("number") or event.get("number")
        if not isinstance(number, int):
            raise RuntimeError("pull_request event is missing its number")
        return [number]
    pulls = _gh_json([f"repos/{repository}/commits/{head}/pulls"])
    numbers = sorted(
        {pull.get("number") for pull in pulls if isinstance(pull.get("number"), int)}
    )
    if not numbers:
        raise RuntimeError(
            f"no pull requests are associated with merge-group commit {head}"
        )
    return numbers


def _validate_pull(repository: str, number: int, errors: list[str]) -> None:
    pull = _gh_json([f"repos/{repository}/pulls/{number}"])
    reviews = _gh_json([f"repos/{repository}/pulls/{number}/reviews", "--paginate"])
    files = _gh_json([f"repos/{repository}/pulls/{number}/files", "--paginate"])
    owner, name = repository.split("/", 1)
    decision_data = _gh_json(
        [
            "graphql",
            "-f",
            "query=query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){pullRequest(number:$number){reviewDecision}}}",
            "-f",
            f"owner={owner}",
            "-f",
            f"name={name}",
            "-F",
            f"number={number}",
        ]
    )

    author = pull.get("user", {}).get("login")
    if not isinstance(author, str) or not author:
        _fail(errors, f"PR #{number} has no authenticated author identity")
        return

    # Only each reviewer's latest submitted state is authoritative.  This
    # prevents an old approval from surviving a later changes-requested review.
    latest: dict[str, str] = {}
    for review in reviews:
        login = review.get("user", {}).get("login")
        state = review.get("state")
        if isinstance(login, str) and isinstance(state, str):
            latest[login] = state.upper()
    approvers = sorted(
        login
        for login, state in latest.items()
        if state == "APPROVED" and login != author
    )
    if not approvers:
        _fail(
            errors,
            f"PR #{number} has no current approval from a reviewer other than {author!r}",
        )

    high_risk = sorted(
        file["filename"]
        for file in files
        if isinstance(file.get("filename"), str)
        and file["filename"].startswith(HIGH_RISK_PREFIXES)
    )
    review_decision = (
        decision_data.get("data", {})
        .get("repository", {})
        .get("pullRequest", {})
        .get("reviewDecision")
    )
    if review_decision != "APPROVED":
        detail = " for high-risk changes" if high_risk else ""
        _fail(
            errors,
            f"PR #{number} GitHub review decision is {review_decision!r}, not 'APPROVED'{detail}",
        )
    print(
        f"PR #{number}: GitHub reports {len(approvers)} independent approver(s) and "
        f"{len(high_risk)} high-risk file(s)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Trusted GitHub independent-review policy gate"
    )
    parser.add_argument(
        "--event-path",
        type=Path,
        default=Path(os.environ.get("GITHUB_EVENT_PATH", "/dev/null")),
    )
    args = parser.parse_args(argv)
    errors: list[str] = []
    try:
        event = json.loads(args.event_path.read_text(encoding="utf-8"))
        event_name = os.environ.get("GITHUB_EVENT_NAME", "")
        repository = os.environ.get("GITHUB_REPOSITORY", "")
        if not repository or "/" not in repository:
            raise RuntimeError("GITHUB_REPOSITORY is missing or malformed")
        head = _event_head(event_name, event, errors)
        if head is None:
            return 1
        for number in _pull_numbers(event_name, event, repository, head):
            _validate_pull(repository, number, errors)
    except (OSError, json.JSONDecodeError, RuntimeError) as exc:
        _fail(errors, str(exc))
    if errors:
        print(
            f"09-change-risk-and-approval FAILED with {len(errors)} policy violation(s)",
            file=sys.stderr,
        )
        return 1
    print("09-change-risk-and-approval PASSED using authenticated GitHub review data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
