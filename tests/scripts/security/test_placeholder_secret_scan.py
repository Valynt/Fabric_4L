from scripts.security.placeholder_secret_scan import scan_doc


def _secret_doc(value: str, namespace: str = "value-fabric-production") -> dict:
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": "test-secret", "namespace": namespace},
        "stringData": {"password": value},
    }


def test_production_target_forbidden_placeholder_fails() -> None:
    doc = _secret_doc("minioadmin")
    findings = scan_doc(doc, "k8s/overlays/production/rendered.yaml", allow_guarded_dev=False)
    assert any("production-forbidden placeholder value" in finding for finding in findings)


def test_local_compose_allowlist_skips_production_forbidden_marker() -> None:
    doc = _secret_doc("devpassword", namespace="value-fabric-dev")
    findings = scan_doc(doc, "docker-compose.dev.yml", allow_guarded_dev=False)
    assert not any("production-forbidden placeholder value" in finding for finding in findings)


def test_non_prod_namespace_without_production_target_does_not_trigger_production_rule() -> None:
    doc = _secret_doc("REPLACE_WITH_SECRET", namespace="value-fabric-dev")
    findings = scan_doc(doc, "k8s/base/secret.yaml", allow_guarded_dev=False)
    assert not any("production-forbidden placeholder value" in finding for finding in findings)
