import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
pnpm_cmd = r"C:\Users\BBB\AppData\Roaming\npm\pnpm.cmd"

for script in ["sbom", "audit:ci"]:
    print(f"\n=== pnpm run {script} ===")
    result = subprocess.run(
        [pnpm_cmd, "run", script],
        cwd=repo_root,
        capture_output=True,
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
    (repo_root / f"reports/audit-2026-06-18/pnpm-run-{script}.txt").write_text(
        f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}", encoding="utf-8"
    )
