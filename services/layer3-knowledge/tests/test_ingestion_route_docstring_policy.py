"""Policy checks for Layer 3 ingestion route security documentation."""

from src.api.routes import ingestion


def test_ingestion_route_module_docstring_states_authenticated_tenant_source() -> None:
    """Route module docs must explicitly encode the authenticated-context tenant policy."""
    doc = ingestion.__doc__ or ""

    required_snippets = (
        "derived",
        "exclusively from authenticated request context",
        "never from X-Tenant-ID",
    )

    for snippet in required_snippets:
        assert snippet in doc

    forbidden_snippet = "authenticated request context or the X-Tenant-ID header"
    assert forbidden_snippet not in doc
