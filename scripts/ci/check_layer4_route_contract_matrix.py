#!/usr/bin/env python3
import json,re,sys
from pathlib import Path

MATRIX=Path('contracts/layer4-route-contract-matrix.json')
OPENAPI=Path('contracts/openapi/layer4-agents.json')
ROUTE_DIRS=[Path('services/layer4-agents/src/layer4_agents/api/routes'),Path('services/layer4-agents/src/layer4_agents/feature_flags/api'),Path('services/layer4-agents/src/layer4_agents/tenants/api/routes'),Path('services/layer4-agents/src/layer4_agents/registry/api')]

pat=re.compile(r'@(?:router|[a-zA-Z_][\w]*)\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)')

def discovered_routes():
    out=set()
    for d in ROUTE_DIRS:
        if not d.exists():
            continue
        for f in d.rglob('*.py'):
            txt=f.read_text(errors='ignore')
            for m in pat.finditer(txt):
                out.add((m.group(1).upper(),m.group(2)))
    return out

def collect_refs(obj):
    refs=[]
    if isinstance(obj,dict):
        for k,v in obj.items():
            if k=='$ref' and isinstance(v,str): refs.append(v)
            refs.extend(collect_refs(v))
    elif isinstance(obj,list):
        for i in obj: refs.extend(collect_refs(i))
    return refs

def main():
    matrix=json.loads(MATRIX.read_text())
    openapi=json.loads(OPENAPI.read_text())
    paths=openapi.get('paths',{})
    components=openapi.get('components',{})
    entries={(e['method'],e['openapi_path']):e for e in matrix.get('entries',[])}
    errors=[]

    # every openapi route in matrix
    for p,ms in paths.items():
        for m in ms:
            if m.startswith('x-'): continue
            key=(m.upper(),p)
            if key not in entries:
                errors.append(f"Missing matrix entry for OpenAPI route {key[0]} {key[1]}")

    # every discovered route in matrix OR absent from openapi allowed only internal non-/api
    for m,p in discovered_routes():
        if p.startswith('/api') and (m,p) not in entries:
            errors.append(f"Missing matrix entry for discovered route {m} {p}")

    # refs exist
    for e in matrix.get('entries',[]):
        for ref in collect_refs(e):
            if not ref.startswith('#/'): continue
            cur={'components':components}
            ok=True
            for part in ref[2:].split('/'):
                if part not in cur:
                    ok=False; break
                cur=cur[part]
            if not ok:
                errors.append(f"Invalid schema reference in matrix {e['method']} {e['openapi_path']}: {ref}")

    if errors:
        print('\n'.join(errors))
        return 1
    print('Layer4 route contract matrix check passed.')
    return 0

if __name__=='__main__':
    sys.exit(main())
