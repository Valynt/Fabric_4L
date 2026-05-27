#!/usr/bin/env python3
"""Extract and triage issues from recent PR merge commits."""

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = REPO_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def run_git(args, check=False):
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT)] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git command failed")
    return result


def ensure_origin_main_available():
    """Fail fast if origin/main is unavailable."""
    probe = run_git(["rev-parse", "--verify", "origin/main^{commit}"])
    if probe.returncode != 0:
        raise RuntimeError(
            "Preflight failed: origin/main is unavailable. "
            "Run `git fetch origin main` and retry."
        )


def get_merge_commits(limit=20, base_ref="origin/main"):
    """Return list of merge commits that look like PR merges from explicit base ref history."""
    retrieval_command = (
        f"git -C {REPO_ROOT} log {base_ref} --format=%H|%P|%s "
        f"--grep='Merge pull request' -n {limit}"
    )
    log_result = run_git(
        ["log", base_ref, "--format=%H|%P|%s", "--grep=Merge pull request", "-n", str(limit)],
        check=True,
    )
    commits = []
    for line in log_result.stdout.strip().splitlines():
        if "|" not in line:
            continue
        sha, parents, msg = line.split("|", 2)
        commits.append({"sha": sha, "parents": parents.split(), "message": msg})

    window = {
        "base_ref": base_ref,
        "limit": limit,
        "retrieval_command": retrieval_command,
        "start_sha": commits[-1]["sha"] if commits else None,
        "end_sha": commits[0]["sha"] if commits else None,
    }
    return commits, window


def get_pr_number(msg):
    m = re.search(r"Merge pull request #(\d+)", msg)
    return int(m.group(1)) if m else None


def get_branch_name(msg):
    m = re.search(r"Merge pull request #\d+ from \S+/(\S+)", msg)
    return m.group(1) if m else None


def get_diff(sha, parents):
    """Diff between merge base and the merge commit (what the PR introduced)."""
    if len(parents) >= 2:
        return run_git(["diff", f"{parents[0]}..{sha}"], check=True).stdout
    return run_git(["diff", f"{sha}~1..{sha}"], check=True).stdout


def scan_diff(diff_text, pr_num, sha, branch):
    findings = []
    lines = diff_text.splitlines()
    current_file = None
    line_no = 0

    smell_keywords = ["TODO", "FIXME", "HACK", "XXX", "NOTE:", "WARN"]

    def add_finding(category, severity, description, refs=None):
        findings.append(
            {
                "category": category,
                "severity": severity,
                "description": description,
                "pr_number": pr_num,
                "commit_sha": sha,
                "branch": branch,
                "references": refs or [],
            }
        )

    for line in lines:
        if line.startswith("diff --git"):
            m = re.search(r"diff --git a/(\S+) b/(\S+)", line)
            if m:
                current_file = m.group(2)
            line_no = 0
            continue
        if line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            if m:
                line_no = int(m.group(1)) - 1
            continue
        if line.startswith("+") and not line.startswith("+++"):
            line_no += 1
            content = line[1:]

            for kw in smell_keywords:
                if kw in content.upper():
                    add_finding(
                        "code_smell",
                        "Medium",
                        f"{kw} comment found in added code: {content.strip()[:120]}",
                        refs=[{"file": current_file, "line": line_no}],
                    )

            if re.search(r"^\s*except\s*:\s*$", content):
                add_finding(
                    "exception_handling",
                    "High",
                    "Bare 'except:' clause swallows all exceptions including KeyboardInterrupt.",
                    refs=[{"file": current_file, "line": line_no}],
                )

            if re.search(r"except\s+\w+\s*:\s*pass", content):
                add_finding(
                    "exception_handling",
                    "High",
                    "Exception block with 'pass' silently swallows errors.",
                    refs=[{"file": current_file, "line": line_no}],
                )

            if re.search(r'(?i)(api_key|secret|password|token)\s*=\s*["\'][\w\-]{8,}["\']', content):
                is_test_file = "test" in (current_file or "").lower()
                add_finding(
                    "security",
                    "Low" if is_test_file else "Critical",
                    "Potential hardcoded secret or credential in source code.",
                    refs=[{"file": current_file, "line": line_no}],
                )

            if re.search(r"^\s*print\(", content) and "test" not in (current_file or "").lower():
                add_finding(
                    "code_smell",
                    "Low",
                    f"Leftover print() statement in non-test code: {content.strip()[:80]}",
                    refs=[{"file": current_file, "line": line_no}],
                )

            if re.search(r"(?i)\b(race|concurrent|thread|lock|mutex)\b", content):
                add_finding(
                    "concurrency",
                    "Medium",
                    f"Concurrency-related code change: {content.strip()[:120]}",
                    refs=[{"file": current_file, "line": line_no}],
                )

    return findings


def deduplicate(findings):
    seen = set()
    out = []
    for f in findings:
        key = (f["category"], f["severity"], f["description"], f["pr_number"])
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def main():
    ensure_origin_main_available()
    commits, commit_window = get_merge_commits(limit=20, base_ref="origin/main")
    all_findings = []

    print(f"Scanning {len(commits)} PR merge commits...")
    for c in commits:
        pr = get_pr_number(c["message"])
        branch = get_branch_name(c["message"])
        print(f"  PR #{pr} ({c['sha'][:8]}) branch={branch}")
        diff = get_diff(c["sha"], c["parents"])
        findings = scan_diff(diff, pr, c["sha"], branch)
        all_findings.extend(findings)

    all_findings = deduplicate(all_findings)
    all_findings.sort(key=lambda x: (SEVERITY_ORDER.get(x["severity"], 99), x["pr_number"]))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scanned_commits": len(commits),
        "commit_window": commit_window,
        "total_findings": len(all_findings),
        "findings": all_findings,
    }

    out_path = REPORTS_DIR / f"pr-bug-triage-{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport written to {out_path}")
    print(f"Total findings: {len(all_findings)}")
    for sev in ["Critical", "High", "Medium", "Low"]:
        count = sum(1 for f in all_findings if f["severity"] == sev)
        if count:
            print(f"  {sev}: {count}")


if __name__ == "__main__":
    main()
