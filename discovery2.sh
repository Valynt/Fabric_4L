#!/bin/bash
set -e
echo "=== API ROUTES ==="
grep -rE '(@router|@app|\.get\(|\.post\(|\.put\(|\.delete\()' services/api/app/routers/ --include='*.py' | head -30

echo "=== FRONTEND ROUTES ==="
grep -rE "(createBrowserRouter|path:.*'|route\()" apps/web/src/ --include='*.ts' --include='*.tsx' | head -20

echo "=== DB SESSION ==="
grep -rE '(get_db|get_session|async_session|create_session|db_session)' services/api/app/ --include='*.py' | head -15

echo "=== ENGINE ==="
grep -rE '(engine\.connect|SessionLocal|scoped_session)' services/api/app/ --include='*.py' | head -10

echo "=== RLS ==="
grep -rE '(RLS|row_level_security|USING|WITH CHECK|tenant_id)' services/api/app/ --include='*.sql' | head -10

echo "=== AUTH DEPENDS ==="
grep -rE '(Depends.*auth|require_auth|get_current_user|check_permission|has_role)' services/api/app/ --include='*.py' | head -15

echo "=== ROLE PERM ==="
grep -rE 'role|permission|admin' services/api/app/ --include='*.py' | grep -i 'require|check|verify' | head -10

echo "=== PROTECTED ROUTE ==="
grep -rE 'RouteGuard|ProtectedRoute|useAuth' apps/web/src/ --include='*.tsx' --include='*.ts' | head -10

echo "=== MARKERS ==="
grep -r '@pytest.mark' tests/ --include='*.py' | head -20

echo "=== TEST FILES ALL ==="
find tests/ -name '*.py' | sort

echo "=== DONE ==="
