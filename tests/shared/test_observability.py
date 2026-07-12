"""Unit tests for shared.observability helpers.

Covers:
  - PathNormalizer cardinality controls (UUID, hash, numeric, depth cap, known-route mapping)
  - is_internal_ip RFC1918/loopback recognition
  - verify_metrics_access auth flow (token, header, internal IP, dev bypass, deny)
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from value_fabric.shared.observability import (
    PathNormalizer,
    is_internal_ip,
    verify_metrics_access,
)

# ---------------------------------------------------------------------------
# PathNormalizer
# ---------------------------------------------------------------------------


@pytest.fixture
def normalizer() -> PathNormalizer:
    return PathNormalizer(
        known_routes={
            "/api/v1/truths/{truth_id}": "/api/v1/truths/{id}",
            "/health": "/health",
            "/": "/",
        },
        max_segments=6,
    )


class TestPathNormalizer:
    def test_root_path_returns_root(self, normalizer: PathNormalizer) -> None:
        assert normalizer.normalize("/") == "/"
        assert normalizer.normalize("") == "/"

    def test_known_route_exact_match(self, normalizer: PathNormalizer) -> None:
        assert normalizer.normalize("/health") == "/health"
        assert normalizer.normalize("/health/") == "/health"  # trailing slash stripped

    def test_known_route_template_lookup(self, normalizer: PathNormalizer) -> None:
        # Literal-template key gets mapped to canonical {id} form
        result = normalizer.normalize("/api/v1/truths/{truth_id}")
        assert result == "/api/v1/truths/{id}"

    def test_uuid_collapsed_to_id(self, normalizer: PathNormalizer) -> None:
        path = "/api/v1/truths/3fa85f64-5717-4562-b3fc-2c963f66afa6/validate"
        assert normalizer.normalize(path) == "/api/v1/truths/{id}/validate"

    def test_numeric_segment_collapsed_to_id(self, normalizer: PathNormalizer) -> None:
        assert normalizer.normalize("/users/12345/profile") == "/users/{id}/profile"

    def test_api_v1_segment_preserved(self, normalizer: PathNormalizer) -> None:
        # The literal "v1" must not be collapsed to {id}
        assert normalizer.normalize("/api/v1/things") == "/api/v1/things"

    def test_long_hex_hash_collapsed(self, normalizer: PathNormalizer) -> None:
        sha = "a" * 64
        assert normalizer.normalize(f"/blobs/{sha}") == "/blobs/{hash}"

    def test_depth_capped_with_truncation_marker(self, normalizer: PathNormalizer) -> None:
        path = "/a/b/c/d/e/f/g/h"
        result = normalizer.normalize(path)
        assert result.endswith("/{...}")
        # 6 segments retained
        assert result.count("/") == 7  # leading slash + 6 segments + truncation segment

    def test_query_strings_and_fragments_are_removed_from_metric_labels(self, normalizer: PathNormalizer) -> None:
        result = normalizer.normalize(
            "/api/v1/accounts/12345/documents/3fa85f64-5717-4562-b3fc-2c963f66afa6?tenant=acme&token=secret#download"
        )
        assert result == "/api/v1/accounts/{id}/documents/{id}"
        assert "secret" not in result
        assert "?" not in result
        assert "#" not in result

    def test_no_known_routes_still_works(self) -> None:
        n = PathNormalizer()
        uuid = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
        assert n.normalize(f"/x/{uuid}") == "/x/{id}"


# ---------------------------------------------------------------------------
# is_internal_ip
# ---------------------------------------------------------------------------


class TestIsInternalIp:
    @pytest.mark.parametrize(
        "ip",
        [
            "10.0.0.1",
            "10.255.255.255",
            "172.16.0.1",
            "172.31.255.255",
            "192.168.1.1",
            "127.0.0.1",
            "::1",
            "localhost",
            "::ffff:10.0.0.1",
        ],
    )
    def test_private_addresses(self, ip: str) -> None:
        assert is_internal_ip(ip) is True

    @pytest.mark.parametrize(
        "ip",
        [
            "8.8.8.8",
            "172.15.0.1",  # just below the 172.16-31 range
            "172.32.0.1",  # just above
            "192.169.0.1",
            "203.0.113.5",
            "",
        ],
    )
    def test_public_addresses(self, ip: str) -> None:
        assert is_internal_ip(ip) is False

    def test_malformed_172_ip_does_not_crash(self) -> None:
        assert is_internal_ip("172.notanumber.0.1") is False


# ---------------------------------------------------------------------------
# verify_metrics_access
# ---------------------------------------------------------------------------


def _make_request(
    headers: dict[str, str] | None = None,
    client_host: str | None = None,
) -> SimpleNamespace:
    """Construct a minimal Request-like object for verify_metrics_access."""
    return SimpleNamespace(
        headers=headers or {},
        client=SimpleNamespace(host=client_host) if client_host else None,
    )


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear env vars that affect verify_metrics_access between tests."""
    for key in (
        "METRICS_INTERNAL_SCRAPE_TOKEN",
        "ENVIRONMENT",
        "ALLOW_INSECURE_DEV_AUTH_BYPASS",
        "APP_ENV",
        "NODE_ENV",
    ):
        monkeypatch.delenv(key, raising=False)


