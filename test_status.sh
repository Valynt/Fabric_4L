#!/bin/bash
set -e
echo "=== LAYER7 BILLING TESTS ==="
cd services/layer7-billing
python -m pytest tests/ -v --tb=short 2>&1 | head -80 || true
cd ../..

echo "=== LAYER1 CELERY TESTS ==="
cd services/layer1-ingestion
python -m pytest tests/unit/test_l2_celery_dispatch.py -v --tb=short 2>&1 | head -40 || true
cd ../..

echo "=== SHARED STORAGE TESTS ==="
cd packages/shared
python -m pytest src/value_fabric/shared/storage/tests/ -v --tb=short 2>&1 | head -40 || true
cd ../..

echo "=== DONE ==="
