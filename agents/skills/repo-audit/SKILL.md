---
name: repo-audit
description: >-
  Autonomous repository health auditing with scorecard tracking, finding management,
  and remediation sprint planning. Use when the user asks to audit the repo, check codebase
  health, review scorecards, manage findings, or plan remediation sprints.
---

# Repository Health Audit

Autonomous repository health auditing with scorecard tracking, finding management, and remediation sprint planning.

## Skill Metadata
- **Version**: 1.2.0
- **Category**: engineering
triggers:
  - pattern: "audit.*repo"
    action: run_full_audit
  - pattern: "check.*health|health.*check"
    action: run_full_audit
  - pattern: "score.*card|scorecard"
    action: get_latest_scorecard
  - pattern: "finding.*status|update.*finding"
    action: update_finding
  - pattern: "sprint.*plan|roadmap"
    action: get_sprint_plan
  - pattern: "repo.*status|how.*healthy"
    action: get_quick_status
inputs:
  - repo_url: str (required)
  - branch: str (default: main)
  - incremental: bool (default: true)
  - areas: list[AuditArea] (default: all)
outputs:
  - scorecard: Scorecard
  - findings: list[Finding]
  - sprints: list[Sprint]
  - report: Markdown string
  - report_path: str
permissions:
  - read: repository
  - read: .git/
  - write: audit_reports/
  - write: .audit_cache/
