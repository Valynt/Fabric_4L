#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

RUNTIME_STRICT_PREFIX = "packages/shared/src/value_fabric/shared/"


@dataclass(frozen=True)
class AllowRule:
    path: str
    rationale: str


def load_allowlist(path: Path) -> dict[str, AllowRule]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    rules: dict[str, AllowRule] = {}
    for item in data.get("allow", []):
        p = str(item.get("path", "")).strip()
        r = str(item.get("rationale", "")).strip()
        if p:
            rules[p] = AllowRule(path=p, rationale=r)
    return rules


def normalize(paths: list[str]) -> set[str]:
    return {p.strip().replace('\\', '/') for p in paths if p and p.strip()}


def parse_expected_reason(body: str) -> str:
    m = re.search(r"(?mis)^##\s*Why overlap is expected\s*\n(.*?)(?:\n##\s|\Z)", body or "")
    return (m.group(1).strip() if m else "")


def area(path: str) -> str:
    parts = path.split('/')
    return '/'.join(parts[:3]) if len(parts) >= 3 else (parts[0] if parts else "")


def fetch_recent_merged(owner: str, repo: str, token: str, limit: int) -> list[dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=closed&base=main&sort=updated&direction=desc&per_page={min(100, limit*4)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        prs = json.load(resp)
    merged = [pr for pr in prs if pr.get("merged_at")][:limit]
    return merged


def fetch_pr_files(owner: str, repo: str, number: int, token: str) -> set[str]:
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}/files?per_page=100"
    files: list[str] = []
    page = 1
    while True:
        req = urllib.request.Request(url + f"&page={page}", headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            chunk = json.load(resp)
        if not chunk:
            break
        files.extend(str(f.get("filename", "")) for f in chunk)
        if len(chunk) < 100:
            break
        page += 1
    return normalize(files)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--allowlist", default="config/ci/pr_overlap_allowlist.json")
    ap.add_argument("--threshold", type=float, default=0.35)
    ap.add_argument("--recent", type=int, default=12)
    ap.add_argument("--changed-files", default=os.environ.get("CHANGED_FILES", ""))
    ap.add_argument("--fixture", default=os.environ.get("PR_OVERLAP_FIXTURE", ""))
    args = ap.parse_args()

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("No GITHUB_EVENT_PATH; skipping overlap guard.")
        return 0
    payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    pr = payload.get("pull_request") or {}
    if not pr:
        print("Not a PR event; skipping overlap guard.")
        return 0

    changed = normalize(args.changed_files.split())
    if not changed:
        print("No changed files supplied; skipping overlap guard.")
        return 0

    allow = load_allowlist(Path(args.allowlist))
    strict = {p for p in changed if p.startswith(RUNTIME_STRICT_PREFIX)}
    filtered = {p for p in changed if (p not in allow or p.startswith(RUNTIME_STRICT_PREFIX))}
    if not filtered:
        print("Only allowlisted hot files changed; overlap guard passed.")
        return 0

    token = os.environ.get("GITHUB_TOKEN")
    repo_full = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or "/" not in repo_full:
        print("Missing GITHUB_TOKEN or GITHUB_REPOSITORY; cannot evaluate overlap.")
        return 1
    owner, repo = repo_full.split('/', 1)

    fixture = {}
    if args.fixture:
        fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    merged_prs = fixture.get("merged_prs") if fixture else fetch_recent_merged(owner, repo, token, args.recent)
    by_area = {area(p) for p in filtered}
    highest = 0.0
    details = None
    for item in merged_prs:
        files = normalize((fixture.get("pr_files", {}).get(str(item["number"]), []) if fixture else [])) or fetch_pr_files(owner, repo, int(item["number"]), token)
        candidate = {f for f in files if area(f) in by_area}
        if not candidate:
            continue
        overlap = len(filtered & candidate) / max(len(filtered), 1)
        if overlap > highest:
            highest = overlap
            details = (item["number"], overlap, sorted(filtered & candidate)[:20])

    print(f"Max overlap ratio vs last {len(merged_prs)} merged PRs: {highest:.2%}")
    if details:
        print(f"Most overlapping merged PR #{details[0]} overlap={details[1]:.2%}")

    reason_text = parse_expected_reason(str(pr.get("body") or ""))
    if highest >= args.threshold and not reason_text:
        print("ERROR: overlap threshold exceeded but PR body is missing section 'Why overlap is expected'.")
        print("Include a non-empty section heading '## Why overlap is expected'.")
        return 1

    if strict and highest >= args.threshold and len(reason_text) < 20:
        print("ERROR: strict runtime shared-module overlap exceeded and explanation is too short.")
        return 1

    print("PR overlap guard passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
