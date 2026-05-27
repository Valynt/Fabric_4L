from __future__ import annotations

import ast
from pathlib import Path

from scripts.ci.check_route_tenant_propagation import RouteTenantVisitor


def _check(src: str):
    tree = ast.parse(src)
    v = RouteTenantVisitor(Path("inline.py"))
    v.visit(tree)
    return v.violations


def test_flags_missing_tenant_forwarding() -> None:
    src = '''
@router.get("/x")
async def handler(tenant_id: str, service=Depends(get_service)):
    return await service.fetch(account_id="a1")
'''
    violations = _check(src)
    assert violations


def test_allows_tenant_forwarding() -> None:
    src = '''
@router.get("/x")
async def handler(tenant_id: str, service=Depends(get_service)):
    return await service.fetch(tenant_id=tenant_id, account_id="a1")
'''
    violations = _check(src)
    assert violations == []
