#!/usr/bin/env bash
# Audit the service's frozen production dependency export. Scanner failures and
# export failures fail closed. Vulnerability blocking policy is selected
# independently through PIP_AUDIT_VULNERABILITY_POLICY.
set -euo pipefail

readonly vulnerability_policy="${PIP_AUDIT_VULNERABILITY_POLICY:-any}"
if [[ "${vulnerability_policy}" != "any" ]]; then
  echo "Unsupported PIP_AUDIT_VULNERABILITY_POLICY: ${vulnerability_policy}" >&2
  exit 64
fi

requirements_file="$(mktemp)"
trap 'rm -f "${requirements_file}"' EXIT

uv export \
  --frozen \
  --all-extras \
  --no-dev \
  --no-emit-project \
  --format requirements-txt \
  --output-file "${requirements_file}"

set +e
uvx --from pip-audit==2.9.0 pip-audit \
  --requirement "${requirements_file}" \
  --no-deps \
  --disable-pip
audit_status=$?
set -e

case "${audit_status}" in
  0)
    exit 0
    ;;
  1)
    echo "pip-audit found a vulnerability; policy '${vulnerability_policy}' blocks any finding." >&2
    exit 1
    ;;
  *)
    echo "pip-audit scanner failed with exit code ${audit_status}; failing closed." >&2
    exit "${audit_status}"
    ;;
esac
