#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo " Fabric 4L Dev Environment Health Verification"
echo "=================================================="

FAILED=0

check_cmd() {
  local name="$1"
  local cmd="$2"
  local version_output

  if ! version_output=$(eval "$cmd" 2>&1); then
    echo "  [FAIL] $name: command failed or not found ($cmd)"
    echo "         Output: $version_output"
    FAILED=$((FAILED + 1))
    return 1
  else
    local first_line
    first_line=$(echo "$version_output" | head -n 1)
    echo "  [OK]   $name: $first_line"
    return 0
  fi
}

echo ""
echo "--- Python & Tooling ---"
# Python must be 3.11.x
python_ver=$(python3 --version 2>&1 || true)
if [[ "$python_ver" =~ ^Python\ 3\.11\. ]]; then
  echo "  [OK]   python: $python_ver (3.11.x required)"
else
  echo "  [FAIL] python: $python_ver (must be Python 3.11.x)"
  FAILED=$((FAILED + 1))
fi

check_cmd "uv" "uv --version"

echo ""
echo "--- Node.js & JavaScript Tooling ---"
# Node must be 22.x
node_ver=$(node --version 2>&1 || true)
if [[ "$node_ver" =~ ^v22\. ]]; then
  echo "  [OK]   node: $node_ver (22.x required)"
else
  echo "  [FAIL] node: $node_ver (must be Node.js 22.x)"
  FAILED=$((FAILED + 1))
fi

check_cmd "pnpm" "pnpm --version"

echo ""
echo "--- Container & Cloud Native Tooling ---"
check_cmd "docker CLI" "docker --version"
check_cmd "docker compose" "docker compose version"

if docker info >/dev/null 2>&1; then
  server_ver=$(docker info --format '{{.ServerVersion}}' 2>/dev/null || echo "reachable")
  echo "  [OK]   docker daemon (DinD): reachable (server: $server_ver)"
else
  echo "  [FAIL] docker daemon (DinD): unreachable at DOCKER_HOST=${DOCKER_HOST:-unix:///var/run/docker.sock}"
  FAILED=$((FAILED + 1))
fi

check_cmd "kubectl" "kubectl version --client"
check_cmd "kustomize" "kustomize version"
check_cmd "cosign" "cosign version"

echo ""
echo "--- Secrets & Developer Utilities ---"
check_cmd "infisical" "infisical --version"
check_cmd "gh (GitHub CLI)" "gh --version"
check_cmd "make" "make --version"
check_cmd "jq" "jq --version"

echo ""
echo "=================================================="
if [ "$FAILED" -eq 0 ]; then
  echo " ALL CHECKS PASSED: Environment is healthy."
  echo "=================================================="
  exit 0
else
  echo " FAILED: $FAILED check(s) failed."
  echo "=================================================="
  exit 1
fi
