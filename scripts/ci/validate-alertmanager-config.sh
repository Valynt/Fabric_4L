#!/bin/bash
# Validate Alertmanager configuration before deployment
# Usage: ./validate-alertmanager-config.sh [config_file]

set -e

CONFIG_FILE="${1:-k8s/base/monitoring-alertmanager.yml}"
AMTOOL="${AMTOOL:-amtool}"

if ! command -v "$AMTOOL" &> /dev/null; then
    echo "⚠️  amtool not found. Installing..."
    # Try to install via go or docker
    if command -v go &> /dev/null; then
        go install github.com/prometheus/alertmanager/cmd/amtool@latest
        # Ensure the freshly-built binary is on PATH for the rest of the script.
        export PATH="$(go env GOPATH)/bin:${PATH}"
    elif command -v docker &> /dev/null; then
        echo "Using docker to run amtool validation..."
        AMBIN="docker run --rm -i prom/alertmanager:v0.28.1 amtool"
    else
        echo "❌ amtool not available and cannot be installed"
        echo "   Install: go install github.com/prometheus/alertmanager/cmd/amtool@latest"
        exit 1
    fi
fi

echo "🔍 Validating Alertmanager configuration..."
echo "   File: $CONFIG_FILE"

# Extract alertmanager.yml from ConfigMap
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Parse ConfigMap and extract alertmanager.yml
python3 << 'EOF' - "$CONFIG_FILE" "$TEMP_DIR"
import sys
import yaml
import os

config_file = sys.argv[1]
temp_dir = sys.argv[2]

with open(config_file, 'r') as f:
    docs = list(yaml.safe_load_all(f))

for doc in docs:
    if doc and doc.get('kind') == 'ConfigMap':
        data = doc.get('data', {})
        for key, value in data.items():
            if key.endswith('.yml') or key.endswith('.yaml'):
                output_path = os.path.join(temp_dir, key)
                with open(output_path, 'w') as out:
                    out.write(value)
                print(f"📄 Extracted: {key} -> {output_path}")
EOF

# Validate each config file
VALIDATION_FAILED=0
for config in "$TEMP_DIR"/*.yml "$TEMP_DIR"/*.yaml; do
    if [ -f "$config" ]; then
        echo ""
        echo "✅ Validating: $(basename "$config")"
        sed -i 's#\${ALERTMANAGER_DEFAULT_WEBHOOK_URL:-http://localhost:5001/webhook}#http://localhost:5001/webhook#g' "$config"
        sed -i 's#\${ALERTMANAGER_CRITICAL_WEBHOOK_URL:-http://localhost:5001/webhook}#http://localhost:5001/webhook#g' "$config"
        sed -i 's#\${ALERTMANAGER_WARNING_WEBHOOK_URL:-http://localhost:5001/webhook}#http://localhost:5001/webhook#g' "$config"
        if [ -n "$AMBIN" ]; then
            # Use docker
            if ! $AMBIN check-config "$config" 2>&1; then
                VALIDATION_FAILED=1
            fi
        else
            if ! $AMTOOL check-config "$config" 2>&1; then
                VALIDATION_FAILED=1
            fi
        fi
    fi
done

echo ""
if [ $VALIDATION_FAILED -eq 0 ]; then
    echo "🎉 All Alertmanager configurations are valid!"
    exit 0
else
    echo "❌ Validation failed. Please fix the configuration errors above."
    exit 1
fi
