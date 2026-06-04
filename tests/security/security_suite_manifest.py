"""Central security suite category manifest.

This module is intentionally metadata-only.  It lets the centralized
``tests/security`` suite point at the existing layer and policy tests without
copying their assertions or re-collecting them through import side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SecurityCategory:
    """Security test coverage category and its backing test modules."""

    key: str
    title: str
    description: str
    paths: tuple[str, ...]

    def resolved_paths(self) -> tuple[Path, ...]:
        """Return repository-absolute paths for every referenced test file."""
        return tuple(REPO_ROOT / path for path in self.paths)


SECURITY_CATEGORIES: tuple[SecurityCategory, ...] = (
    SecurityCategory(
        key="auth_guards",
        title="Authentication and authorization guards",
        description=(
            "JWT validation, default-deny authorization, RBAC, session hijacking, "
            "WebSocket auth, service-account validation, and dev-bypass guardrails."
        ),
        paths=(
            "tests/security/test_auth_boundaries.py",
            "tests/security/test_auth_default_deny.py",
            "tests/security/test_auth_governance.py",
            "tests/security/test_auth_source_validation.py",
            "tests/security/test_jwt_validation.py",
            "tests/security/test_jwt_config_validation.py",
            "tests/security/test_jwt_library_parity.py",
            "tests/security/test_jwt_rotation.py",
            "tests/security/test_rbac.py",
            "tests/security/test_rbac_expanded.py",
            "tests/security/test_websocket_auth.py",
            "tests/security/test_p1_13_websocket_auth.py",
            "tests/security/test_service_account_validation.py",
            "tests/security/test_dev_bypass.py",
            "services/api/app/tests/test_impersonation_security.py",
            "services/api/app/tests/test_bcrypt_security.py",
        ),
    ),
    SecurityCategory(
        key="tenant_isolation",
        title="Tenant isolation and cross-tenant boundaries",
        description=(
            "Authenticated tenant context propagation, repository filters, graph/RLS "
            "enforcement, hostile tenant journeys, and cross-layer isolation matrices."
        ),
        paths=(
            "tests/security/test_tenant_isolation.py",
            "tests/security/test_tenant_boundary_fails_closed.py",
            "tests/security/test_cross_tenant_api.py",
            "tests/security/test_cross_tenant_write.py",
            "tests/security/test_cross_layer_tenant.py",
            "tests/security/test_cross_layer_tenant_isolation_matrix.py",
            "tests/security/test_hostile_tenant_e2e_matrix.py",
            "tests/security/test_hostile_tenant_journey_contracts.py",
            "tests/security/test_harness_tenant_isolation.py",
            "tests/security/test_tenant_context_contract.py",
            "tests/security/test_tenant_mismatch.py",
            "tests/security/test_tier_aware_isolation.py",
            "tests/backend_integrated/test_tenant_isolation_security_persistence.py",
            "tests/layer1/test_layer1_security_invariants.py",
            "tests/layer2/test_layer2_security_invariants.py",
            "tests/layer3/test_layer3_security_invariants.py",
            "tests/layer4/test_layer4_security_invariants.py",
            "tests/layer6/test_layer6_security_invariants.py",
        ),
    ),
    SecurityCategory(
        key="secret_handling",
        title="Secret handling and sensitive data controls",
        description=(
            "Secret scanning, hardcoded secret prevention, API key rejection, PII "
            "encryption, audit resiliency, and sensitive-route audit coverage."
        ),
        paths=(
            "tests/security/test_secrets_protection.py",
            "tests/security/test_p0_5_api_key_rejection.py",
            "tests/security/test_pii_encryption_at_rest.py",
            "tests/security/test_hardcoded_demo_data_removal.py",
            "tests/security/test_sensitive_route_audit_coverage.py",
            "tests/security/test_audit_event_emission.py",
            "tests/security/test_audit_resilience.py",
            "tests/security/test_audit_retry_queue.py",
            "tests/security/test_tenant_audit.py",
            "tests/security/test_privileged_audit.py",
        ),
    ),
    SecurityCategory(
        key="security_headers",
        title="Security headers and browser-facing hardening",
        description=(
            "HTTP response security headers, CSRF protection, security middleware, "
            "request tracing, correlation logging, and production bypass guardrails."
        ),
        paths=(
            "tests/security/test_security_headers.py",
            "tests/security/test_security_misconfiguration.py",
            "tests/security/test_shared_security_middleware.py",
            "tests/security/test_p1_14_security_middleware.py",
            "tests/security/test_governance_middleware_resolution_order.py",
            "tests/security/test_csrf_comprehensive.py",
            "tests/security/test_request_tracing.py",
            "tests/security/test_correlation_logging_contract.py",
            "tests/security/test_trace_correlation_contract.py",
            "tests/security/test_production_bypass_guardrails.py",
        ),
    ),
    SecurityCategory(
        key="dependency_policy",
        title="Dependency and supply-chain policy",
        description=(
            "pnpm-only/package-manager policy, lockfile integrity, vulnerable package "
            "posture, SBOM structure, and workflow/dependency governance checks."
        ),
        paths=(
            "tests/security/test_supply_chain.py",
            "tests/security/test_dockerfile_lockfile_fix.py",
            "tests/security/test_frontend_coverage_thresholds.py",
            "tests/security/test_mandatory_security_regression_gate.py",
            "tests/ci/test_mandatory_security_regression_gate.py",
            "scripts/ci/check_package_manager_policy.mjs",
            "scripts/ci/validate_dependabot_coverage.py",
        ),
    ),
    SecurityCategory(
        key="container_policy",
        title="Container and deployment policy",
        description=(
            "Dockerfile reproducibility, Kubernetes/container hardening policies, "
            "startup validation, and production-readiness container controls."
        ),
        paths=(
            "tests/security/test_dockerfile_lockfile_fix.py",
            "tests/security/test_h03_service_startup_validation.py",
            "tests/security/test_startup_bypass_nonzero_exit.py",
            "tests/security/test_security_misconfiguration.py",
            "tests/k8s/test_security_policies.py",
            "k8s/policy/security-hardening.rego",
            ".github/workflows/security-gates.yml",
        ),
    ),
)


def category_by_key(key: str) -> SecurityCategory:
    """Return a category by stable key."""
    for category in SECURITY_CATEGORIES:
        if category.key == key:
            return category
    raise KeyError(key)


def python_test_paths(category: SecurityCategory) -> tuple[str, ...]:
    """Return referenced pytest modules for a category."""
    return tuple(path for path in category.paths if path.endswith(".py") and "/test_" in path)


def iter_missing_paths(category: SecurityCategory) -> Iterable[str]:
    """Yield manifest paths that no longer exist in the repository."""
    for path in category.paths:
        if not (REPO_ROOT / path).exists():
            yield path
