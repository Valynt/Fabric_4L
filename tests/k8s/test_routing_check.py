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


# Minimal valid same-origin nginx render. API and frontend are separate
# same-host Ingresses so the API-only rewrite cannot affect SPA routes.
VALID_NGINX_RENDER = textwrap.dedent(
    """\
    apiVersion: v1
    kind: ConfigMap
    metadata: {name: routing-host, namespace: value-fabric}
    data: {host: app.example.com}
    ---
    apiVersion: v1
    kind: Service
    metadata: {name: frontend, namespace: value-fabric}
    spec: {type: ClusterIP, selector: {app: frontend}, ports: [{port: 3000}]}
    ---
    apiVersion: v1
    kind: Service
    metadata: {name: api-gateway, namespace: value-fabric}
    spec: {type: ClusterIP, selector: {app: api-gateway}, ports: [{port: 8000}]}
    ---
    apiVersion: v1
    kind: Service
    metadata: {name: layer1-ingestion, namespace: value-fabric}
    spec: {type: ClusterIP, selector: {app: layer1-ingestion}, ports: [{port: 8000}]}
    ---
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: frontend
      namespace: value-fabric
      annotations:
        nginx.ingress.kubernetes.io/enable-cors: "false"
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
          secretName: application-tls
    ---
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: application-api
      namespace: value-fabric
      annotations:
        nginx.ingress.kubernetes.io/use-regex: "true"
        nginx.ingress.kubernetes.io/rewrite-target: /v1/$2
        nginx.ingress.kubernetes.io/enable-cors: "false"
        nginx.ingress.kubernetes.io/auth-url: "http://auth.value-fabric.svc.cluster.local/auth"
        nginx.ingress.kubernetes.io/auth-signin: "https://app.example.com/signin"
        nginx.ingress.kubernetes.io/auth-response-headers: "Authorization"
        nginx.ingress.kubernetes.io/limit-rps: "20"
        nginx.ingress.kubernetes.io/limit-rpm: "200"
        nginx.ingress.kubernetes.io/limit-connections: "10"
        nginx.ingress.kubernetes.io/limit-burst-multiplier: "5"
        nginx.ingress.kubernetes.io/proxy-read-timeout: "120"
        nginx.ingress.kubernetes.io/proxy-send-timeout: "120"
        nginx.ingress.kubernetes.io/configuration-snippet: add_header X-Content-Type-Options nosniff;
    spec:
      rules:
        - host: app.example.com
          http:
            paths:
              - path: /api/v1(/|$)(.*)
                pathType: ImplementationSpecific
                backend:
                  service: {name: api-gateway, port: {number: 8000}}
      tls:
        - hosts: [app.example.com]
          secretName: application-tls
    """
)


VALID_GATEWAY_RENDER = textwrap.dedent(
    """\
    apiVersion: v1
    kind: ConfigMap
    metadata: {name: routing-host, namespace: value-fabric}
    data: {host: app.example.com}
    ---
    apiVersion: v1
    kind: Service
    metadata: {name: frontend, namespace: value-fabric}
    spec: {type: ClusterIP, ports: [{port: 3000}]}
    ---
    apiVersion: v1
    kind: Service
    metadata: {name: api-gateway, namespace: value-fabric}
    spec: {type: ClusterIP, ports: [{port: 8000}]}
    ---
    apiVersion: v1
    kind: Service
    metadata: {name: layer1-ingestion, namespace: value-fabric}
    spec: {type: ClusterIP, ports: [{port: 8000}]}
    ---
    apiVersion: gateway.networking.k8s.io/v1
    kind: Gateway
    metadata: {name: value-fabric-gateway, namespace: value-fabric}
    spec:
      gatewayClassName: envoy-gateway
      listeners:
        - name: https-application
          protocol: HTTPS
          port: 443
          hostname: app.example.com
    ---
    apiVersion: gateway.networking.k8s.io/v1
    kind: HTTPRoute
    metadata: {name: application, namespace: value-fabric}
    spec:
      hostnames: [app.example.com]
      rules:
        - matches: [{path: {type: PathPrefix, value: /api/v1}}]
          filters:
            - type: URLRewrite
              urlRewrite: {path: {type: ReplacePrefixMatch, replacePrefixMatch: /v1}}
          backendRefs: [{name: api-gateway, port: 8000}]
        - matches: [{path: {type: PathPrefix, value: /}}]
          backendRefs: [{name: frontend, port: 3000}]
    """
)

