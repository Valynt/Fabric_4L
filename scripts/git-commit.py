import subprocess
from pathlib import Path

repo = Path("C:/Users/BBB/Fabric_4L")
message = """feat: initial audit phase — lint, SLOs, dependency patches, and L1 test sync

- Fix Layer 1 ruff UP037 lint failure in source_routes.py
- Create docs/slo.md with platform/layer SLOs and burn-rate alerting
- Resolve 3 high-severity pnpm audit advisories:
  - react-router via apps/web ^7.15.0
  - tmp / form-data via root pnpm.overrides
- Regenerate pnpm-lock.yaml and re-run audit scans
- Sync Layer 1 Celery stage helper names with tests (_*_stage_async)
- Record all findings in reports/audit-2026-06-18/
- Add prioritized backlog in .kimi/backlog.yaml and journal in .kimi/journal.md

Co-authored-by: Ona <no-reply@ona.com>
"""

for cmd in [
    ["git", "add", "-A"],
    ["git", "commit", "-m", message],
]:
    result = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        raise SystemExit(result.returncode)

print("Committed successfully.")
