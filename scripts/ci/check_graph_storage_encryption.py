#!/usr/bin/env python3
"""Validate graph storage encryption posture for Kubernetes manifests."""
from __future__ import annotations
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
POLICY = yaml.safe_load((ROOT / 'config/ci/graph-storage-encryption-policy.yaml').read_text())
MANIFESTS = [ROOT / 'k8s/neo4j.yml', ROOT / 'k8s/base/neo4j.yml']


def docs(manifest: Path):
    return [x for x in yaml.safe_load_all(manifest.read_text()) if isinstance(x, dict)]

errors = []
for manifest in MANIFESTS:
    found = {}
    for d in docs(manifest):
        if d.get('kind') != 'PersistentVolumeClaim':
            continue
        name = d.get('metadata', {}).get('name')
        if name not in POLICY['required_pvcs']:
            continue
        found[name] = True
        sc = d.get('spec', {}).get('storageClassName')
        if sc not in POLICY['allowed_encrypted_storage_classes']:
            errors.append(f"{manifest}: PVC {name} storageClassName={sc!r} is not an approved encrypted class")
        ann = d.get('metadata', {}).get('annotations', {})
        if ann.get(POLICY['required_annotation_key']) != POLICY['required_annotation_value']:
            errors.append(f"{manifest}: PVC {name} missing required encryption annotation")
    for req in POLICY['required_pvcs']:
        if req not in found:
            errors.append(f"{manifest}: missing required PVC {req}")

if errors:
    print('Graph storage encryption check failed:')
    for err in errors:
        print(' -', err)
    sys.exit(1)

print('Graph storage encryption check passed')
