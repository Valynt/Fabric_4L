import ast
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "ci"
    / "check_layer5_tenant_isolation_matrix.py"
)
SPEC = spec_from_file_location("check_layer5_tenant_isolation_matrix", MODULE_PATH)
check = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(check)


def test_extract_route_from_decorator_get_with_path():
    source = """
@router.get("/entities")
async def list_entities(): ...
"""
    tree = ast.parse(source)
    dec = tree.body[0].decorator_list[0]
    assert check._extract_route_from_decorator(dec) == ("GET", "/api/v1/entities")


def test_extract_route_from_decorator_post_with_path():
    source = """
@router.post("/entities/{entity_id}/verify")
async def verify_entity(): ...
"""
    tree = ast.parse(source)
    dec = tree.body[0].decorator_list[0]
    assert check._extract_route_from_decorator(dec) == (
        "POST",
        "/api/v1/entities/{entity_id}/verify",
    )


def test_extract_route_from_decorator_returns_none_for_non_router_decorator():
    source = """
@some_other_decorator
async def fn(): ...
"""
    tree = ast.parse(source)
    dec = tree.body[0].decorator_list[0]
    assert check._extract_route_from_decorator(dec) is None


def test_has_caller_dependency_detects_get_current_user():
    source = """
async def read_entity(
    entity_id: str,
    caller: User = Depends(get_current_user),
): ...
"""
    tree = ast.parse(source)
    node = tree.body[0]
    assert check._has_caller_dependency(node) is True


def test_has_caller_dependency_returns_false_when_no_caller():
    source = """
async def read_entity(entity_id: str): ...
"""
    tree = ast.parse(source)
    node = tree.body[0]
    assert check._has_caller_dependency(node) is False


def test_has_caller_dependency_returns_false_for_wrong_dependency():
    source = """
async def read_entity(
    entity_id: str,
    caller: User = Depends(get_optional_user),
): ...
"""
    tree = ast.parse(source)
    node = tree.body[0]
    assert check._has_caller_dependency(node) is False
