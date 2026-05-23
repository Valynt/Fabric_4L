#!/usr/bin/env bash
# validate-monitoring-stack.sh
# Validates monitoring stack YAML syntax, compose config integrity, and
# runbook URL coverage for all alerts defined in rules files.
#
# Usage: ./scripts/ci/validate-monitoring-stack.sh
# Exit code: 0 if all checks pass, non-zero otherwise.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${PROJECT_ROOT}"

ERRORS=0

echo "=== Validating monitoring YAML syntax ==="

python3 -c "
import yaml, sys, glob, os

files = (
    glob.glob('monitoring/**/*.yml', recursive=True)
    + glob.glob('monitoring/**/*.yaml', recursive=True)
    + ['k8s/base/monitoring-alertmanager.yml', 'k8s/base/monitoring-prometheus.yml']
)

ok = 0
fail = 0
for f in files:
    try:
        with open(f, encoding='utf-8') as fh:
            if '---' in fh.read():
                fh.seek(0)
                list(yaml.safe_load_all(fh))
            else:
                fh.seek(0)
                yaml.safe_load(fh)
        ok += 1
    except Exception as e:
        print(f'FAIL: {f} -> {e}', file=sys.stderr)
        fail += 1

print(f'YAML check: {ok} passed, {fail} failed')
sys.exit(1 if fail else 0)
" || ERRORS=$((ERRORS + 1))

echo ""
echo "=== Validating docker-compose.monitoring.yml ==="

if docker compose -f docker-compose.monitoring.yml config > /dev/null 2>&1; then
    echo "docker-compose.monitoring.yml: OK"
else
    echo "FAIL: docker-compose.monitoring.yml config validation failed" >&2
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "=== Validating runbook URL coverage ==="

python3 -c "
import yaml, re, sys, os

runbook_dirs = [
    'docs/troubleshooting/runbooks',
    'docs/troubleshooting/runbooks/infrastructure',
    'docs/troubleshooting/runbooks/application',
    'docs/troubleshooting/runbooks/incident',
    'docs/operations/runbooks',
]

# Build a set of existing runbook filenames
existing = set()
for d in runbook_dirs:
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.endswith('.md'):
                existing.add(f)

rules_files = [
    'monitoring/alerting/rules.yml',
    'monitoring/alerting/rules-production.yml',
    'monitoring/alerting/loki-rules.yml',
]

missing = 0
for rf in rules_files:
    if not os.path.exists(rf):
        print(f'SKIP: {rf} not found')
        continue
    with open(rf, encoding='utf-8') as fh:
        docs = list(yaml.safe_load_all(fh))
    for doc in docs:
        if not doc or 'groups' not in doc:
            continue
        for group in doc['groups']:
            for rule in group.get('rules', []):
                url = rule.get('annotations', {}).get('runbook_url', '')
                if not url:
                    continue
                # Extract filename from GitHub/raw URL path
                m = re.search(r'/([^/]+\\.md)$', url)
                if not m:
                    continue
                fname = m.group(1)
                if fname not in existing:
                    alert = rule.get('alert', 'unknown')
                    print(f'MISSING: {alert} in {rf} -> {fname}')
                    missing += 1

print(f'Runbook check: {missing} missing runbooks')
sys.exit(1 if missing else 0)
" || ERRORS=$((ERRORS + 1))

echo ""
if [ "$ERRORS" -eq 0 ]; then
    echo "All monitoring stack validation checks passed."
    exit 0
else
    echo "Validation failed with $ERRORS error(s)."
    exit 1
fi
