#!/bin/bash
if grep -rn "ALLOW_INSECURE_DEV_AUTH_BYPASS=true" . --include="*.yml" --include="*.yaml" --include="*.py" > /dev/null; then
    echo "ERROR: ALLOW_INSECURE_DEV_AUTH_BYPASS=true found in committed files"
    exit 1
fi
echo "OK: No dev auth bypass in committed files"
