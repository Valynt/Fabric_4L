#!/usr/bin/env python3
from __future__ import annotations
import argparse, re, sys
from pathlib import Path
import yaml
from yaml import YAMLError

ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / 'Makefile'
MAKE_TARGET_RE = re.compile(r'(?:^|[;&|]\s*)make\s+([^\n#]+)')
SCRIPT_TOKEN_RE = re.compile(r'(?:^|\s)(?:python3?|bash|sh|node)\s+([^\s\\]+)')


def load_make_targets() -> set[str]:
    out=set()
    for line in MAKEFILE.read_text(encoding='utf-8', errors='ignore').splitlines():
        if line.startswith(('\t',' ')) or ':' not in line: continue
        head=line.split(':',1)[0].strip()
        if not head or head.startswith('.') or '=' in head: continue
        for t in head.split():
            if re.fullmatch(r'[A-Za-z0-9_.\-/]+', t): out.add(t)
    return out


def extract_make_targets(run:str)->list[str]:
    ts=[]
    for chunk in MAKE_TARGET_RE.findall(run):
        for tok in re.split(r'\s+', chunk.strip()):
            if tok.startswith('-') or '=' in tok: continue
            if tok in {'&&','||','|',';','\\'}: break
            ts.append(tok); break
    return ts


def exists_path(token:str)->bool:
    token=token.strip().strip("'\"")
    if not token or token.startswith('${{') or token.startswith('/') or '*' in token or '?' in token:
        return False
    return (ROOT/token).exists()


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--workflow-glob', default='*.yml')
    args=ap.parse_args()
    workflows=sorted((ROOT/'.github/workflows').glob(args.workflow_glob))
    make_targets=load_make_targets()
    errors=[]
    for wf in workflows:
        try:data=yaml.safe_load(wf.read_text(encoding='utf-8', errors='ignore')) or {}
        except YAMLError as exc:
            print(f'warning: skipping non-parseable workflow file {wf}: {exc}')
            continue
        for job, jobdef in (data.get('jobs') or {}).items():
            run_text='\n'.join(step.get('run','') for step in jobdef.get('steps',[]) if isinstance(step,dict))
            for t in extract_make_targets(run_text):
                if t not in make_targets: errors.append(f"{wf}: job '{job}' missing make target '{t}'")
            for step in jobdef.get('steps',[]):
                if not isinstance(step,dict): continue
                run=step.get('run','')
                if isinstance(run,str):
                    for sc in SCRIPT_TOKEN_RE.findall(run):
                        if '/' in sc and not exists_path(sc):
                            errors.append(f"{wf}: job '{job}' missing script/path '{sc}'")
                if str(step.get('uses','')).startswith('actions/upload-artifact'):
                    raw=str((step.get('with') or {}).get('path',''))
                    for p in [x.strip() for x in raw.splitlines() if x.strip()]:
                        if p.startswith('${{') or '${{' in p: continue
                        if '*' in p or '?' in p:
                            prefix=p.split('*',1)[0]
                            if prefix and prefix not in run_text:
                                errors.append(f"{wf}: job '{job}' artifact path '{p}' appears never produced")
                        elif not exists_path(p) and p not in run_text:
                            errors.append(f"{wf}: job '{job}' artifact path '{p}' appears never produced")
    if errors:
        print('Workflow reference check failed:\n')
        print('\n'.join(f'- {e}' for e in errors))
        return 1
    print('Workflow reference check passed.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
