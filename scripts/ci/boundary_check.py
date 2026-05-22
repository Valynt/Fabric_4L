"""CI gate: detect prohibited tenant inference in runtime source trees."""
from __future__ import annotations
import argparse, re, subprocess, sys
from pathlib import Path

DENY_PATTERNS = [
    r'request\.headers\.get\s*\(\s*["\"]X-Tenant-ID["\"]',
    r'request\.query_params',
    r'\b(?:request\.query_params|query_params|query|params|payload|body|request_body|data)\.get\s*\(\s*["\"]tenant_id["\"]',
    r'api_key\.tenant_id',
    r'getattr\s*\(\s*api_key\s*,\s*["\"]tenant_id["\"]',
]
ALLOWLIST_PATHS = [
    "packages/shared/src/shared/boundaries/tenant_boundary.py",
    "packages/shared/src/shared/identity/context.py",
    "packages/shared/src/shared/identity/middleware.py",
    "tests/security/test_boundary_check_static.py",
    "tests/fixtures/security/boundary_check/",
]
RUNTIME_ROOTS = [Path("services"), Path("value_fabric"), Path("packages/shared/src/shared")]

def is_allowlisted(p: Path)->bool: return any(a in str(p).replace('\\','/') for a in ALLOWLIST_PATHS)

def changed_lines(base_ref:str)->dict[str,set[int]]:
    diff = subprocess.run(["git","diff","--unified=0","--no-color",f"{base_ref}...HEAD","--","*.py"],capture_output=True,text=True,check=False).stdout
    out:dict[str,set[int]]={}; cur=None
    for line in diff.splitlines():
        if line.startswith("+++ b/"): cur=line[6:]; out.setdefault(cur,set())
        elif line.startswith("@@") and cur:
            m=re.search(r"\+(\d+)(?:,(\d+))?",line)
            if not m: continue
            start=int(m.group(1)); count=int(m.group(2) or "1")
            for n in range(start,start+count): out[cur].add(n)
    return out

def find_violations_in_file(filepath: Path, only_lines:set[int]|None=None)->list[dict]:
    if is_allowlisted(filepath): return []
    v=[]
    for i,line in enumerate(filepath.read_text(encoding='utf-8').splitlines(),1):
        if only_lines is not None and i not in only_lines: continue
        for p in DENY_PATTERNS:
            if re.search(p,line,re.IGNORECASE): v.append({"line":i,"content":line.strip()}); break
    return v

def main()->None:
    ap=argparse.ArgumentParser(); ap.add_argument('--base-ref'); args=ap.parse_args()
    touched = changed_lines(args.base_ref) if args.base_ref else None
    violations={}
    for root in [r for r in RUNTIME_ROOTS if r.exists()]:
        for f in root.rglob('*.py'):
            s=str(f).replace('\\','/')
            if any(x in s for x in ['/tests/','/.venv/','/site-packages/']): continue
            rel=s
            line_scope = touched.get(rel) if touched is not None else None
            if touched is not None and not line_scope: continue
            found=find_violations_in_file(f,line_scope)
            if found: violations[f]=found
    if not violations:
        print('✓ No tenant boundary violations detected'); sys.exit(0)
    total=0
    for fp,vs in sorted(violations.items()):
        print(f"\n{fp}")
        for x in vs: print(f"  Line {x['line']}: {x['content'][:120]}"); total+=1
    print(f"\nFAIL: {len(violations)} files with {total} boundary violations")
    sys.exit(1)

if __name__=='__main__': main()
