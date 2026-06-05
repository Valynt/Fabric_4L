from __future__ import annotations

import ast
from pathlib import Path

from scripts.ci.check_route_tenant_propagation import RouteTenantVisitor, build_parser


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


def test_allows_tenant_forwarding_from_authenticated_context() -> None:
    src = '''
@router.get("/x")
async def handler(_ctx: RequestContext, service=Depends(get_service)):
    return await service.fetch(tenant_id=str(_ctx.tenant_id), account_id="a1")
'''
    violations = _check(src)
    assert violations == []


def test_allows_tenant_bound_repository_owner() -> None:
    src = '''
@router.get("/x")
async def handler(tenant_id: str, db=Depends(get_db)):
    repo = SignalRepository(db, tenant_id)
    return await repo.fetch(account_id="a1")
'''
    violations = _check(src)
    assert violations == []


def test_allows_tenant_bound_request_object() -> None:
    src = '''
@router.post("/x")
async def handler(tenant_id: str, service=Depends(get_service)):
    idem_request = IdempotencyRequest(tenant_id=tenant_id, endpoint_key="POST /x")
    return await service.check_replay(idem_request)
'''
    violations = _check(src)
    assert violations == []


def test_strict_flag_is_supported() -> None:
    args = build_parser().parse_args(["--strict"])
    assert args.strict is True
