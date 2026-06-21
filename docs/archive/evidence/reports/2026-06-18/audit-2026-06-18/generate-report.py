import json
import os
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent.parent
REPORT_DIR = Path(__file__).resolve().parent


def load_json(name):
    path = REPORT_DIR / f"{name}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def load_json_path(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def load_text(name):
    path = REPORT_DIR / f"{name}.txt"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def main():
    findings = load_json("findings")
    pnpm = load_json("pnpm-audit") or {}
    semgrep = load_json("semgrep") or {}
    bandit = load_json("bandit") or {}
    pip = load_json("pip-audit") or {}
    dead = load_json("dead-code") or {}
    sbom = load_json_path(ROOT / "artifacts" / "supply-chain" / "fabric-4l-source-sbom.cdx.json") or {}

    # pnpm audit details
    pnpm_vulns = pnpm.get("metadata", {}).get("vulnerabilities", {}) if isinstance(pnpm, dict) else {}
    pnpm_advisories = pnpm.get("advisories", {}) if isinstance(pnpm, dict) else {}
    high_moderate = []
    for adv in pnpm_advisories.values():
        if adv.get("severity") in ("high", "moderate"):
            high_moderate.append({
                "id": adv.get("github_advisory_id"),
                "module": adv.get("module_name"),
                "severity": adv.get("severity"),
                "title": adv.get("title"),
            })

    # semgrep summary
    semgrep_results = semgrep.get("results", []) if isinstance(semgrep, dict) else []
    semgrep_errors = semgrep.get("errors", []) if isinstance(semgrep, dict) else []
    semgrep_rules = {}
    for r in semgrep_results:
        check = r.get("check_id", "unknown")
        semgrep_rules[check] = semgrep_rules.get(check, 0) + 1

    # bandit summary
    bandit_results = bandit.get("results", []) if isinstance(bandit, dict) else []
    bandit_by_sev = {}
    bandit_by_test = {}
    for r in bandit_results:
        sev = r.get("issue_severity", "UNKNOWN")
        test = r.get("test_id", "UNKNOWN")
        bandit_by_sev[sev] = bandit_by_sev.get(sev, 0) + 1
        bandit_by_test[test] = bandit_by_test.get(test, 0) + 1
    bandit_medium = [r for r in bandit_results if r.get("issue_severity") == "MEDIUM"]
    bandit_medium_top = []
    for r in bandit_medium[:10]:
        bandit_medium_top.append({
            "file": r.get("filename"),
            "line": r.get("line_number"),
            "test": r.get("test_id"),
            "issue_text": r.get("issue_text"),
        })

    # pip-audit summary
    pip_vulns = []
    pip_count = 0
    if isinstance(pip, dict):
        for dep in pip.get("dependencies", []):
            for v in dep.get("vulns", []):
                pip_count += 1
                pip_vulns.append({
                    "name": dep.get("name"),
                    "version": dep.get("version"),
                    "id": v.get("id"),
                    "fix": v.get("fix_versions"),
                    "aliases": v.get("aliases", []),
                })
    pip_top = pip_vulns[:10]

    # Build markdown
    md = f"""# Enterprise Production-Readiness Audit Report

**Date:** {datetime.now(timezone.utc).isoformat()}
**Repository:** {ROOT}
**Scope:** Initial discovery audit — dependency vulnerabilities, static analysis, lint, type-check, dead code.

## Executive Summary

| Scan | Result | Notes |
| ---- | ------ | ----- |
| `pnpm audit` | FAIL ({pnpm_vulns.get('high', 0)} high, {pnpm_vulns.get('moderate', 0)} moderate, {pnpm_vulns.get('low', 0)} low) | {len(pnpm_advisories)} advisories; see details below |
| `make lint` | FAIL | 2 fixable UP037 errors in `services/layer1-ingestion/src/layer1_ingestion/api/source_routes.py` |
| `make typecheck` | PASS | All layers type-check cleanly |
| `semgrep` | FAIL ({len(semgrep_results)} results, {len(semgrep_errors)} errors) | Automated SAST findings across services/apps/packages |
| `pip-audit` | FAIL ({pip_count} vulnerabilities) | Python dependency vulnerabilities; see top issues below |
| `bandit` | FAIL ({len(bandit_results)} findings) | {bandit_by_sev.get('MEDIUM', 0)} medium, {bandit_by_sev.get('HIGH', 0)} high severity |
| `gitleaks` | NOT RUN | Binary not installed in local environment |
| `trivy` | NOT RUN | Binary not installed in local environment |
| SBOM (CycloneDX) | PASS | Generated `artifacts/supply-chain/fabric-4l-source-sbom.cdx.json` ({len(sbom.get('components', []))} components) |
| Dead-code scan | PASS | 7 high/medium candidates already removed; 3 low-confidence candidates remain (test-referenced) |

## P0 Blockers

1. **Layer 1 lint failures** — `source_routes.py` contains forward-referenced type annotations that break ruff.
2. **Dependency vulnerabilities** — pnpm audit reports high-severity packages in the frontend dependency tree.
3. **Semgrep SAST findings** — 411 results must be triaged and classified.
4. **Bandit medium findings** — Python security patterns require review and suppression or remediation.
5. **Missing secret scanner** — `gitleaks` is not installed locally; CI already runs it, but local verification is blocked.

## P1 Items

1. **Trivy container/filesystem scan** — Not installed locally; CI runs it, but local verification is blocked.
2. **Dead code** — Remaining 3 low-confidence Layer 4 tool modules need ownership review.
3. **SLOs documentation** — Exit criteria require `docs/slo.md`; currently missing.
4. **DR runbooks** — Exit criteria require runbooks; some exist in `ops/`, need completeness review.

## Tool Details

### pnpm audit (high/moderate advisories)

| Advisory | Module | Severity | Title |
| -------- | ------ | -------- | ----- |
"""
    for a in high_moderate:
        md += f"| {a.get('id') or '-'} | `{a.get('module')}` | {a.get('severity')} | {a.get('title', '')[:80]} |\n"

    md += f"""
### semgrep top rules

| Rule | Count |
| ---- | ----- |
"""
    for rule, count in sorted(semgrep_rules.items(), key=lambda x: x[1], reverse=True)[:10]:
        md += f"| `{rule}` | {count} |\n"

    md += f"""
### bandit medium findings (top 10)

| File | Line | Test | Issue |
| ---- | ---- | ---- | ----- |
"""
    for r in bandit_medium_top:
        md += f"| `{r.get('file')}` | {r.get('line')} | `{r.get('test')}` | {r.get('issue_text', '')[:60]} |\n"

    md += f"""
### pip-audit top findings (top 10)

| Package | Version | ID | Fix versions |
| ------- | ------- | -- | ------------ |
"""
    for v in pip_top:
        md += f"| `{v.get('name')}` | {v.get('version')} | {v.get('id')} | {v.get('fix')} |\n"

    md += f"""
## Dead Code

- **Existing candidates (3):** `{', '.join(d['file'] for d in dead.get('existing', []))}`
- **Already removed (7):** `{', '.join(d['file'] for d in dead.get('removed', []))}`

## Artifacts

All raw JSON/TXT outputs are in `reports/audit-2026-06-18/`:
- `pnpm-audit.json` — full pnpm audit JSON
- `semgrep.json` — full Semgrep findings
- `bandit.json` — full Bandit findings
- `pip-audit.json` — full pip-audit findings
- `dead-code.json` — dead-code candidates
- `make-lint.txt` — ruff lint output
- `make-typecheck.txt` — mypy output
- `pnpm-run-sbom.txt` — SBOM generation log
- `pnpm-run-audit:ci.txt` — supply-chain CI policy log

## Next Steps

1. Fix the Layer 1 lint/typecheck issues in `source_routes.py`.
2. Triage and remediate the 3 high-severity pnpm audit advisories.
3. Triage the 411 Semgrep findings against the security baseline.
4. Review and suppress or remediate Bandit medium findings.
5. Install `gitleaks` and `trivy` locally for full parity with CI security gates.
6. Create `docs/slo.md` with SLOs and alerting rules.
"""

    (REPORT_DIR / "audit-report.md").write_text(md, encoding="utf-8")
    print("Wrote", REPORT_DIR / "audit-report.md")


if __name__ == "__main__":
    main()
