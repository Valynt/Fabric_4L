#!/bin/bash
# validate-non-root-posture.sh
#
# Validates that all Deployments, StatefulSets, and DaemonSets in the
# k8s/base directory have securityContext.runAsNonRoot=true set.
#
# Usage:
#   ./scripts/k8s/validate-non-root-posture.sh
#
# Returns:
#   0 if all resources have non-root posture
#   1 if validation fails

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_BASE_DIR="${SCRIPT_DIR}/../../k8s/base"

echo "Validating workload securityContext baseline across all Deployments/StatefulSets/DaemonSets..."

python3 - <<'PY'
from pathlib import Path
import sys
import yaml

base = Path("k8s/base")
files = sorted([*base.rglob("*.yml"), *base.rglob("*.yaml")])
if not files:
    print(f"No YAML files found in {base}")
    sys.exit(1)

def truthy(v): return v is True
required_container = ("allowPrivilegeEscalation", "readOnlyRootFilesystem", "capabilities")
required_pod = ("runAsNonRoot", "seccompProfile")
failures = 0
checked = 0

for f in files:
    for doc in yaml.safe_load_all(f.read_text()):
        if not isinstance(doc, dict):
            continue
        kind = doc.get("kind")
        if kind not in {"Deployment", "StatefulSet", "DaemonSet"}:
            continue
        checked += 1
        name = doc.get("metadata", {}).get("name", "unknown")
        spec = doc.get("spec", {}).get("template", {}).get("spec", {})
        pod_sc = spec.get("securityContext", {}) or {}
        errs = []
        if not truthy(pod_sc.get("runAsNonRoot")):
            errs.append("pod securityContext.runAsNonRoot != true")
        seccomp_type = ((pod_sc.get("seccompProfile") or {}).get("type"))
        if seccomp_type != "RuntimeDefault":
            errs.append("pod securityContext.seccompProfile.type != RuntimeDefault")
        for container_type in ("initContainers", "containers"):
            for c in spec.get(container_type, []) or []:
                c_name = c.get("name", "unknown")
                sc = c.get("securityContext", {}) or {}
                if sc.get("allowPrivilegeEscalation") is not False:
                    errs.append(f"{container_type}.{c_name} missing allowPrivilegeEscalation=false")
                if sc.get("readOnlyRootFilesystem") is not True:
                    errs.append(f"{container_type}.{c_name} missing readOnlyRootFilesystem=true")
                drops = ((sc.get("capabilities") or {}).get("drop") or [])
                if "ALL" not in drops:
                    errs.append(f"{container_type}.{c_name} missing capabilities.drop=[ALL]")
        if errs:
            failures += 1
            print(f"✗ FAIL: {f} ({kind} {name})")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"✓ PASS: {f} ({kind} {name})")

print(f"\nValidation complete: {failures} failures out of {checked} resources checked")
sys.exit(1 if failures else 0)
PY
