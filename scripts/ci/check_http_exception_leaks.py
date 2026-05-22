#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROUTE_GLOBS = [
    ROOT / 'services/layer3-knowledge/src/api/routes',
    ROOT / 'services/layer4-agents/src/api/routes',
    ROOT / 'value_fabric/layer3/api/routes',
    ROOT / 'value_fabric/layer4/api/routes',
]
PATTERN = re.compile(r"HTTPException\([^\n]*str\(e\)|detail\s*=\s*f['\"][^\n]*\{str\(e\)\}")

violations=[]
changed_files = set()
diff = ROOT.joinpath(".git")
if diff.exists():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    changed_files = {line.strip() for line in result.stdout.splitlines() if line.strip()}

for base in RUNTIME_ROUTE_GLOBS:
    if not base.exists():
        continue
    for path in base.rglob('*.py'):
        rel = str(path.relative_to(ROOT))
        if changed_files and rel not in changed_files:
            continue
        text=path.read_text(encoding='utf-8')
        for i,line in enumerate(text.splitlines(),1):
            if PATTERN.search(line):
                violations.append(f"{rel}:{i}:{line.strip()}")

if violations:
    print('Disallowed HTTPException detail leak pattern(s) found:')
    print('\n'.join(violations))
    sys.exit(1)
print('No disallowed HTTPException(... str(e) ...) patterns found in runtime routes.')
