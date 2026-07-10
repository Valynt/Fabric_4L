#!/usr/bin/env python3
from __future__ import annotations
import subprocess, pathlib, re

TEST_TARGETS=[
 'services/layer4-agents/tests/test_webhook_security_matrix.py',
]
cmd=['pytest','-vv','--tb=short',*TEST_TARGETS]
proc=subprocess.run(cmd,capture_output=True,text=True)
out=proc.stdout+"\n"+proc.stderr
rows=[]
for line in out.splitlines():
 m=re.search(r"::(test_[^ ]+) (PASSED|FAILED)",line)
 if m: rows.append((m.group(1),m.group(2)))
art=pathlib.Path('artifacts'); art.mkdir(exist_ok=True)
md=art/'webhook-security-matrix.md'
with md.open('w') as f:
 f.write('# Webhook Security Test Matrix\n\n')
 f.write('| Test | Result |\n|---|---|\n')
 for name,res in rows:
  f.write(f'| {name} | {"PASS PASS" if res=="PASSED" else "FAIL FAIL"} |\n')
 f.write(f'\nOverall exit code: {proc.returncode}\n')
print(out)
raise SystemExit(proc.returncode)
