#!/bin/bash
set -e
echo "=== SERVICES ==="
ls -1 services/

echo "=== APPS ==="
ls -1 apps/

echo "=== PACKS ==="
ls -1 packs/

echo "=== TESTS (top-level) ==="
find . -maxdepth 2 -name 'test_*.py' -o -maxdepth 2 -name '*_test.py' | head -20

echo "=== PYTEST INI ==="
head -40 pytest.ini

echo "=== MAKEFILE TESTS ==="
grep -E '^test' Makefile | head -10

echo "=== WEB PKG TESTS ==="
grep -A1 '"test"' apps/web/package.json | head -5

echo "=== WORKFLOWS ==="
ls -1 .github/workflows/ | head -15

echo "=== AUTH FILES (tenant_id) ==="
grep -rl 'tenant_id' services/ --include='*.py' | head -15

echo "=== DECORATORS ==="
grep -rE '@require_|@protected|@authorized|@permission_required' services/ --include='*.py' | head -10

echo "=== HTTP EXC ==="
grep -rE '(raise.*Forbidden|raise.*Unauthorized|HTTPException.*403|HTTPException.*401|abort.*403)' services/ --include='*.py' | head -15

echo "=== BASEMODEL ==="
grep -rE 'BaseModel|validator|Field' services/ --include='*.py' | head -15

echo "=== IDEMPOTENCY ==="
grep -rE 'idempotency|dedup' services/ --include='*.py' | head -10

echo "=== DONE ==="
