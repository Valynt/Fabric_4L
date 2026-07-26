#!/usr/bin/env python3
from __future__ import annotations
import argparse,re
from pathlib import Path
LEGACY_TOKEN='value-fabric/'
SCAN_DIRS=('services','scripts','tests')
SKIP_PREFIXES=('docs/archive/','.venv/','node_modules/')
SKIP_FILES={'MIGRATION_REPORT.md','canonical-paths.yaml','tests/ci/test_legacy_path_guard.py','scripts/verification/migration_verification_checklist.sh','scripts/ci/legacy_path_guard.py'}
IGNORE_PATTERNS=[re.compile(p) for p in (
    r'@value-fabric/',r'value-fabric\.io/',r'secret/(data/)?value-fabric/',r'cluster\.local/ns/value-fabric/',
    r'\.value-fabric\.',r'/var/log/value-fabric/',r'value-fabric\.svc\.cluster\.local',r'fabric-4l/value-fabric/',
    r'value-fabric/(security-leads|qa-leads|backend-leads|frontend-leads|infrastructure)(?:["/]|$)',
    r'value-fabric/\$\{layer\}',r'\.config/value-fabric/crawler\.yml',r'ghcr\\?\.io/value-fabric/ci-tools/security-suite',
)]

def should_scan(path: Path, root: Path)->bool:
    rel=path.relative_to(root).as_posix()
    if (
        any(rel.startswith(s) for s in SKIP_PREFIXES)
        or rel in SKIP_FILES
        or path.is_dir()
        or "__pycache__" in path.parts
        or path.suffix == ".pyc"
    ):
        return False
    return True

def is_ignored(line:str)->bool:
    return any(p.search(line) for p in IGNORE_PATTERNS)

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default='.')
    root=Path(ap.parse_args().repo_root).resolve(); violations=[]
    for d in SCAN_DIRS:
        p=root/d
        if not p.exists(): continue
        for f in p.rglob('*'):
            if not should_scan(f,root): continue
            txt=f.read_text(encoding='utf-8',errors='ignore')
            for i,l in enumerate(txt.splitlines(),1):
                if LEGACY_TOKEN in l and not is_ignored(l): violations.append((f.relative_to(root).as_posix(),i,l.strip()))
    if violations:
        print('Legacy filesystem path references detected:')
        for v in violations: print(f' - {v[0]}:{v[1]}: {v[2]}')
        return 1
    print('PASS: no legacy `value-fabric/` filesystem references found in active code/config.')
    return 0
if __name__=='__main__': raise SystemExit(main())