class TestVerifyMetricsAccess:
    def test_bearer_token_match_grants_access(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("METRICS_INTERNAL_SCRAPE_TOKEN", "secret-token")
        req = _make_request(headers={"Authorization": "Bearer secret-token"})
        assert verify_metrics_access(req) is True

    def test_bearer_token_mismatch_denies(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("METRICS_INTERNAL_SCRAPE_TOKEN", "secret-token")
        req = _make_request(headers={"Authorization": "Bearer wrong"})
        assert verify_metrics_access(req) is False

    def test_custom_scrape_token_header_match(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("METRICS_INTERNAL_SCRAPE_TOKEN", "secret-token")
        req = _make_request(headers={"X-Prometheus-Scrape-Token": "secret-token"})
        assert verify_metrics_access(req) is True

    def test_token_headers_are_case_insensitive_for_plain_mapping_adapters(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("METRICS_INTERNAL_SCRAPE_TOKEN", "secret-token")
        assert verify_metrics_access(_make_request(headers={"authorization": "Bearer secret-token"})) is True
        assert verify_metrics_access(_make_request(headers={"x-prometheus-scrape-token": "secret-token"})) is True

    def test_internal_network_grants_access_without_token(self) -> None:
        req = _make_request(client_host="10.0.0.5")
        assert verify_metrics_access(req) is True

    def test_public_ip_without_token_denied(self) -> None:
        req = _make_request(client_host="8.8.8.8")
        assert verify_metrics_access(req) is False

    def test_dev_bypass_grants_access(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true")
        req = _make_request(client_host="8.8.8.8")
        assert verify_metrics_access(req) is True

    def test_dev_bypass_emits_warning(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true")

        with caplog.at_level("WARNING"):
            assert verify_metrics_access(_make_request(client_host="8.8.8.8")) is True

        assert any(
            record.message == "metrics_dev_bypass_enabled"
            and getattr(record, "flag", None) == "ALLOW_INSECURE_DEV_AUTH_BYPASS"
            for record in caplog.records
        )

    def test_dev_bypass_disabled_in_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true")
        req = _make_request(client_host="8.8.8.8")
        assert verify_metrics_access(req) is False

    @pytest.mark.parametrize("env_var,env_value", [("APP_ENV", "production"), ("NODE_ENV", "staging")])
    def test_dev_bypass_disabled_in_production_like_runtime_aliases(
        self, monkeypatch: pytest.MonkeyPatch, env_var: str, env_value: str
    ) -> None:
        monkeypatch.setenv(env_var, env_value)
        monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true")
        req = _make_request(client_host="8.8.8.8")
        assert verify_metrics_access(req) is False

    def test_production_like_alias_wins_over_development_when_both_are_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true")
        req = _make_request(client_host="8.8.8.8")
        assert verify_metrics_access(req) is False

    def test_no_client_no_token_no_bypass_denied(self) -> None:
        req = _make_request()
        assert verify_metrics_access(req) is False
