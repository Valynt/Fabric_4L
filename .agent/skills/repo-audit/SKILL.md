skill: repo-audit
name: Repository Health Audit
version: 1.2.0
description: Autonomous repository health auditing with scorecard tracking, finding management, and remediation sprint planning.
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
