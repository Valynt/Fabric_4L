from __future__ import annotations

"""C-06 active security regression tests for Layer 4 production fixes.

These tests intentionally avoid optional import skip gates. If a security-critical
module cannot be imported, the test module must fail during collection rather
than silently passing with no coverage.
"""


import inspect
import pathlib
import sys
import unittest
from types import SimpleNamespace

from fastapi.params import Depends as DependsParam
from pydantic import ValidationError

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SHARED_SRC = REPO_ROOT / "packages" / "shared" / "src"
LAYER4_PROJECT = REPO_ROOT / "services" / "layer4-agents"
LAYER4_SRC = LAYER4_PROJECT / "src"

for path in (str(SHARED_SRC), str(LAYER4_PROJECT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from layer4_agents.api.routes.billing import _get_client_ip  # noqa: E402
from layer4_agents.api.routes.billing_helpers import (
    is_stripe_webhook_ip as _is_stripe_webhook_ip,  # noqa: E402
)
from layer4_agents.api.routes.health_badges import (  # noqa: E402
    dismiss_badge,
    get_detailed_health,
    require_authenticated,
)
from layer4_agents.config.settings import Settings  # noqa: E402
from layer4_agents.metrics.prometheus_metrics import (  # noqa: E402
    _derive_tenant_tier,
    _normalize_path,
)

CORE_ROUTES_SOURCE = LAYER4_SRC / "layer4_agents" / "api" / "core_routes.py"
HEALTH_BADGES_SOURCE = LAYER4_SRC / "layer4_agents" / "api" / "routes" / "health_badges.py"
TOOLS_SOURCE = LAYER4_SRC / "layer4_agents" / "api" / "routes" / "tools.py"
NARRATIVE_SOURCE = LAYER4_SRC / "layer4_agents" / "services" / "narrative_builder_service.py"
VALUE_HYPOTHESIS_SOURCE = LAYER4_SRC / "layer4_agents" / "services" / "value_hypothesis_engine.py"
TENANT_PROVISIONING_SOURCE = LAYER4_SRC / "layer4_agents" / "services" / "tenant_provisioning.py"


class PathNormalizationSecurityTests(unittest.TestCase):
    """Protect Prometheus label cardinality from user-controlled identifiers."""

    def test_uuid_path_segments_are_normalized(self) -> None:
        normalized = _normalize_path("/v1/workflows/550e8400-e29b-41d4-a716-446655440000/status")
        self.assertEqual(normalized, "/v1/workflows/{id}/status")

    def test_numeric_path_segments_are_normalized(self) -> None:
        normalized = _normalize_path("/v1/customers/123456/invoices/987654")
        self.assertEqual(normalized, "/v1/customers/{id}/invoices/{id}")

    def test_hex_identifier_segments_are_normalized(self) -> None:
        normalized = _normalize_path("/v1/api-keys/507f1f77bcf86cd799439011")
        self.assertEqual(normalized, "/v1/api-keys/{id}")

    def test_short_static_segments_are_preserved(self) -> None:
        normalized = _normalize_path("/v1/health/detailed")
        self.assertEqual(normalized, "/v1/health/detailed")

    def test_empty_path_normalizes_to_root(self) -> None:
        self.assertEqual(_normalize_path(""), "/")

    def test_trailing_slash_is_removed(self) -> None:
        self.assertEqual(_normalize_path("/v1/health/"), "/v1/health")


class TenantTierCardinalityTests(unittest.TestCase):
    """Protect tenant labels from exposing raw tenant identifiers."""

    def test_none_tenant_maps_to_unknown(self) -> None:
        self.assertEqual(_derive_tenant_tier(None), "unknown")

    def test_tenant_ids_map_to_sha256_hash_buckets(self) -> None:
        expectations = {
            "enterprise-acme-corp": "2462",
            "pro-customer-123": "3358",
            "free-trial-user": "9525",
        }
        for tenant_id, expected in expectations.items():
            with self.subTest(tenant_id=tenant_id):
                self.assertEqual(_derive_tenant_tier(tenant_id), expected)

    def test_unclassified_tenants_are_bucketed_not_exposed(self) -> None:
        tenant_id = "customer-secret-tenant-id-12345"
        derived = _derive_tenant_tier(tenant_id)
        self.assertRegex(derived, r"^[0-9a-f]{4}$")
        self.assertNotIn("secret", derived)
        self.assertNotIn("tenant", derived)

    def test_bucket_assignment_is_deterministic(self) -> None:
        tenant_id = "customer-secret-tenant-id-12345"
        self.assertEqual(_derive_tenant_tier(tenant_id), _derive_tenant_tier(tenant_id))


class StripeWebhookIpTests(unittest.TestCase):
    """Validate defense-in-depth checks for Stripe webhook source IPs."""

    def test_known_stripe_webhook_ips_are_allowed(self) -> None:
        for ip in ("3.18.12.63", "52.15.183.38", "54.187.174.170"):
            with self.subTest(ip=ip):
                self.assertTrue(_is_stripe_webhook_ip(ip))

    def test_loopback_ips_are_allowed_for_local_development(self) -> None:
        for ip in ("127.0.0.1", "::1"):
            with self.subTest(ip=ip):
                self.assertTrue(_is_stripe_webhook_ip(ip))

    def test_arbitrary_public_ips_are_rejected(self) -> None:
        for ip in ("8.8.8.8", "1.1.1.1", "203.0.113.10"):
            with self.subTest(ip=ip):
                self.assertFalse(_is_stripe_webhook_ip(ip))

    def test_malformed_ip_is_rejected(self) -> None:
        for ip in ("not-an-ip", "999.999.999.999", ""):
            with self.subTest(ip=ip):
                self.assertFalse(_is_stripe_webhook_ip(ip))

    def test_client_ip_prefers_x_forwarded_for_origin(self) -> None:
        request = SimpleNamespace(
            headers={"X-Forwarded-For": "3.18.12.63, 10.0.0.1"},
            client=SimpleNamespace(host="10.0.0.2"),
        )
        self.assertEqual(_get_client_ip(request), "3.18.12.63")

    def test_client_ip_uses_x_real_ip_before_socket_address(self) -> None:
        request = SimpleNamespace(
            headers={"X-Real-IP": "52.15.183.38"},
            client=SimpleNamespace(host="10.0.0.2"),
        )
        self.assertEqual(_get_client_ip(request), "52.15.183.38")

    def test_client_ip_falls_back_to_socket_address(self) -> None:
        request = SimpleNamespace(headers={}, client=SimpleNamespace(host="54.187.174.169"))
        self.assertEqual(_get_client_ip(request), "54.187.174.169")


class ProductionSettingsValidationTests(unittest.TestCase):
    """Ensure production configuration fails fast when critical secrets are unsafe."""

    VALID_JWT = "j" * 40
    VALID_HMAC = "h" * 40
    VALID_DB = "postgresql://layer4:strong-unique-password@db.example.com:5432/layer4"
    VALID_CORS = "https://app.valuefabric.io"
    VALID_NEO4J_URI = "neo4j+s://example.databases.neo4j.io"
    VALID_NEO4J_PASSWORD = "strong-neo4j-password"
    VALID_LAYER_ENDPOINT = "https://layer.internal.valuefabric.local"

    def _settings(self, **overrides: object) -> Settings:
        values: dict[str, object] = {
            "environment": "production",
            "jwt_secret": self.VALID_JWT,
            "api_key_hmac_secret": self.VALID_HMAC,
            "database_url": self.VALID_DB,
            "cors_origins": self.VALID_CORS,
            "neo4j_uri": self.VALID_NEO4J_URI,
            "neo4j_password": self.VALID_NEO4J_PASSWORD,
            "layer1_api_url": self.VALID_LAYER_ENDPOINT,
            "layer2_api_url": self.VALID_LAYER_ENDPOINT,
            "layer3_api_url": self.VALID_LAYER_ENDPOINT,
            "layer5_api_url": self.VALID_LAYER_ENDPOINT,
        }
        values.update(overrides)
        return Settings(**values)

    def test_valid_production_configuration_is_accepted(self) -> None:
        settings = self._settings()
        self.assertTrue(settings.is_production)
        self.assertEqual(settings.cors_origins_list, [self.VALID_CORS])

    def test_missing_jwt_secret_fails_in_production(self) -> None:
        with self.assertRaisesRegex(ValidationError, "JWT_SECRET is required in production"):
            self._settings(jwt_secret="")

    def test_short_jwt_secret_fails_in_production(self) -> None:
        with self.assertRaisesRegex(ValidationError, "JWT_SECRET must be at least 32 characters"):
            self._settings(jwt_secret="short")

    def test_missing_api_key_hmac_secret_fails_in_production(self) -> None:
        with self.assertRaisesRegex(ValidationError, "API_KEY_HMAC_SECRET is required in production"):
            self._settings(api_key_hmac_secret="")

    def test_short_api_key_hmac_secret_fails_in_production(self) -> None:
        with self.assertRaisesRegex(ValidationError, "API_KEY_HMAC_SECRET must be at least 32 characters"):
            self._settings(api_key_hmac_secret="short")

    def test_default_database_credentials_fail_in_production(self) -> None:
        with self.assertRaisesRegex(ValidationError, "insecure default credentials"):
            self._settings(database_url="postgresql://postgres:postgres@db.example.com:5432/layer4")

    def test_missing_cors_origins_fail_in_production(self) -> None:
        with self.assertRaisesRegex(ValidationError, "CORS_ORIGINS is required in production"):
            self._settings(cors_origins="")

    def test_wildcard_cors_fails_in_production(self) -> None:
        with self.assertRaisesRegex(ValidationError, "cannot contain '\\*' in production"):
            self._settings(cors_origins="*")

    def test_origin_without_scheme_fails_in_production(self) -> None:
        with self.assertRaisesRegex(ValidationError, "must start with http:// or https://"):
            self._settings(cors_origins="app.valuefabric.io")

    def test_development_generates_nonempty_ephemeral_secrets(self) -> None:
        settings = Settings(environment="development", jwt_secret="", api_key_hmac_secret="")
        self.assertGreaterEqual(len(settings.jwt_secret), 32)
        self.assertGreaterEqual(len(settings.api_key_hmac_secret), 32)

    def test_production_rejects_http_layer_endpoint_without_mesh_mtls(self) -> None:
        with self.assertRaisesRegex(ValidationError, "must use HTTPS in production"):
            self._settings(layer1_api_url="http://layer1-ingestion.value-fabric.svc.cluster.local:8000")

    def test_production_allows_http_layer_endpoint_with_mesh_mtls(self) -> None:
        settings = self._settings(
            layer2_api_url="http://layer2-extraction.value-fabric.svc.cluster.local:8000",
            service_mesh_mtls_enabled=True,
        )
        self.assertEqual(
            settings.layer2_api_url,
            "http://layer2-extraction.value-fabric.svc.cluster.local:8000",
        )

    def test_production_rejects_in_memory_oidc_state_store_backend(self) -> None:
        with self.assertRaisesRegex(ValidationError, "OIDC state store backend must be 'redis'"):
            self._settings(oidc_state_store_backend="memory")

    def test_development_requires_explicit_insecure_http_override(self) -> None:
        with self.assertRaisesRegex(ValidationError, "ALLOW_INSECURE_SERVICE_HTTP_IN_DEVELOPMENT=true"):
            Settings(
                environment="development",
                jwt_secret="j" * 40,
                api_key_hmac_secret="h" * 40,
                allow_insecure_service_http_in_development=False,
                layer1_api_url="http://localhost:8000",
                layer2_api_url="https://layer2.local",
                layer3_api_url="https://layer3.local",
                layer5_api_url="https://layer5.local",
            )

    def test_development_allows_http_with_explicit_override(self) -> None:
        settings = Settings(
            environment="development",
            jwt_secret="j" * 40,
            api_key_hmac_secret="h" * 40,
            allow_insecure_service_http_in_development=True,
            layer1_api_url="http://localhost:8000",
            layer2_api_url="https://layer2.local",
            layer3_api_url="https://layer3.local",
            layer5_api_url="https://layer5.local",
        )
        self.assertEqual(settings.layer1_api_url, "http://localhost:8000")


class MetricsEndpointSecurityWiringTests(unittest.TestCase):
    """Verify the active metrics endpoint remains protected by access control."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = CORE_ROUTES_SOURCE.read_text(encoding="utf-8")

    def test_metrics_access_control_import_is_present(self) -> None:
        self.assertIn("from value_fabric.shared.observability.metrics_access import verify_metrics_access", self.source)
        self.assertIn("METRICS_ACCESS_AVAILABLE", self.source)

    def test_metrics_endpoint_invokes_access_verifier_before_reading_metrics(self) -> None:
        verifier_index = self.source.index("is_authorized, error_message = verify_metrics_access(request)")
        metrics_read_index = self.source.index('metrics = getattr(request.app.state, "metrics", None)')
        self.assertLess(verifier_index, metrics_read_index)

    def test_unauthorized_metrics_scrapes_return_401(self) -> None:
        self.assertIn("if not is_authorized:", self.source)
        self.assertIn("status_code=401", self.source)
        self.assertIn('content=error_message or "Unauthorized"', self.source)


class HealthEndpointAuthTests(unittest.TestCase):
    """Verify privileged health badge endpoints are not exposed anonymously."""

    def test_detailed_health_requires_authenticated_context_parameter(self) -> None:
        signature = inspect.signature(get_detailed_health)
        self.assertIn("context", signature.parameters)
        default = signature.parameters["context"].default
        self.assertIsInstance(default, DependsParam)
        self.assertIs(default.dependency, require_authenticated)

    def test_badge_dismissal_requires_authenticated_context_parameter(self) -> None:
        signature = inspect.signature(dismiss_badge)
        self.assertIn("context", signature.parameters)
        default = signature.parameters["context"].default
        self.assertIsInstance(default, DependsParam)
        self.assertIs(default.dependency, require_authenticated)

    def test_health_badges_source_has_no_security_available_fallback(self) -> None:
        source = HEALTH_BADGES_SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("SECURITY_AVAILABLE", source)
        self.assertNotIn("if SECURITY_AVAILABLE else", source)
        self.assertIn("Depends(require_authenticated)", source)


class FailClosedToolGatewayRegressionTests(unittest.TestCase):
    """Ensure C-03 fail-closed source guards remain present while C-06 runs."""

    def test_tool_gateway_raises_service_unavailable_when_gateway_unavailable(self) -> None:
        source = TOOLS_SOURCE.read_text(encoding="utf-8")
        self.assertIn("def require_tool_gateway_available()", source)
        self.assertIn("raise ServiceUnavailableError(", source)
        self.assertIn("Tool governance gateway unavailable", source)
        self.assertNotIn("lambda: None", source)


class InjectionSafeQueryConstructionTests(unittest.TestCase):
    """Regression guards for SQL/Cypher injection-safe query construction."""

    def test_narrative_builder_avoids_fstring_cypher(self) -> None:
        source = NARRATIVE_SOURCE.read_text(encoding="utf-8")
        self.assertNotIn('f"MATCH (n:Narrative)', source)
        self.assertNotIn("f'MATCH (n:Narrative)", source)
        # The WHERE clause must be assembled from controlled fragments and
        # passed as parameters, not interpolated.
        self.assertIn("$tenant_id", source)
        self.assertIn("$account_id", source)
        self.assertIn("$status", source)

    def test_value_hypothesis_engine_avoids_fstring_cypher(self) -> None:
        source = VALUE_HYPOTHESIS_SOURCE.read_text(encoding="utf-8")
        self.assertNotIn('f"MATCH (vh:ValueHypothesis)', source)
        self.assertNotIn("f'MATCH (vh:ValueHypothesis)", source)
        self.assertIn("$tenant_id", source)
        self.assertIn("$account_id", source)
        self.assertIn("$status", source)

    def test_tenant_provisioning_uses_quoted_identifier_and_validation(self) -> None:
        source = TENANT_PROVISIONING_SOURCE.read_text(encoding="utf-8")
        self.assertIn("re.match(r\"^[a-z_][a-z0-9_]*$\", schema_name)", source)
        self.assertIn('CREATE SCHEMA IF NOT EXISTS "' + "' + schema_name + '" + '"', source)
        self.assertIn('GRANT USAGE ON SCHEMA "' + "' + schema_name + '" + '" TO "' + "' + grant_role + '" + '"', source)


if __name__ == "__main__":
    unittest.main()
