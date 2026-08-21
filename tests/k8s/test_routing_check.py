"""Unit tests for `scripts/ci/k8s_routing_check.py`.

These tests exercise the gate's behaviour against minimal synthetic renders so
that future changes to the gate cannot silently weaken its guarantees:

  - Mutual exclusivity of routing kinds per axis.
  - Sentinel-survival detection (`__HOST__`, `__API_HOST__`).
  - Per-listener bucket-swap detection (an `https-api` listener that carries
    the frontend host must fail).
  - Hostname mismatch against `routing-host` ConfigMap.
  - Missing `routing-host` ConfigMap.
  - Backend Service-existence.
  - Routing stack importing `../../base`.

The gate is invoked as a subprocess so we cover the real CLI surface; this
matches the way CI runs it.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPT_REL = Path("scripts/ci/k8s_routing_check.py")


def _ok_routing_dir(tmp_path: Path) -> Path:
    """Routing dir whose stacks do not import base. Always rule-compliant."""
    routing = tmp_path / "routing"
    (routing / "nginx").mkdir(parents=True)
    (routing / "nginx" / "kustomization.yaml").write_text(
        "apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\nresources: []\n",
        encoding="utf-8",
    )
    return routing


def _bad_routing_dir(tmp_path: Path) -> Path:
    """Routing dir with a stack that wrongly imports base."""
    routing = tmp_path / "routing-bad"
    (routing / "nginx").mkdir(parents=True)
    (routing / "nginx" / "kustomization.yaml").write_text(
        "apiVersion: kustomize.config.k8s.io/v1beta1\n"
        "kind: Kustomization\n"
        "resources:\n"
        "  - ../../base\n",
        encoding="utf-8",
    )
    return routing


def _run_gate(
    repo_root: Path,
    rendered_dir: Path,
    routing_dir: Path,
    deployments: list[str],
) -> subprocess.CompletedProcess:
    args = [
        sys.executable,
        str(repo_root / SCRIPT_REL),
        "--rendered-dir",
        str(rendered_dir),
        "--routing-dir",
        str(routing_dir),
    ]
    for dep in deployments:
        args.extend(["--deployment", dep])
    return subprocess.run(args, capture_output=True, text=True, cwd=str(repo_root))


# A minimal valid nginx-axis render. Two Services + ConfigMap +
# matching frontend/layer-apis Ingresses. No sentinels, no forbidden kinds.
# The layer-apis Ingress routes to api-gateway (the gateway is the only
# public API entry point; see scripts/ci/k8s_routing_check.py).
VALID_NGINX_RENDER = textwrap.dedent(
    """\
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: routing-host
      namespace: value-fabric
    data:
      host: app.example.com
      apiHost: api.example.com
    ---
    apiVersion: v1
    kind: Service
    metadata: {name: frontend, namespace: value-fabric}
    spec: {selector: {app: frontend}, ports: [{port: 3000}]}
    ---
    apiVersion: v1
    kind: Service
    metadata: {name: api-gateway, namespace: value-fabric}
    spec: {selector: {app: api-gateway}, ports: [{port: 8000}]}
    ---
    apiVersion: v1
    kind: Service
    metadata: {name: layer1-ingestion, namespace: value-fabric}
    spec: {selector: {app: layer1}, ports: [{port: 8000}]}
    ---
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: frontend
      namespace: value-fabric
      annotations:
        nginx.ingress.kubernetes.io/enable-cors: "true"
        nginx.ingress.kubernetes.io/auth-url: "http://auth.value-fabric.svc.cluster.local/auth"
        nginx.ingress.kubernetes.io/auth-signin: "https://auth.example.com/signin"
        nginx.ingress.kubernetes.io/auth-response-headers: "Authorization"
        nginx.ingress.kubernetes.io/limit-rps: "10"
        nginx.ingress.kubernetes.io/limit-rpm: "600"
        nginx.ingress.kubernetes.io/limit-connections: "20"
        nginx.ingress.kubernetes.io/limit-burst-multiplier: "2"
    spec:
      rules:
        - host: app.example.com
          http:
            paths:
              - path: /
                pathType: Prefix
                backend:
                  service: {name: frontend, port: {number: 3000}}
      tls:
        - hosts: [app.example.com]
          secretName: frontend-tls
    ---
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: layer-apis
      namespace: value-fabric
      annotations:
        nginx.ingress.kubernetes.io/enable-cors: "true"
        nginx.ingress.kubernetes.io/auth-url: "http://auth.value-fabric.svc.cluster.local/auth"
        nginx.ingress.kubernetes.io/auth-signin: "https://auth.example.com/signin"
        nginx.ingress.kubernetes.io/auth-response-headers: "Authorization"
        nginx.ingress.kubernetes.io/limit-rps: "10"
        nginx.ingress.kubernetes.io/limit-rpm: "600"
        nginx.ingress.kubernetes.io/limit-connections: "20"
        nginx.ingress.kubernetes.io/limit-burst-multiplier: "2"
    spec:
      rules:
        - host: api.example.com
          http:
            paths:
              - path: /
                pathType: Prefix
                backend:
                  service: {name: api-gateway, port: {number: 8000}}
      tls:
        - hosts: [api.example.com]
          secretName: layer-apis-tls
    """
)


# Gateway-API render where the `https-api` listener wrongly carries the
# frontend host. The bucket-swap bug must be caught.
SWAPPED_GATEWAY_RENDER = textwrap.dedent(
    """\
    apiVersion: v1
    kind: ConfigMap
    metadata: {name: routing-host, namespace: value-fabric}
    data: {host: app.example.com, apiHost: api.example.com}
    ---
    apiVersion: v1
    kind: Service
    metadata: {name: frontend, namespace: value-fabric}
    spec: {selector: {app: frontend}, ports: [{port: 3000}]}
    ---
    apiVersion: v1
    kind: Service
    metadata: {name: layer1-ingestion, namespace: value-fabric}
    spec: {selector: {app: layer1}, ports: [{port: 8000}]}
    ---
    apiVersion: v1
    kind: Service
    metadata: {name: api-gateway, namespace: value-fabric}
    spec: {selector: {app: api-gateway}, ports: [{port: 8000}]}
    ---
    apiVersion: gateway.networking.k8s.io/v1
    kind: Gateway
    metadata: {name: value-fabric-gateway, namespace: value-fabric}
    spec:
      gatewayClassName: envoy
      listeners:
        - name: https-frontend
          protocol: HTTPS
          port: 443
          hostname: app.example.com
        - name: https-api
          protocol: HTTPS
          port: 443
          hostname: app.example.com   # BUG: should be api.example.com
    ---
    apiVersion: gateway.networking.k8s.io/v1
    kind: HTTPRoute
    metadata: {name: frontend, namespace: value-fabric}
    spec:
      hostnames: [app.example.com]
      rules:
        - backendRefs: [{name: frontend, port: 3000}]
    ---
    apiVersion: gateway.networking.k8s.io/v1
    kind: HTTPRoute
    metadata: {name: layer-apis, namespace: value-fabric}
    spec:
      hostnames: [api.example.com]
      rules:
        - backendRefs: [{name: api-gateway, port: 8000}]
    """
)


@pytest.fixture
def repo_root(request: pytest.FixtureRequest) -> Path:
    # tests/k8s/ -> repo root is two levels up
    return Path(request.fspath).parent.parent.parent


def test_gate_accepts_valid_nginx_render(tmp_path: Path, repo_root: Path) -> None:
    """A clean nginx-axis render passes all five gates."""
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    (rendered / "dev-nginx.yaml").write_text(VALID_NGINX_RENDER, encoding="utf-8")
    result = _run_gate(repo_root, rendered, _ok_routing_dir(tmp_path), ["dev-nginx:nginx"])
    assert result.returncode == 0, result.stderr + result.stdout


def test_gate_detects_sentinel_survival(tmp_path: Path, repo_root: Path) -> None:
    """A sentinel left in the rendered output fails the gate."""
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    bad = VALID_NGINX_RENDER.replace("app.example.com", "__HOST__", 1)
    (rendered / "dev-nginx.yaml").write_text(bad, encoding="utf-8")
    result = _run_gate(repo_root, rendered, _ok_routing_dir(tmp_path), ["dev-nginx:nginx"])
    assert result.returncode == 1
    assert "__HOST__" in result.stderr


def test_gate_detects_forbidden_kind_for_axis(tmp_path: Path, repo_root: Path) -> None:
    """A Gateway API resource leaking into an nginx-axis render fails mutex."""
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    leaky = VALID_NGINX_RENDER + textwrap.dedent(
        """\
        ---
        apiVersion: gateway.networking.k8s.io/v1
        kind: HTTPRoute
        metadata: {name: leaked, namespace: value-fabric}
        spec:
          hostnames: [app.example.com]
          rules:
            - backendRefs: [{name: frontend, port: 3000}]
        """
    )
    (rendered / "dev-nginx.yaml").write_text(leaky, encoding="utf-8")
    result = _run_gate(repo_root, rendered, _ok_routing_dir(tmp_path), ["dev-nginx:nginx"])
    assert result.returncode == 1
    assert "forbidden routing resource" in result.stderr
    assert "HTTPRoute" in result.stderr


def test_gate_detects_hostname_mismatch(tmp_path: Path, repo_root: Path) -> None:
    """A host that is neither `host` nor `apiHost` fails consistency."""
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    bad = VALID_NGINX_RENDER.replace("- host: app.example.com", "- host: rogue.example.com")
    (rendered / "dev-nginx.yaml").write_text(bad, encoding="utf-8")
    result = _run_gate(repo_root, rendered, _ok_routing_dir(tmp_path), ["dev-nginx:nginx"])
    assert result.returncode == 1
    assert "rogue.example.com" in result.stderr


def test_gate_detects_listener_bucket_swap(tmp_path: Path, repo_root: Path) -> None:
    """An `https-api` listener that carries the frontend host must fail.

    This is the regression test for the P1 weakness identified during
    refinement: previously the gate dumped every listener host into both
    buckets, so a swap was invisible. After the refactor, listener.name
    classifies each host into its expected bucket and the swap is caught.
    """
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    (rendered / "prod-gateway-api.yaml").write_text(SWAPPED_GATEWAY_RENDER, encoding="utf-8")
    result = _run_gate(
        repo_root, rendered, _ok_routing_dir(tmp_path), ["prod-gateway-api:gateway-api"]
    )
    assert result.returncode == 1, result.stdout
    # The error mentions the wrong bucket (api) and the offending host.
    assert "bucket=api" in result.stderr
    assert "app.example.com" in result.stderr


def test_gate_detects_missing_routing_host_configmap(
    tmp_path: Path, repo_root: Path
) -> None:
    """A render that omits the routing-host ConfigMap fails."""
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    no_cm = "\n".join(
        block
        for block in VALID_NGINX_RENDER.split("---")
        if "kind: ConfigMap" not in block
    )
    (rendered / "dev-nginx.yaml").write_text(no_cm, encoding="utf-8")
    result = _run_gate(repo_root, rendered, _ok_routing_dir(tmp_path), ["dev-nginx:nginx"])
    assert result.returncode == 1
    assert "missing 'routing-host' ConfigMap" in result.stderr


def test_gate_detects_gateway_bypass_on_layer_apis_ingress(
    tmp_path: Path, repo_root: Path
) -> None:
    """A layer-apis Ingress routing directly to a layer Service must fail.

    This is the regression test for the production ingress bypass: the
    `layer-apis` Ingress must route to `api-gateway`, never directly to a
    layer Service. Routing to a layer bypasses gateway auth, tenant
    resolution, rate limiting, and audit logging.
    """
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    bad = VALID_NGINX_RENDER.replace(
        "service: {name: api-gateway, port: {number: 8000}}",
        "service: {name: layer1-ingestion, port: {number: 8000}}",
    )
    (rendered / "dev-nginx.yaml").write_text(bad, encoding="utf-8")
    result = _run_gate(repo_root, rendered, _ok_routing_dir(tmp_path), ["dev-nginx:nginx"])
    assert result.returncode == 1
    assert "must route through" in result.stderr
    assert "api-gateway" in result.stderr


def test_gate_detects_bypass_path_prefix_on_any_ingress(
    tmp_path: Path, repo_root: Path
) -> None:
    """Any Ingress routing a /layerN path to a non-gateway Service must fail.

    Catches a bypass even when the Ingress is not named `layer-apis` (e.g.
    a stray Ingress exposing /layer4 directly to layer4-agents).
    """
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    bad = VALID_NGINX_RENDER + textwrap.dedent(
        """\
        ---
        apiVersion: networking.k8s.io/v1
        kind: Ingress
        metadata: {name: rogue-bypass, namespace: value-fabric}
        spec:
          rules:
            - host: api.example.com
              http:
                paths:
                  - path: /layer4
                    pathType: Prefix
                    backend:
                      service: {name: layer4-agents, port: {number: 8000}}
        """
    )
    (rendered / "dev-nginx.yaml").write_text(bad, encoding="utf-8")
    result = _run_gate(repo_root, rendered, _ok_routing_dir(tmp_path), ["dev-nginx:nginx"])
    assert result.returncode == 1
    assert "bypass path" in result.stderr
    assert "/layer4" in result.stderr


def test_gate_detects_unknown_backend_service(tmp_path: Path, repo_root: Path) -> None:
    """A backend Service ref that does not exist in the render fails."""
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    bad = VALID_NGINX_RENDER.replace(
        "service: {name: api-gateway, port: {number: 8000}}",
        "service: {name: nonexistent-svc, port: {number: 8000}}",
    )
    (rendered / "dev-nginx.yaml").write_text(bad, encoding="utf-8")
    result = _run_gate(repo_root, rendered, _ok_routing_dir(tmp_path), ["dev-nginx:nginx"])
    assert result.returncode == 1
    assert "nonexistent-svc" in result.stderr


def test_gate_detects_routing_stack_importing_base(
    tmp_path: Path, repo_root: Path
) -> None:
    """Routing stacks must not import `../../base`."""
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    (rendered / "dev-nginx.yaml").write_text(VALID_NGINX_RENDER, encoding="utf-8")
    result = _run_gate(repo_root, rendered, _bad_routing_dir(tmp_path), ["dev-nginx:nginx"])
    assert result.returncode == 1
    assert "must not import base" in result.stderr


def test_gate_tolerates_comments_about_base(tmp_path: Path, repo_root: Path) -> None:
    """A comment mentioning `../../base` does not trip the base-import rule.

    Regression test: an earlier implementation grepped raw text and tripped
    on documentation comments. The current implementation parses YAML.
    """
    routing = tmp_path / "routing-comment"
    (routing / "nginx").mkdir(parents=True)
    (routing / "nginx" / "kustomization.yaml").write_text(
        "# Routing stacks MUST NOT import ../../base.\n"
        "apiVersion: kustomize.config.k8s.io/v1beta1\n"
        "kind: Kustomization\n"
        "resources: []\n",
        encoding="utf-8",
    )
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    (rendered / "dev-nginx.yaml").write_text(VALID_NGINX_RENDER, encoding="utf-8")
    result = _run_gate(repo_root, rendered, routing, ["dev-nginx:nginx"])
    assert result.returncode == 0, result.stderr + result.stdout


def test_gate_detects_missing_deployment_security_context(tmp_path: Path, repo_root: Path) -> None:
    """Rendered deployment bundles fail when container hardening is missing."""
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    insecure = VALID_NGINX_RENDER + textwrap.dedent(
        """\
        ---
        apiVersion: apps/v1
        kind: Deployment
        metadata: {name: oauth2-proxy, namespace: value-fabric}
        spec:
          selector: {matchLabels: {app: oauth2-proxy}}
          template:
            metadata: {labels: {app: oauth2-proxy}}
            spec:
              containers:
                - name: oauth2-proxy
                  image: quay.io/oauth2-proxy/oauth2-proxy:v7.6.0
        """
    )
    (rendered / "dev-nginx.yaml").write_text(insecure, encoding="utf-8")
    result = _run_gate(repo_root, rendered, _ok_routing_dir(tmp_path), ["dev-nginx:nginx"])
    assert result.returncode == 1
    assert "runAsNonRoot must be true" in result.stderr
