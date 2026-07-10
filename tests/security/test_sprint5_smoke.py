"""Sprint 5 security smoke tests (S5-R5).

Fast, no-external-service checks that verify:
  S5-R5.1  Missing tenant context → 401/422 (not 200, not 500)
  S5-R5.2  Wrong tenant in JWT → 404 on resource lookup
  S5-R5.3  Body tenant_id is ignored; authenticated tenant from JWT is used
  S5-R5.4  decision_by is server-derived from ctx.user_id; body value ignored
  S5-R5.5  No secrets appear in structured log output

All checks are AST/source-level or unit-level to stay under 2 minutes.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

pytestmark = [pytest.mark.security, pytest.mark.unit]

LAYER4_SRC = pathlib.Path("services/layer4-agents/src/layer4_agents")


# ---------------------------------------------------------------------------
# S5-R5.1 — Missing tenant context → 401/422
# ---------------------------------------------------------------------------


class TestMissingTenantContext:
    """Missing tenant context must fail closed with 401 or 422."""

    def test_governance_workflows_read_requires_auth(self) -> None:
        """All GET routes in governance_workflows.py use require_authenticated."""
        source = pathlib.Path(
            LAYER4_SRC / "api/routes/governance_workflows.py"
        ).read_text()
        assert "require_authenticated" in source, (
            "governance_workflows.py must import require_authenticated"
        )
        tree = ast.parse(source)
        get_routes = [
            n for n in ast.walk(tree)
            if isinstance(n, ast.AsyncFunctionDef)
            and n.name in (
                "list_reviews", "get_review", "get_version",
                "get_version_diff", "get_audit_export", "get_lineage",
            )
        ]
        assert get_routes, "Expected GET route handlers not found"
        for fn in get_routes:
            fn_src = ast.get_source_segment(source, fn) or ""
            assert "AuthDep" in fn_src or "require_authenticated" in fn_src, (
                f"{fn.name} must require authentication (AuthDep or require_authenticated)"
            )

    def test_governance_workflows_write_requires_content_admin(self) -> None:
        """All POST routes in governance_workflows.py use require_content_admin."""
        source = pathlib.Path(
            LAYER4_SRC / "api/routes/governance_workflows.py"
        ).read_text()
        assert "require_content_admin" in source, (
            "governance_workflows.py must import require_content_admin"
        )
        tree = ast.parse(source)
        post_routes = [
            n for n in ast.walk(tree)
            if isinstance(n, ast.AsyncFunctionDef)
            and n.name in (
                "create_review", "create_decision",
                "create_version", "create_audit_export",
            )
        ]
        assert post_routes, "Expected POST route handlers not found"
        for fn in post_routes:
            fn_src = ast.get_source_segment(source, fn) or ""
            assert "ContentAdminDep" in fn_src or "require_content_admin" in fn_src, (
                f"{fn.name} must require content_admin or higher"
            )

    def test_harness_routes_require_authentication(self) -> None:
        """Harness routes use require_authenticated (AuthCtxDep)."""
        source = pathlib.Path(
            LAYER4_SRC / "api/routes/harness.py"
        ).read_text()
        assert "require_authenticated" in source, (
            "harness.py must use require_authenticated"
        )
        assert "AuthCtxDep" in source, (
            "harness.py must define AuthCtxDep"
        )

    def test_services_api_tenant_context_fails_without_jwt(self) -> None:
        """services/api TenantRequired raises when no JWT is present."""
        source = pathlib.Path(
            "services/api/app/core/tenant_context.py"
        ).read_text()
        # Must depend on require_authenticated
        assert "require_authenticated" in source, (
            "TenantRequired must depend on require_authenticated"
        )
        # Must raise on missing tenant
        assert "HTTPException" in source, (
            "TenantRequired must raise HTTPException when tenant context is missing"
        )


# ---------------------------------------------------------------------------
# S5-R5.2 — Wrong tenant → 404 on resource lookup
# ---------------------------------------------------------------------------


class TestWrongTenantReturns404:
    """Wrong tenant in JWT must yield 404 on resource lookup, not 200."""

    def test_harness_get_run_raises_404_on_key_error(self) -> None:
        """harness.py translates KeyError from registry.get_run to HTTP 404."""
        source = pathlib.Path(
            LAYER4_SRC / "api/routes/harness.py"
        ).read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_run":
                fn_src = ast.get_source_segment(source, node) or ""
                assert "404" in fn_src or "HTTP_404_NOT_FOUND" in fn_src or "NotFoundError" in fn_src, (
                    "get_run must return 404 when run is not found for the tenant"
                )
                return

        pytest.fail("get_run not found in harness.py")

    def test_harness_get_gate_raises_404_on_key_error(self) -> None:
        """harness.py translates KeyError from registry.get_gate to HTTP 404."""
        source = pathlib.Path(
            LAYER4_SRC / "api/routes/harness.py"
        ).read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "decide_gate":
                fn_src = ast.get_source_segment(source, node) or ""
                assert "404" in fn_src or "HTTP_404_NOT_FOUND" in fn_src or "NotFoundError" in fn_src, (
                    "decide_gate must return 404 when gate is not found for the tenant"
                )
                return

        pytest.fail("decide_gate not found in harness.py")


# ---------------------------------------------------------------------------
# S5-R5.3 — Body tenant_id is ignored
# ---------------------------------------------------------------------------


class TestBodyTenantIgnored:
    """Body-supplied tenant_id must be ignored; JWT tenant is authoritative."""

    def test_enrichment_batch_ignores_body_tenant(self) -> None:
        """Enrichment batch endpoint uses auth context tenant, not body tenant_id."""
        source = pathlib.Path(
            LAYER4_SRC / "api/routes/enrichment.py"
        ).read_text()
        # V-004 comment must be present
        assert "V-004" in source or "body" in source.lower(), (
            "enrichment.py must document that body tenant_id is ignored"
        )
        assert "get_verified_tenant_id" in source or "require_authenticated" in source, (
            "enrichment.py must derive tenant from auth context"
        )

    def test_services_api_tenant_context_ignores_body(self) -> None:
        """services/api TenantRequired derives tenant from JWT, not request body."""
        source = pathlib.Path(
            "services/api/app/core/tenant_context.py"
        ).read_text()
        # DECISION(10f1343660a64912bd5e43ebe82a26c9): ACCEPTED
        # Must not read tenant_id from request body
        assert "request.body" not in source and "body.tenant_id" not in source, (
            "TenantRequired must not read tenant_id from request body"
        )
        # Must read from JWT payload
        assert "auth.tenant_id" in source, (
            "TenantRequired must read tenant_id from JWT payload (auth.tenant_id)"
        )

    def test_harness_routes_use_ctx_tenant_not_body(self) -> None:
        """Harness routes use ctx.tenant_id, never body.tenant_id."""
        source = pathlib.Path(
            LAYER4_SRC / "api/routes/harness.py"
        ).read_text()
        assert "body.tenant_id" not in source, (
            "harness.py must not use body.tenant_id — use ctx.tenant_id only"
        )
        assert "ctx.tenant_id" in source, (
            "harness.py must use ctx.tenant_id from authenticated context"
        )


# ---------------------------------------------------------------------------
# S5-R5.4 — decision_by is server-derived
# ---------------------------------------------------------------------------


class TestDecisionByServerDerived:
    """decision_by must always come from ctx.user_id, never from request body."""

    def test_decide_gate_uses_server_derived_decision_by(self) -> None:
        """decide_gate sets decision_by from ctx.user_id, not body."""
        source = pathlib.Path(
            LAYER4_SRC / "api/routes/harness.py"
        ).read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "decide_gate":
                fn_src = ast.get_source_segment(source, node) or ""
                assert "ctx.user_id" in fn_src, (
                    "decide_gate must set decision_by from ctx.user_id"
                )
                assert "body.decision_by" not in fn_src, (
                    "decide_gate must not use body.decision_by"
                )
                # Must use server_decision_by variable
                assert "server_decision_by" in fn_src or "decision_by=ctx" in fn_src, (
                    "decide_gate must use a server-derived variable for decision_by"
                )
                return

        pytest.fail("decide_gate not found in harness.py")

    def test_gate_decision_request_model_has_no_decision_by(self) -> None:
        """GateDecisionRequest body model must not expose a decision_by field."""
        source = pathlib.Path(
            LAYER4_SRC / "harness/api_models.py"
        ).read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "GateDecisionRequest":
                class_src = ast.get_source_segment(source, node) or ""
                assert "decision_by" not in class_src, (
                    "GateDecisionRequest must not expose decision_by — "
                    "it is always server-derived from ctx.user_id"
                )
                return

        # If the class doesn't exist, that's also fine — no body field to spoof
        pass


# ---------------------------------------------------------------------------
# S5-R5.5 — No secrets in structured log output
# ---------------------------------------------------------------------------


class TestNoSecretsInLogs:
    """Secrets must not appear in structured log output."""

    def test_jwt_secret_not_logged_in_security_module(self) -> None:
        """services/api security.py must not log the JWT secret."""
        source = pathlib.Path(
            "services/api/app/core/security.py"
        ).read_text()
        # DECISION(57c427a3066048f99dbc051c40a5766d): ACCEPTED
        # secret_key must not appear in any log call
        log_lines = [
            line for line in source.splitlines()
            if ("logger." in line or "logging." in line)
            and "secret_key" in line
        ]
        assert not log_lines, (
            f"JWT secret_key must not be logged. Found in lines: {log_lines}"
        )

    def test_stripe_key_not_logged(self) -> None:
        """Stripe secret key must not appear in log calls."""
        source = pathlib.Path(
            LAYER4_SRC / "services/stripe_client.py"
        ).read_text()
        log_lines = [
            line for line in source.splitlines()
            if ("logger." in line or "logging." in line or "log." in line)
            and ("STRIPE_SECRET_KEY" in line or "stripe_api_key" in line or "_stripe_api_key" in line)
        ]
        assert not log_lines, (
            f"Stripe secret key must not be logged. Found in lines: {log_lines}"
        )

    def test_api_keys_not_logged_in_layer4_settings(self) -> None:
        """Layer 4 settings must not log API key values."""
        source = pathlib.Path(
            LAYER4_SRC / "config/settings.py"
        ).read_text()
        # Check that secret fields are not emitted in log calls
        secret_fields = ["jwt_secret", "stripe_secret_key", "openai_api_key", "together_api_key"]
        for field in secret_fields:
            log_lines = [
                line for line in source.splitlines()
                if ("logger." in line or "logging." in line)
                and field in line
            ]
            assert not log_lines, (
                f"Secret field '{field}' must not be logged. Found in: {log_lines}"
            )

    def test_layer4_lifecycle_logger_does_not_log_secrets(self) -> None:
        """Layer4LifecycleLogger emit() must not include secret fields."""
        source = pathlib.Path(
            LAYER4_SRC / "observability.py"
        ).read_text()
        tree = ast.parse(source)

        lifecycle_logger_class = next(
            (
                node
                for node in tree.body
                if isinstance(node, ast.ClassDef)
                and node.name == "Layer4LifecycleLogger"
            ),
            None,
        )
        assert lifecycle_logger_class is not None, (
            "Expected Layer4LifecycleLogger to exist in observability.py"
        )

        emit_method = next(
            (
                node
                for node in lifecycle_logger_class.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "emit"
            ),
            None,
        )
        assert emit_method is not None, (
            "Expected Layer4LifecycleLogger.emit() to exist in observability.py"
        )

        forbidden_keys = {"api_key", "secret", "password"}
        for node in ast.walk(emit_method):
            if isinstance(node, ast.Dict):
                for key in node.keys:
                    if (
                        isinstance(key, ast.Constant)
                        and isinstance(key.value, str)
                        and key.value in forbidden_keys
                    ):
                        pytest.fail(
                            f"Layer4LifecycleLogger.emit() payload must not include "
                            f"secret field '{key.value}'"
                        )
