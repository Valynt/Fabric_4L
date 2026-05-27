#!/usr/bin/env python3
from __future__ import annotations
import re
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / 'config/ci/value_fabric_deep_import_baseline.txt'
PAT = re.compile(r'^\s*(?:from|import)\s+(value_fabric\.[\w\.]+)')
viol=[]
for p in (ROOT/'services').rglob('*.py'):
    rel=p.relative_to(ROOT).as_posix()
    if '/tests/' in rel or rel.endswith('/adapters/value_fabric_api.py'):
        continue
    for i,l in enumerate(p.read_text(encoding='utf-8',errors='ignore').splitlines(),1):
        m=PAT.match(l)
        if not m: continue
        mod=m.group(1)
        if mod.startswith('value_fabric.public_api') or mod=='value_fabric.shared':
            continue
        if mod.startswith('value_fabric.shared.'):
            viol.append(f'{rel}:{i}:{mod}')

baseline=set(BASELINE.read_text().splitlines()) if BASELINE.exists() else set()
new=[v for v in viol if v and v not in baseline]
if new:
    print('New non-public value_fabric.shared deep imports detected:')
    print('\n'.join(new))
    sys.exit(1)
print(f'OK: {len(viol)} non-public shared imports (baseline-locked); new=0')
