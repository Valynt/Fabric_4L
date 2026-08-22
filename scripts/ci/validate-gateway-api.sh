#!/usr/bin/env bash
# Validate that the production overlay includes Gateway API routing resources
# and that TLS certificate references are correctly configured.
#
# Usage:
#   bash scripts/ci/validate-gateway-api.sh [overlay-path]
#
# Defaults:
#   overlay-path: k8s/deployments/prod-gateway-api
#
# Exit codes:
#   0  Gateway API resources are properly integrated
#   1  Validation failed
#
set -euo pipefail

OVERLAY="${1:-k8s/deployments/prod-gateway-api}"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TMPDIR}"' EXIT

echo "==> Validating Gateway API integration for overlay: ${OVERLAY}"

if ! command -v kustomize >/dev/null 2>&1; then
  echo "::error::kustomize is required" >&2
  exit 1
fi

if [[ ! -f "${OVERLAY}/kustomization.yaml" ]]; then
  echo "::error::Overlay not found: ${OVERLAY}/kustomization.yaml" >&2
  exit 1
fi

MANIFEST="${TMPDIR}/rendered.yaml"
kustomize build --load-restrictor=LoadRestrictionsNone "${OVERLAY}" > "${MANIFEST}"

ERRORS=0

# Use Python/PyYAML for robust multi-document YAML assertions. This avoids
# differences in yq output formatting between local tooling and CI runners.
python3 - "${MANIFEST}" <<'PY' || ERRORS=$((ERRORS + 1))
import sys
import yaml

manifest_path = sys.argv[1]
errors = []

try:
    with open(manifest_path, "r", encoding="utf-8") as f:
        docs = list(yaml.safe_load_all(f))
except yaml.YAMLError as exc:
    errors.append(f"Failed to parse rendered manifest: {exc}")
    docs = []

resources = {}
for doc in docs:
    if not isinstance(doc, dict):
        continue
    kind = doc.get("kind")
    name = doc.get("metadata", {}).get("name")
    if kind and name:
        resources.setdefault(kind, set()).add(name)

# Check 1: Gateway resource exists
if "Gateway" not in resources or "value-fabric-gateway" not in resources["Gateway"]:
    errors.append("Gateway 'value-fabric-gateway' not found in rendered output")

# Check 2: HTTPRoute resources exist
http_routes = resources.get("HTTPRoute", set())
for route in ("application",):
    if route not in http_routes:
        errors.append(f"HTTPRoute '{route}' not found in rendered output")

# Check 3: Certificate resources exist with valid issuerRef
certs = [d for d in docs if isinstance(d, dict) and d.get("kind") == "Certificate"]
cert_names = {c.get("metadata", {}).get("name") for c in certs}
for cert in ("frontend-tls",):
    if cert not in cert_names:
        errors.append(f"Certificate '{cert}' not found in rendered output")

issuer_refs = {
    c.get("spec", {}).get("issuerRef", {}).get("name")
    for c in certs
    if isinstance(c.get("spec", {}).get("issuerRef"), dict)
}
if "letsencrypt-prod" not in issuer_refs:
    errors.append("Certificate issuerRef 'letsencrypt-prod' not found")

# Check 4: Hostnames are replaced (no placeholder hostnames remain)
with open(manifest_path, "r", encoding="utf-8") as f:
    raw = f.read()
for placeholder in ("__HOST__", "__API_HOST__"):
    if placeholder in raw:
        errors.append(f"Unresolved {placeholder} placeholder found in rendered output")

# Check 5: Warn on conflicting ingress resources
ingresses = resources.get("Ingress", set())
if ingresses:
    print(f"::warning::Ingress resources found alongside Gateway API (potential conflict): {sorted(ingresses)}")

if errors:
    for err in errors:
        print(f"::error::{err}")
    sys.exit(1)

print("==> Python YAML validation passed")
PY

# Preserve the bash ERRORS counter above by checking the Python exit code explicitly.
# The heredoc already exits non-zero on error and increments ERRORS via '||'.

echo ""
if [[ ${ERRORS} -eq 0 ]]; then
  echo "==> PASS: Gateway API resources are properly integrated in ${OVERLAY}"
  exit 0
else
  echo "==> FAIL: ${ERRORS} Gateway API integration error(s) detected"
  exit 1
fi
