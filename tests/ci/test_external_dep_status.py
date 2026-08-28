from pathlib import Path

from scripts.ci.external_dep_status import (
    classify_probe_result,
    load_and_validate_registry,
    verify_hostname_allowed,
)


def test_classify_up_when_status_matches_and_well_formed():
    assert classify_probe_result(200, ok=True, well_formed=True,
                                 expected_status=200, configured_down_statuses={503}) == "up"


def test_classify_down_only_on_well_formed_unambiguous_status():
    # 503 is an explicit configured 'down' status AND the body was well-formed
    assert classify_probe_result(503, ok=True, well_formed=True,
                                 expected_status=200, configured_down_statuses={503}) == "down"


def test_timeout_is_unknown_not_down():
    # ok=False (probe raised timeout/connection error) => not safely down
    assert classify_probe_result(None, ok=False, well_formed=False,
                                 expected_status=200, configured_down_statuses={503}) == "unknown"


def test_malformed_response_is_unknown_not_down():
    assert classify_probe_result(503, ok=True, well_formed=False,
                                 expected_status=200, configured_down_statuses={503}) == "unknown"


def test_unexpected_status_is_unknown():
    assert classify_probe_result(418, ok=True, well_formed=True,
                                 expected_status=200, configured_down_statuses={503}) == "unknown"


def test_required_coverage_forbidden_on_third_party(tmp_path):
    reg = tmp_path / "reg.yaml"
    reg.write_text(
        """
services:
  - id: example-com
    service: example.com
    classification: third_party
    consuming_jobs: [integration-xl]
    coverage: required
    probe: {url: https://example.com/status, method: GET, expected_status: 200}
    probe_timeout_seconds: 5
    retry_policy: {max_attempts: 2, backoff_seconds: 1}
    failure_owner: team-platform
    hostname_allowlist: [example.com]
""",
        encoding="utf-8",
    )
    errors = load_and_validate_registry(reg)
    assert any("required" in e and "third_party" in e for e in errors)


def test_hostname_allowlist_enforced(tmp_path):
    reg = tmp_path / "reg.yaml"
    reg.write_text(
        """
services:
  - id: ghcr
    service: registry
    classification: controlled
    consuming_jobs: [build-images]
    coverage: informational
    probe: {url: https://ghcr.io/v2/, method: GET, expected_status: 200, down_statuses: [503]}
    probe_timeout_seconds: 5
    retry_policy: {max_attempts: 2, backoff_seconds: 1}
    failure_owner: team-platform
    hostname_allowlist: [ghcr.io]
""",
        encoding="utf-8",
    )
    assert load_and_validate_registry(reg) == []
    assert verify_hostname_allowed("https://ghcr.io/v2/", ["ghcr.io"])
    assert not verify_hostname_allowed("https://evil.example/x", ["ghcr.io"])
