#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARTIFACT_DIR="${ROOT_DIR}/artifacts/zero-trust"
mkdir -p "${ARTIFACT_DIR}"

summary_file="${ARTIFACT_DIR}/summary.md"
network_json="${ARTIFACT_DIR}/network_policy_checks.json"
tenant_json="${ARTIFACT_DIR}/tenant_isolation_checks.json"
auth_json="${ARTIFACT_DIR}/service_auth_checks.json"

pass_count=0
fail_count=0

check_file_contains() {
  local file="$1"
  local pattern="$2"
  if [[ -f "$file" ]] && grep -qE "$pattern" "$file"; then
    return 0
  fi
  return 1
}

record() {
  local name="$1"
  local status="$2"
  local details="$3"
  if [[ "$status" == "pass" ]]; then
    ((pass_count+=1))
  else
    ((fail_count+=1))
  fi
  printf -- "- [%s] %s — %s\n" "$status" "$name" "$details" >> "$summary_file"
}

: > "$summary_file"
{
  echo "# Zero Trust Validation Summary"
  echo
  echo "Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo
} >> "$summary_file"

# ----------------------
# ZT-1 Network policy checks
# ----------------------
np_deny_file="${ROOT_DIR}/k8s/base/network-policies/deny-all.yml"
np_kustomization="${ROOT_DIR}/k8s/base/network-policies/kustomization.yaml"

if check_file_contains "$np_deny_file" "kind:\\s*NetworkPolicy" && check_file_contains "$np_deny_file" "default-deny-all"; then
  record "ZT-1.1 default deny policy exists" "pass" "deny-all policy found"
  np11=true
else
  record "ZT-1.1 default deny policy exists" "fail" "missing deny-all policy or name"
  np11=false
fi

if check_file_contains "$np_kustomization" "deny-all.yml"; then
  record "ZT-1.2 kustomization includes deny-all" "pass" "deny-all.yml referenced"
  np12=true
else
  record "ZT-1.2 kustomization includes deny-all" "fail" "deny-all.yml not referenced"
  np12=false
fi

required_policies=(layer1-policy.yml layer2-policy.yml layer3-policy.yml layer4-policy.yml layer5-policy.yml layer6-policy.yml frontend-policy.yml)
missing=()
for policy in "${required_policies[@]}"; do
  [[ -f "${ROOT_DIR}/k8s/base/network-policies/${policy}" ]] || missing+=("${policy}")
done

if [[ ${#missing[@]} -eq 0 ]]; then
  record "ZT-1.3 layer allowlist policies present" "pass" "all expected per-layer policies exist"
  np13=true
else
  record "ZT-1.3 layer allowlist policies present" "fail" "missing: ${missing[*]}"
  np13=false
fi

cat > "$network_json" <<JSON
{
  "default_deny_exists": ${np11},
  "deny_all_in_kustomization": ${np12},
  "layer_policies_present": ${np13}
}
JSON

# ----------------------
# ZT-2 Tenant isolation checks
# ----------------------
isolation_file="${ROOT_DIR}/packages/shared/src/value_fabric/shared/identity/isolation.py"
jwt_tests="${ROOT_DIR}/packages/shared/src/value_fabric/shared/identity/tests/test_jwt.py"
middleware_file="${ROOT_DIR}/packages/shared/src/value_fabric/shared/identity/middleware.py"

if check_file_contains "$isolation_file" "class TenantScopedMixin" && check_file_contains "$isolation_file" "class TenantScopedCypher" && check_file_contains "$isolation_file" "def tenant_cache_key"; then
  record "ZT-2.1 tenant isolation primitives" "pass" "TenantScopedMixin/TenantScopedCypher/tenant_cache_key found"
  ti21=true
else
  record "ZT-2.1 tenant isolation primitives" "fail" "missing one or more isolation primitives"
  ti21=false
fi

if check_file_contains "$middleware_file" "Authorization" && check_file_contains "$middleware_file" "X-Tenant-ID"; then
  record "ZT-2.2 identity-to-tenant resolution path" "pass" "middleware tenant resolution controls found"
  ti22=true
else
  record "ZT-2.2 identity-to-tenant resolution path" "fail" "tenant resolution controls not found"
  ti22=false
fi

if check_file_contains "$jwt_tests" "test_missing_tenant_claim_returns_none" && check_file_contains "$jwt_tests" "test_invalid_tenant_uuid_returns_none"; then
  record "ZT-2.3 tenant claim negative tests exist" "pass" "jwt tests cover invalid tenant claim paths"
  ti23=true
else
  record "ZT-2.3 tenant claim negative tests exist" "fail" "jwt tenant negative tests missing"
  ti23=false
fi

cat > "$tenant_json" <<JSON
{
  "tenant_isolation_primitives_present": ${ti21},
  "tenant_resolution_controls_present": ${ti22},
  "tenant_negative_tests_present": ${ti23}
}
JSON

# ----------------------
# ZT-3 Service auth checks
# ----------------------
deps_file="${ROOT_DIR}/packages/shared/src/value_fabric/shared/identity/dependencies.py"
l4_settings_file="${ROOT_DIR}/services/layer4-agents/src/layer4_agents/config/settings.py"

if check_file_contains "$middleware_file" "Bearer" && check_file_contains "$middleware_file" "X-API-Key"; then
  record "ZT-3.1 service authn paths" "pass" "Bearer + API key support found"
  sa31=true
else
  record "ZT-3.1 service authn paths" "fail" "missing bearer or api-key auth path"
  sa31=false
fi

if check_file_contains "$deps_file" "def require_role" && check_file_contains "$deps_file" "def require_permission"; then
  record "ZT-3.2 authz dependency controls" "pass" "role/permission checks found"
  sa32=true
else
  record "ZT-3.2 authz dependency controls" "fail" "role/permission checks missing"
  sa32=false
fi

if check_file_contains "$l4_settings_file" "JWT_SECRET" && check_file_contains "$l4_settings_file" "at least 32 characters"; then
  record "ZT-3.3 strong JWT secret policy" "pass" "JWT secret enforcement found"
  sa33=true
else
  record "ZT-3.3 strong JWT secret policy" "fail" "JWT secret enforcement not found"
  sa33=false
fi

cat > "$auth_json" <<JSON
{
  "service_authn_paths_present": ${sa31},
  "service_authz_controls_present": ${sa32},
  "jwt_secret_policy_present": ${sa33}
}
JSON

{
  echo
  echo "Totals: pass=${pass_count}, fail=${fail_count}"
} >> "$summary_file"

if [[ "$fail_count" -gt 0 ]]; then
  echo "Zero trust validation failed with ${fail_count} failing checks. See ${summary_file}." >&2
  exit 1
fi

echo "Zero trust validation passed. Evidence written to ${ARTIFACT_DIR}."