VALID_ISTIO_RENDER = textwrap.dedent(
    """\
    apiVersion: v1
    kind: ConfigMap
    metadata: {name: routing-host, namespace: value-fabric}
    data: {host: app.example.com}
    ---
    apiVersion: v1
    kind: Service
    metadata: {name: frontend, namespace: value-fabric}
    spec: {type: ClusterIP, ports: [{port: 3000}]}
    ---
    apiVersion: v1
    kind: Service
    metadata: {name: api-gateway, namespace: value-fabric}
    spec: {type: ClusterIP, ports: [{port: 8000}]}
    ---
    apiVersion: v1
    kind: Service
    metadata: {name: layer1-ingestion, namespace: value-fabric}
    spec: {type: ClusterIP, ports: [{port: 8000}]}
    ---
    apiVersion: networking.istio.io/v1
    kind: Gateway
    metadata: {name: value-fabric-gateway, namespace: value-fabric}
    spec:
      selector: {istio: ingressgateway}
      servers:
        - port: {number: 443, name: https-application, protocol: HTTPS}
          hosts: [app.example.com]
    ---
    apiVersion: networking.istio.io/v1
    kind: VirtualService
    metadata: {name: application, namespace: value-fabric}
    spec:
      hosts: [app.example.com]
      gateways: [value-fabric-gateway]
      http:
        - match: [{uri: {prefix: /api/v1}}]
          rewrite: {uri: /v1}
          route: [{destination: {host: api-gateway, port: {number: 8000}}}]
        - match: [{uri: {prefix: /}}]
          route: [{destination: {host: frontend, port: {number: 3000}}}]
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
    result = _run_gate(
        repo_root, rendered, _ok_routing_dir(tmp_path), ["dev-nginx:nginx"]
    )
    assert result.returncode == 0, result.stderr + result.stdout


def test_gate_detects_sentinel_survival(tmp_path: Path, repo_root: Path) -> None:
    """A sentinel left in the rendered output fails the gate."""
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    bad = VALID_NGINX_RENDER.replace("app.example.com", "__HOST__", 1)
    (rendered / "dev-nginx.yaml").write_text(bad, encoding="utf-8")
    result = _run_gate(
        repo_root, rendered, _ok_routing_dir(tmp_path), ["dev-nginx:nginx"]
    )
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
    result = _run_gate(
        repo_root, rendered, _ok_routing_dir(tmp_path), ["dev-nginx:nginx"]
    )
    assert result.returncode == 1
    assert "forbidden routing resource" in result.stderr
    assert "HTTPRoute" in result.stderr


def test_gate_detects_hostname_mismatch(tmp_path: Path, repo_root: Path) -> None:
    """A host that is neither `host` nor `apiHost` fails consistency."""
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    bad = VALID_NGINX_RENDER.replace(
        "- host: app.example.com", "- host: rogue.example.com"
    )
    (rendered / "dev-nginx.yaml").write_text(bad, encoding="utf-8")
    result = _run_gate(
        repo_root, rendered, _ok_routing_dir(tmp_path), ["dev-nginx:nginx"]
    )
    assert result.returncode == 1
    assert "rogue.example.com" in result.stderr


@pytest.mark.parametrize(
    ("name", "axis", "manifest"),
    [
        ("prod-gateway-api", "gateway-api", VALID_GATEWAY_RENDER),
        ("prod-istio", "istio", VALID_ISTIO_RENDER),
    ],
)
def test_gate_accepts_same_origin_parity_renders(
    tmp_path: Path,
    repo_root: Path,
    name: str,
    axis: str,
    manifest: str,
) -> None:
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    (rendered / f"{name}.yaml").write_text(manifest, encoding="utf-8")
    result = _run_gate(
        repo_root, rendered, _ok_routing_dir(tmp_path), [f"{name}:{axis}"]
    )
    assert result.returncode == 0, result.stderr + result.stdout


def test_gate_detects_gateway_hostname_mismatch(
    tmp_path: Path, repo_root: Path
) -> None:
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    bad = VALID_GATEWAY_RENDER.replace(
        "hostname: app.example.com", "hostname: rogue.example.com"
    )
    (rendered / "prod-gateway-api.yaml").write_text(bad, encoding="utf-8")
    result = _run_gate(
        repo_root, rendered, _ok_routing_dir(tmp_path), ["prod-gateway-api:gateway-api"]
    )
    assert result.returncode == 1
    assert "rogue.example.com" in result.stderr
    assert "does not match application host" in result.stderr


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
    result = _run_gate(
        repo_root, rendered, _ok_routing_dir(tmp_path), ["dev-nginx:nginx"]
    )
    assert result.returncode == 1
    assert "missing 'routing-host' ConfigMap" in result.stderr


def test_gate_detects_unknown_backend_service(tmp_path: Path, repo_root: Path) -> None:
    """A backend Service ref that does not exist in the render fails."""
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    bad = VALID_NGINX_RENDER.replace(
        "service: {name: api-gateway, port: {number: 8000}}",
        "service: {name: nonexistent-svc, port: {number: 8000}}",
    )
    (rendered / "dev-nginx.yaml").write_text(bad, encoding="utf-8")
    result = _run_gate(
        repo_root, rendered, _ok_routing_dir(tmp_path), ["dev-nginx:nginx"]
    )
    assert result.returncode == 1
    assert "nonexistent-svc" in result.stderr


def test_gate_detects_routing_stack_importing_base(
    tmp_path: Path, repo_root: Path
) -> None:
    """Routing stacks must not import `../../base`."""
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    (rendered / "dev-nginx.yaml").write_text(VALID_NGINX_RENDER, encoding="utf-8")
    result = _run_gate(
        repo_root, rendered, _bad_routing_dir(tmp_path), ["dev-nginx:nginx"]
    )
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


@pytest.mark.parametrize(
    ("needle", "replacement", "message"),
    [
        (
            "service: {name: api-gateway, port: {number: 8000}}",
            "service: {name: frontend, port: {number: 3000}}",
            "/api/v1 route must target only api-gateway:8000",
        ),
        (
            "nginx.ingress.kubernetes.io/rewrite-target: /v1/$2",
            "nginx.ingress.kubernetes.io/rewrite-target: /api/v1/$2",
            "must rewrite /api/v1 to /v1",
        ),
    ],
)
def test_gate_rejects_misrouted_nginx_api(
    tmp_path: Path,
    repo_root: Path,
    needle: str,
    replacement: str,
    message: str,
) -> None:
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    bad = VALID_NGINX_RENDER.replace(needle, replacement)
    (rendered / "prod-nginx.yaml").write_text(bad, encoding="utf-8")
    result = _run_gate(
        repo_root, rendered, _ok_routing_dir(tmp_path), ["prod-nginx:nginx"]
    )
    assert result.returncode == 1
    assert message in result.stderr


def test_gate_rejects_direct_layer_route(tmp_path: Path, repo_root: Path) -> None:
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    bad = VALID_GATEWAY_RENDER.replace(
        "backendRefs: [{name: api-gateway, port: 8000}]",
        "backendRefs: [{name: layer1-ingestion, port: 8000}]",
    )
    (rendered / "prod-gateway-api.yaml").write_text(bad, encoding="utf-8")
    result = _run_gate(
        repo_root, rendered, _ok_routing_dir(tmp_path), ["prod-gateway-api:gateway-api"]
    )
    assert result.returncode == 1
    assert (
        "external route references internal layer Service 'layer1-ingestion'"
        in result.stderr
    )


def test_gate_rejects_api_rule_after_frontend_fallback(
    tmp_path: Path, repo_root: Path
) -> None:
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    api_rule = VALID_ISTIO_RENDER.index("    - match: [{uri: {prefix: /api/v1}}]")
    fallback_rule = VALID_ISTIO_RENDER.index(
        "    - match: [{uri: {prefix: /}}]", api_rule
    )
    tail = VALID_ISTIO_RENDER[fallback_rule:]
    fallback_end = tail.index("\n", tail.index("route: [{destination:")) + 1
    fallback_block = tail[:fallback_end]
    api_block = VALID_ISTIO_RENDER[api_rule:fallback_rule]
    bad = VALID_ISTIO_RENDER[:api_rule] + fallback_block + api_block
    (rendered / "prod-istio.yaml").write_text(bad, encoding="utf-8")
    result = _run_gate(
        repo_root, rendered, _ok_routing_dir(tmp_path), ["prod-istio:istio"]
    )
    assert result.returncode == 1
    assert "/api/v1 route must precede the frontend catch-all" in result.stderr


def test_gate_rejects_external_layer_service_type(
    tmp_path: Path, repo_root: Path
) -> None:
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    bad = VALID_NGINX_RENDER.replace(
        "spec: {type: ClusterIP, selector: {app: layer1-ingestion}",
        "spec: {type: LoadBalancer, selector: {app: layer1-ingestion}",
    )
    (rendered / "prod-nginx.yaml").write_text(bad, encoding="utf-8")
    result = _run_gate(
        repo_root, rendered, _ok_routing_dir(tmp_path), ["prod-nginx:nginx"]
    )
    assert result.returncode == 1
    assert "Service/layer1-ingestion must remain internal-only" in result.stderr


def test_gate_rejects_empty_render(tmp_path: Path, repo_root: Path) -> None:
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    (rendered / "prod-nginx.yaml").write_text("", encoding="utf-8")
    result = _run_gate(
        repo_root, rendered, _ok_routing_dir(tmp_path), ["prod-nginx:nginx"]
    )
    assert result.returncode == 1
    assert "rendered output is empty" in result.stderr


def test_gate_ignores_non_application_routes_certificates_and_workloads(
    tmp_path: Path, repo_root: Path
) -> None:
    rendered = tmp_path / "rendered"
    rendered.mkdir()
    unrelated = VALID_NGINX_RENDER + textwrap.dedent(
        """\
        ---
        apiVersion: networking.k8s.io/v1
        kind: Ingress
        metadata: {name: private-admin, namespace: monitoring}
        spec:
          rules:
            - host: admin.internal.example
              http:
                paths:
                  - path: /
                    pathType: Prefix
                    backend:
                      service: {name: admin-console, port: {number: 9090}}
        ---
        apiVersion: v1
        kind: Service
        metadata: {name: admin-console, namespace: monitoring}
        spec: {type: ClusterIP, ports: [{port: 9090}]}
        ---
        apiVersion: cert-manager.io/v1
        kind: Certificate
        metadata: {name: internal-service-tls, namespace: value-fabric}
        spec: {dnsNames: [internal.value-fabric.svc]}
        ---
        apiVersion: apps/v1
        kind: Deployment
        metadata: {name: unrelated-monitoring, namespace: monitoring}
        spec:
          selector: {matchLabels: {app: unrelated-monitoring}}
          template:
            metadata: {labels: {app: unrelated-monitoring}}
            spec:
              containers: [{name: monitoring, image: example.invalid/monitoring:latest}]
        """
    )
    (rendered / "prod-nginx.yaml").write_text(unrelated, encoding="utf-8")

    result = _run_gate(
        repo_root, rendered, _ok_routing_dir(tmp_path), ["prod-nginx:nginx"]
    )

    assert result.returncode == 0, result.stderr


def test_gate_detects_missing_deployment_security_context(
    tmp_path: Path, repo_root: Path
) -> None:
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
    result = _run_gate(
        repo_root, rendered, _ok_routing_dir(tmp_path), ["dev-nginx:nginx"]
    )
    assert result.returncode == 1
    assert "runAsNonRoot must be true" in result.stderr
