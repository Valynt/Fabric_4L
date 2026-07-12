#!/bin/bash
# Check that no production-facing YAML/Python files enable the insecure dev auth bypass.
# tests/config/test_production_defaults.py is excluded because it is a negative test
# that asserts these flags are rejected in production-like environments.
if grep -rn "ALLOW_INSECURE_DEV_AUTH_BYPASS=true" . \
    --include="*.yml" --include="*.yaml" --include="*.py" \
    --exclude="test_production_defaults.py" \
    --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules --exclude-dir=.worktrees > /dev/null; then
    echo "ERROR: ALLOW_INSECURE_DEV_AUTH_BYPASS=true found in committed files"
    exit 1
fi
echo "OK: No dev auth bypass in committed files"
