from pathlib import Path

from scripts.ci import boundary_check


def test_detects_prohibited_runtime_patterns(tmp_path: Path) -> None:
    target = tmp_path / "runtime_violation.py"
    target.write_text(
        'def bad_patterns(request, payload, api_key):\n'
        '    tenant = request.headers.get("X-Tenant-ID")\n'
        '    maybe = request.query_params.get("tenant_id")\n'
        '    data_tenant = payload.get("tenant_id")\n'
        '    key_tenant = api_key.tenant_id\n'
        '    fallback = getattr(api_key, "tenant_id", None)\n'
    )
    violations = boundary_check.find_violations_in_file(target)
    assert violations
    assert any("request.headers.get" in v["content"] for v in violations)


def test_allows_shared_resolver_and_fixtures() -> None:
    allowlisted_fixture = Path("tests/fixtures/security/boundary_check/allowlisted_fixture.py")
    assert boundary_check.is_allowlisted(allowlisted_fixture)
    assert boundary_check.find_violations_in_file(allowlisted_fixture) == []


def test_strict_flag_is_supported() -> None:
    parser = boundary_check.build_parser()
    args = parser.parse_args(["--strict"])
    assert args.strict is True
