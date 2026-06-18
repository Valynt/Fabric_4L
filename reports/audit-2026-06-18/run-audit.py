#!/usr/bin/env python3
"""Initial enterprise production-readiness audit runner.

Runs read-only/non-destructive scans and writes findings to the reports directory.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
REPORTS_DIR = ROOT
ARTIFACTS_DIR = REPORTS_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def run(name, cmd, *, cwd=None, check=True, capture=True):
    print(f"\n=== {name} ===")
    print(f"Command: {' '.join(cmd)}")
    executable = shutil.which(cmd[0])
    if executable is None and os.path.exists(cmd[0]):
        executable = cmd[0]
    if executable is None:
        print(f"SKIP: {cmd[0]} not found in PATH")
        return None
    result = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    print(f"Exit code: {result.returncode}")
    if result.stdout:
        print(result.stdout[:5000])
    if result.stderr:
        print(result.stderr[:5000])
    return result


def write_json(name, data):
    path = REPORTS_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {path}")
    return path


def write_text(name, text):
    path = REPORTS_DIR / f"{name}.txt"
    path.write_text(text, encoding="utf-8")
    print(f"Wrote {path}")
    return path


def main():
    findings = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "scans": {},
    }

    # 1. pnpm audit (absolute path required on Windows Python subprocess)
    pnpm_cmd = r"C:\Users\BBB\AppData\Roaming\npm\pnpm.cmd"
    pnpm_audit = run("pnpm audit", [pnpm_cmd, "audit", "--json"], check=False)
    if pnpm_audit:
        try:
            data = json.loads(pnpm_audit.stdout)
        except json.JSONDecodeError:
            data = {"raw": pnpm_audit.stdout, "error": "not valid JSON"}
        write_json("pnpm-audit", data)
        vulns = {}
        if isinstance(data, dict):
            vulns = data.get("metadata", {}).get("vulnerabilities", {})
        findings["scans"]["pnpm_audit"] = {
            "exit_code": pnpm_audit.returncode,
            "vulnerabilities": vulns,
        }

    # 2. make lint
    lint = run("make lint", ["make", "lint"], check=False)
    if lint:
        write_text("make-lint", lint.stdout + "\n" + lint.stderr)
        findings["scans"]["make_lint"] = {"exit_code": lint.returncode}

    # 3. make typecheck
    tc = run("make typecheck", ["make", "typecheck"], check=False)
    if tc:
        write_text("make-typecheck", tc.stdout + "\n" + tc.stderr)
        findings["scans"]["make_typecheck"] = {"exit_code": tc.returncode}

    # 4. gitleaks
    gl = run("gitleaks detect", ["gitleaks", "detect", "--verbose", "--exit-code", "0"], check=False)
    if gl:
        write_text("gitleaks", gl.stdout + "\n" + gl.stderr)
        findings["scans"]["gitleaks"] = {"exit_code": gl.returncode}

    # 5. semgrep — run via Python subprocess and write JSON ourselves to avoid cp1252 encoding bug
    semgrep_cmd = os.path.expanduser(r"~\AppData\Roaming\Python\Python311\Scripts\pysemgrep.exe")
    sem = run("semgrep", [semgrep_cmd, "--config", "auto", "--json", "services", "apps", "packages"], check=False)
    if sem:
        try:
            sem_data = json.loads(sem.stdout)
        except json.JSONDecodeError:
            sem_data = {"raw": sem.stdout, "error": "not valid JSON"}
        write_json("semgrep", sem_data)
        findings["scans"]["semgrep"] = {
            "exit_code": sem.returncode,
            "results": len(sem_data.get("results", [])) if isinstance(sem_data, dict) else None,
            "errors": len(sem_data.get("errors", [])) if isinstance(sem_data, dict) else None,
        }

    # 6. trivy filesystem
    trivy = run("trivy fs", ["trivy", "filesystem", "--scanners", "vuln,secret,config", "--format", "json", "--output", str(REPORTS_DIR / "trivy-fs.json"), "."], check=False)
    if trivy:
        findings["scans"]["trivy_fs"] = {"exit_code": trivy.returncode}

    # 7. pip-audit (via python -m pip_audit)
    pip_audit = run("pip-audit", [sys.executable, "-m", "pip_audit", "--format", "json", "--desc", "--output", str(REPORTS_DIR / "pip-audit.json")], check=False)
    if pip_audit:
        findings["scans"]["pip_audit"] = {"exit_code": pip_audit.returncode}

    # 8. bandit (via python -m bandit)
    bandit_json = REPORTS_DIR / "bandit.json"
    bandit = run("bandit", [sys.executable, "-m", "bandit", "-r", "services", "-ll", "-ii", "-f", "json", "-o", str(bandit_json)], check=False)
    if bandit:
        findings["scans"]["bandit"] = {"exit_code": bandit.returncode}

    findings["finished_at"] = datetime.now(timezone.utc).isoformat()
    write_json("findings", findings)
    print("\n=== Audit complete ===")
    print(f"Reports written to: {REPORTS_DIR}")


if __name__ == "__main__":
    main()
