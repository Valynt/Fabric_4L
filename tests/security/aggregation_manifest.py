"""Central security suite coverage map.

This module is intentionally static and side-effect free.  The tests in this
package use it to document and validate the centralized security categories
without importing or duplicating the layer-specific suites that remain in their
canonical locations.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CENTRAL_SECURITY_SUITE_FILES = {
    "test_auth_guards.py",
    "test_tenant_isolation.py",
    "test_secret_handling.py",
    "test_security_headers.py",
    "test_dependency_policy.py",
    "test_container_policy.py",
}

SECURITY_COVERAGE = {
    "auth_guards": {
        "description": "Authentication, authorization, RBAC, JWT, WebSocket auth, and bypass guardrails.",
        "central_file": "tests/security/test_auth_guards.py",
        "references": [
            "tests/security/test_auth_boundaries.py",
            "tests/security/test_auth_default_deny.py",
            "tests/security/test_auth_source_validation.py",
            "tests/security/test_jwt_config_validation.py",
            "tests/security/test_rbac.py",
            "services/api/app/tests/test_auth_enforcement.py",
            "services/layer4-agents/tests/test_fail_closed_authz_guards.py",
            "services/layer7-billing/tests/test_auth_enforcement.py",
        ],
    },
    "tenant_isolation": {
        "description": "Cross-tenant read/write prevention, tenant context propagation, and hostile tenant regressions.",
        "central_file": "tests/security/test_tenant_isolation.py",
        "references": [
            "tests/security/test_cross_layer_tenant_isolation_matrix.py",
            "tests/security/test_cross_tenant_write.py",
            "tests/security/test_graph_tenant_hostile_regression.py",
            "tests/security/test_route_tenant_propagation_static.py",
            "services/layer1-ingestion/tests/test_cross_tenant_hostile.py",
            "services/layer2-extraction/tests/test_cross_tenant_hostile.py",
            "services/layer3-knowledge/tests/test_cross_tenant_hostile.py",
            "services/layer4-agents/tests/test_cross_tenant_hostile.py",
            "services/layer5-ground-truth/tests/test_cross_tenant_hostile.py",
            "services/layer6-benchmarks/tests/test_cross_tenant_hostile.py",
        ],
    },
    "secret_handling": {
        "description": "Committed secret hygiene, production bypass guardrails, and safe secret-backed configuration.",
        "central_file": "tests/security/test_secret_handling.py",
        "references": [
            "tests/security/test_secrets_protection.py",
            "tests/security/test_production_bypass_guardrails.py",
            "tests/security/test_startup_bypass_nonzero_exit.py",
            "tests/security/test_dev_bypass.py",
            "services/layer4-agents/tests/security/test_postgres_backup_secret_fix.py",
            "scripts/ci/check_keycloak_realm_seed_security.py",
            "scripts/ci/check_manifest_secret_hygiene.py",
            "scripts/ci/check_path_env_hygiene.py",
        ],
    },
    "security_headers": {
        "description": "HTTP hardening headers, CORS posture, CSRF controls, and security middleware behavior.",
        "central_file": "tests/security/test_security_headers.py",
        "references": [
            "tests/security/test_security_headers.py",
            "tests/security/test_csrf_comprehensive.py",
            "tests/security/test_p1_14_security_middleware.py",
            "tests/security/test_shared_security_middleware.py",
            "tests/security/test_security_misconfiguration.py",
        ],
    },
    "dependency_policy": {
        "description": "Package-manager governance, supply-chain posture, lockfile policy, and dependency startup checks.",
        "central_file": "tests/security/test_dependency_policy.py",
        "references": [
            "tests/security/test_supply_chain.py",
            "tests/security/test_dockerfile_lockfile_fix.py",
            "scripts/enforce-package-manager.cjs",
            "scripts/ci/check_package_manager_policy.mjs",
            "services/layer2-extraction/tests/test_startup_dependency_verifier.py",
            "services/layer4-agents/tests/test_startup_dependency_verifier.py",
        ],
    },
    "container_policy": {
        "description": "Container, compose, deployment, and production safety policy checks.",
        "central_file": "tests/security/test_container_policy.py",
        "references": [
            "tests/security/test_h03_service_startup_validation.py",
            "tests/security/test_security_misconfiguration.py",
            "docker-compose.dev.yml",
            "docker-compose.test.yml",
            "k8s",
        ],
    },
}


def existing_references(category: str) -> list[Path]:
    """Return existing repository paths referenced by a central category."""
    return [
        REPO_ROOT / path
        for path in SECURITY_COVERAGE[category]["references"]
        if (REPO_ROOT / path).exists()
    ]
