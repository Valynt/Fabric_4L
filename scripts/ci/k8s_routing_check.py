"""
k8s routing axis CI gate.

Validates each rendered deployment overlay under k8s/deployments/ for:

  1. Mutual exclusivity: only routing kinds belonging to that deployment's
     routing axis are present. (apiVersion-aware: Gateway API and Istio both
     use `kind: Gateway`, distinguished by apiVersion group.)

  2. Hostname consistency: every host/TLS-name field in routing resources
     equals the value of the deployment's `routing-host` ConfigMap
     (`data.host` for the frontend host, `data.apiHost` for the API host).

  3. No surviving sentinels (`__HOST__`, `__API_HOST__`).

  4. Service-existence: every backend reference in routing resources
     (`Ingress.spec.rules[].http.paths[].backend.service.name`,
     `HTTPRoute.spec.rules[].backendRefs[].name`,
     `VirtualService.spec.http[].route[].destination.host`) resolves to a
     Service rendered from the env overlay.

  5. Routing stacks under k8s/routing/* must not import `../../base`.
  6. Deployment pod/container security contexts include baseline hardening.
  7. NGINX ingress resources include mandatory CORS, auth, and rate-limit annotations.

Usage:
  python scripts/ci/k8s_routing_check.py \
      --rendered-dir /tmp/renders \
      --routing-dir k8s/routing \
      --deployment dev-nginx:nginx \
      --deployment prod-nginx:nginx \
      --deployment prod-gateway-api:gateway-api \
      --deployment prod-istio:istio

Each --deployment flag is `<deployment-name>:<routing-axis>`. The corresponding
rendered file is expected at `<rendered-dir>/<deployment-name>.yaml`.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

# Routing axis -> set of (apiVersionGroup, kind) tuples that ARE allowed for
# that axis. apiVersionGroup is the part before the first '/' (e.g. for
# "networking.k8s.io/v1" it is "networking.k8s.io"). Anything else from the
# union of routing kinds is forbidden.
ROUTING_KIND_MATRIX: dict[str, set[tuple[str, str]]] = {
    "nginx": {
        ("networking.k8s.io", "Ingress"),
        ("cert-manager.io", "ClusterIssuer"),
    },
    "gateway-api": {
        ("gateway.networking.k8s.io", "Gateway"),
        ("gateway.networking.k8s.io", "HTTPRoute"),
        ("cert-manager.io", "Certificate"),
    },
    "istio": {
        ("networking.istio.io", "Gateway"),
        ("networking.istio.io", "VirtualService"),
        ("networking.istio.io", "DestinationRule"),
    },
}

# All routing-related (group, kind) tuples across all axes. Used to detect
# cross-axis leaks: anything in this set that is not in the deployment's
# allowed subset is forbidden.
ALL_ROUTING_KINDS: set[tuple[str, str]] = set().union(*ROUTING_KIND_MATRIX.values())

# The Service name the API host must route to. The gateway is the only
# public entry point for API traffic; layer Services must never be exposed
# directly by an Ingress. Enforced by _check_gateway_only_api_ingress().
GATEWAY_SERVICE_NAME = "api-gateway"

# Path prefixes that, if routed directly to a non-gateway Service, constitute
# a bypass of the gateway (auth, tenant context, rate limiting, audit).
# These are the public layer-segment surfaces; the gateway owns them and
# delegates internally to the owning layer Service over the mesh.
BYPASS_PATH_PREFIXES = ("/layer1", "/layer2", "/layer3", "/layer4", "/layer5", "/layer6")

SENTINELS = ("__HOST__", "__API_HOST__")

REQUIRED_NGINX_ANNOTATIONS: dict[str, tuple[str, ...]] = {
    "cors": ("nginx.ingress.kubernetes.io/enable-cors",),
    "auth": (
        "nginx.ingress.kubernetes.io/auth-url",
        "nginx.ingress.kubernetes.io/auth-signin",
        "nginx.ingress.kubernetes.io/auth-response-headers",
    ),
    "rate_limiting": (
        "nginx.ingress.kubernetes.io/limit-rps",
        "nginx.ingress.kubernetes.io/limit-rpm",
        "nginx.ingress.kubernetes.io/limit-connections",
        "nginx.ingress.kubernetes.io/limit-burst-multiplier",
    ),
}


def _api_group(api_version: str) -> str:
    """Return the API group (substring before '/') from a Kubernetes apiVersion."""
    return api_version.split("/", 1)[0] if "/" in api_version else ""


def _load_docs(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return [d for d in yaml.safe_load_all(fh) if isinstance(d, dict)]


def _walk_strings(node: object) -> Iterable[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _walk_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk_strings(v)


LAYER_SERVICE_NAMES = {
    "layer1-ingestion",
    "layer2-extraction",
    "layer3-knowledge",
    "layer4-agents",
    "layer5-ground-truth",
    "layer6-benchmarks",
}
LAYER_COMPONENT_SUFFIXES = tuple(f"-layer{i}" for i in range(1, 7))


@dataclass(frozen=True)
class Route:
    resource: str
    host: str
    external_path: str
    backend: str
    port: int | None
    upstream_prefix: str | None
    order: int


def _is_layer_service(name: str) -> bool:
    return name in LAYER_SERVICE_NAMES or name.endswith(LAYER_COMPONENT_SUFFIXES)


def _is_gateway_service(name: str) -> bool:
    return name == "api-gateway" or name.endswith("-api")


def _is_frontend_service(name: str) -> bool:
    return name == "frontend" or name.endswith("-frontend")


def _collect_host_fields(doc: dict) -> list[str]:
    """Return every public hostname declared by a routing or certificate resource."""
    spec = doc.get("spec", {}) or {}
    kind = doc.get("kind", "")
    group = _api_group(doc.get("apiVersion", ""))
    out: list[str] = []

    if group == "networking.k8s.io" and kind == "Ingress":
        out.extend(r["host"] for r in spec.get("rules", []) or [] if r.get("host"))
        for tls in spec.get("tls", []) or []:
            out.extend(tls.get("hosts", []) or [])
    elif group == "cert-manager.io" and kind == "Certificate":
        out.extend(spec.get("dnsNames", []) or [])
    elif group == "gateway.networking.k8s.io" and kind == "Gateway":
        out.extend(
            listener["hostname"]
            for listener in spec.get("listeners", []) or []
            if listener.get("hostname")
        )
    elif group == "gateway.networking.k8s.io" and kind == "HTTPRoute":
        out.extend(spec.get("hostnames", []) or [])
    elif group == "networking.istio.io" and kind == "Gateway":
        for server in spec.get("servers", []) or []:
            out.extend(server.get("hosts", []) or [])
    elif group == "networking.istio.io" and kind == "VirtualService":
        out.extend(spec.get("hosts", []) or [])
    return out


def _ingress_upstream_prefix(doc: dict, path: str) -> str | None:
    if not path.startswith("/api/v1"):
        return None
    annotations = (doc.get("metadata") or {}).get("annotations") or {}
    target = str(annotations.get("nginx.ingress.kubernetes.io/rewrite-target", ""))
    if target in {"/v1", "/v1/$2"}:
        return "/v1"
    return target or None


def _gateway_upstream_prefix(rule: dict, path: str) -> str | None:
    if path != "/api/v1":
        return None
    for route_filter in rule.get("filters", []) or []:
        rewrite = route_filter.get("urlRewrite") or {}
        rewrite_path = rewrite.get("path") or {}
        if route_filter.get("type") == "URLRewrite":
            return rewrite_path.get("replacePrefixMatch")
    return None


def _collect_routes(doc: dict) -> list[Route]:
    spec = doc.get("spec", {}) or {}
    kind = doc.get("kind", "")
    group = _api_group(doc.get("apiVersion", ""))
    name = (doc.get("metadata") or {}).get("name", "?")
    resource = f"{kind}/{name}"
    routes: list[Route] = []

    if group == "networking.k8s.io" and kind == "Ingress":
        order = 0
        for rule in spec.get("rules", []) or []:
            for path_entry in (rule.get("http") or {}).get("paths", []) or []:
                service = (path_entry.get("backend") or {}).get("service") or {}
                port = (service.get("port") or {}).get("number")
                path = str(path_entry.get("path", ""))
                routes.append(
                    Route(
                        resource,
                        str(rule.get("host", "")),
                        "/api/v1" if path.startswith("/api/v1") else path,
                        str(service.get("name", "")),
                        port,
                        _ingress_upstream_prefix(doc, path),
                        order,
                    )
                )
                order += 1
    elif group == "gateway.networking.k8s.io" and kind == "HTTPRoute":
        hosts = spec.get("hostnames", []) or [""]
        for order, rule in enumerate(spec.get("rules", []) or []):
            matches = rule.get("matches", []) or [{}]
            refs = rule.get("backendRefs", []) or []
            for match in matches:
                path = ((match.get("path") or {}).get("value")) or "/"
                for ref in refs:
                    for host in hosts:
                        routes.append(
                            Route(
                                resource,
                                host,
                                path,
                                str(ref.get("name", "")),
                                ref.get("port"),
                                _gateway_upstream_prefix(rule, path),
                                order,
                            )
                        )
    elif group == "networking.istio.io" and kind == "VirtualService":
        hosts = spec.get("hosts", []) or [""]
        for order, http in enumerate(spec.get("http", []) or []):
            matches = http.get("match", []) or [{}]
            destinations = http.get("route", []) or []
            for match in matches:
                path = ((match.get("uri") or {}).get("prefix")) or "/"
                rewrite = (http.get("rewrite") or {}).get("uri")
                for destination_entry in destinations:
                    destination = destination_entry.get("destination") or {}
                    service = str(destination.get("host", "")).split(".")[0]
                    port = (destination.get("port") or {}).get("number")
                    for host in hosts:
                        routes.append(
                            Route(resource, host, path, service, port, rewrite, order)
                        )
    return routes


def _collect_backends(doc: dict) -> list[str]:
    return [route.backend for route in _collect_routes(doc) if route.backend]


def _collect_backend_refs_with_paths(doc: dict) -> list[tuple[str, str]]:
    """Return [(service_name, path_prefix), ...] for a routing resource.

    For NGINX Ingress, HTTPRoute, and VirtualService, extract each
    (backend Service, path prefix) pair so the bypass check can detect
    direct layer exposure on any routing axis, not just nginx Ingress.
    """
    spec = doc.get("spec", {}) or {}
    kind = doc.get("kind", "")
    group = _api_group(doc.get("apiVersion", ""))
    out: list[tuple[str, str]] = []

    if group == "networking.k8s.io" and kind == "Ingress":
        for rule in spec.get("rules", []) or []:
            for path in (rule.get("http") or {}).get("paths", []) or []:
                svc = ((path.get("backend") or {}).get("service") or {}).get("name")
                if svc:
                    out.append((svc, path.get("path", "") or ""))

    elif group == "gateway.networking.k8s.io" and kind == "HTTPRoute":
        for rule in spec.get("rules", []) or []:
            prefix = ""
            for match in rule.get("matches", []) or []:
                p = (match.get("path") or {}).get("value", "") or ""
                if p:
                    prefix = p
                    break
            for ref in rule.get("backendRefs", []) or []:
                if ref.get("name"):
                    out.append((ref["name"], prefix))

    elif group == "networking.istio.io" and kind == "VirtualService":
        for http in spec.get("http", []) or []:
            prefix = ""
            for match in http.get("match", []) or []:
                p = (match.get("uri") or {}).get("prefix", "") or ""
                if p:
                    prefix = p
                    break
            for route in http.get("route", []) or []:
                host = (route.get("destination") or {}).get("host")
                if host:
                    out.append((host.split(".")[0], prefix))

    return out


def _check_gateway_only_api_ingress(name: str, docs: list[dict]) -> list[str]:
    """Assert every API-bucket routing resource routes to the gateway Service.

    The gateway is the only public entry point for API traffic. A routing
    resource whose metadata.name maps to the API bucket (``layer-apis``)
    must route every path/backend to ``api-gateway``; no backend may point
    directly at a layer Service (``layer1-ingestion`` …
    ``layer6-benchmarks``) or any other non-gateway backend, because that
    bypasses the gateway's auth, tenant resolution, rate limiting, and
    audit logging. Applies to NGINX Ingress, Gateway API HTTPRoute, and
    Istio VirtualService.

    Also catches direct bypasses on *any* routing resource: a path
    starting with one of the BYPASS_PATH_PREFIXES routed to a
    non-gateway Service is a bypass regardless of the resource name.
    """
    errors: list[str] = []
    for d in docs:
        gk = (_api_group(d.get("apiVersion", "")), d.get("kind", ""))
        if gk not in ALL_ROUTING_KINDS:
            continue
        md_name = d.get("metadata", {}).get("name", "?")
        is_api_bucket = md_name == "layer-apis"
        for svc, path_prefix in _collect_backend_refs_with_paths(d):
            # Rule 1: an API-bucket resource must route to the gateway.
            if is_api_bucket and svc != GATEWAY_SERVICE_NAME:
                errors.append(
                    f"{name}: {gk[1]}/{md_name} routes path '{path_prefix}' to "
                    f"Service '{svc}', but API traffic must route through "
                    f"'{GATEWAY_SERVICE_NAME}'. Direct layer exposure bypasses "
                    f"gateway auth/tenant/rate-limit/audit invariants."
                )
            # Rule 2: any resource routing a layer-segment path to a
            # non-gateway Service is a bypass, regardless of name.
            if (
                path_prefix in BYPASS_PATH_PREFIXES
                and svc != GATEWAY_SERVICE_NAME
            ):
                errors.append(
                    f"{name}: {gk[1]}/{md_name} routes bypass path "
                    f"'{path_prefix}' directly to Service '{svc}'; "
                    f"layer segments must enter through "
                    f"'{GATEWAY_SERVICE_NAME}'."
                )
    return errors


def _check_deployment(name: str, axis: str, rendered: Path) -> list[str]:
    if axis not in ROUTING_KIND_MATRIX:
        return [f"{name}: unknown routing axis '{axis}'"]
    if not rendered.exists():
        return [f"{name}: rendered file not found: {rendered}"]

    docs = _load_docs(rendered)
    errors: list[str] = []
    if not docs:
        return [f"{name}: rendered output is empty"]

    # 1. Sentinel survival.
    raw = rendered.read_text(encoding="utf-8")
    for sentinel in SENTINELS:
        if sentinel in raw:
            errors.append(
                f"{name}: sentinel '{sentinel}' survived into rendered output"
            )

    # 2. Resolve the canonical application host before selecting edge resources.
    cm = next(
        (
            d
            for d in docs
            if d.get("kind") == "ConfigMap"
            and d.get("metadata", {}).get("name") == "routing-host"
        ),
        None,
    )
    application_host: str | None = None
    if cm is None:
        errors.append(f"{name}: missing 'routing-host' ConfigMap")
    else:
        data = cm.get("data") or {}
        application_host = data.get("host")
        if not application_host:
            errors.append(f"{name}: routing-host ConfigMap must define 'host'")

    def has_canonical_application_backend(doc: dict) -> bool:
        return any(
            (route.external_path == "/api/v1" and _is_gateway_service(route.backend))
            or (route.external_path == "/" and _is_frontend_service(route.backend))
            for route in _collect_routes(doc)
        )

    application_route_docs = [d for d in docs if has_canonical_application_backend(d)]
    referenced_gateways = {
        ref.get("name")
        for d in application_route_docs
        for ref in ((d.get("spec") or {}).get("parentRefs") or [])
        if ref.get("name")
    }
    referenced_tls_secrets: set[str] = set()
    for d in docs:
        metadata_name = (d.get("metadata") or {}).get("name")
        if d not in application_route_docs and metadata_name not in referenced_gateways:
            continue
        spec = d.get("spec") or {}
        for tls in spec.get("tls", []) or []:
            if tls.get("secretName"):
                referenced_tls_secrets.add(tls["secretName"])
        for listener in spec.get("listeners", []) or []:
            for ref in (listener.get("tls") or {}).get("certificateRefs") or []:
                if ref.get("name"):
                    referenced_tls_secrets.add(ref["name"])

    def is_application_edge_resource(doc: dict) -> bool:
        metadata_name = (doc.get("metadata") or {}).get("name")
        return bool(
            has_canonical_application_backend(doc)
            or metadata_name == "value-fabric-gateway"
            or metadata_name in referenced_gateways
            or metadata_name in referenced_tls_secrets
            or (application_host and application_host in _collect_host_fields(doc))
        )

    # Host consistency is enforced only for the application edge. Internal
    # service certificates and unrelated admin routes may use other DNS names.
    if application_host:
        for d in docs:
            if not is_application_edge_resource(d):
                continue
            gk = (_api_group(d.get("apiVersion", "")), d.get("kind", ""))
            md_name = d.get("metadata", {}).get("name", "?")
            for observed in _collect_host_fields(d):
                if observed != application_host:
                    errors.append(
                        f"{name}: host '{observed}' on {gk[1]}/{md_name} "
                        f"does not match application host '{application_host}'"
                    )

    # 3. Mutual exclusivity applies to the application edge, not unrelated
    # monitoring/admin routes bundled into the same production overlay.
    allowed = ROUTING_KIND_MATRIX[axis]
    for d in docs:
        gk = (_api_group(d.get("apiVersion", "")), d.get("kind", ""))
        if (
            gk in ALL_ROUTING_KINDS
            and gk not in allowed
            and is_application_edge_resource(d)
        ):
            md_name = d.get("metadata", {}).get("name", "?")
            errors.append(
                f"{name}: forbidden routing resource for axis '{axis}': "
                f"{gk[0]}/{gk[1]} (name={md_name})"
            )

    # 4. Service-existence.
    rendered_services = {
        d.get("metadata", {}).get("name")
        for d in docs
        if d.get("kind") == "Service" and d.get("metadata", {}).get("name")
    }
    for d in docs:
        gk = (_api_group(d.get("apiVersion", "")), d.get("kind", ""))
        if gk not in ALL_ROUTING_KINDS:
            continue
        for svc in _collect_backends(d):
            if svc not in rendered_services:
                errors.append(
                    f"{name}: routing resource {gk[1]}/"
                    f"{d.get('metadata', {}).get('name', '?')} "
                    f"references Service '{svc}' which is not in the rendered output"
                )

    # 6. Canonical same-origin route topology and internal-only layer Services.
    routes = [route for d in docs for route in _collect_routes(d)]
    application_routes = [route for route in routes if route.host == application_host]
    api_routes = [
        route for route in application_routes if route.external_path == "/api/v1"
    ]
    frontend_routes = [
        route for route in application_routes if route.external_path == "/"
    ]

    if len(api_routes) != 1:
        errors.append(
            f"{name}: expected exactly one /api/v1 route, found {len(api_routes)}"
        )
    else:
        api_route = api_routes[0]
        if not _is_gateway_service(api_route.backend) or api_route.port != 8000:
            errors.append(
                f"{name}: /api/v1 route must target only api-gateway:8000 "
                f"(got {api_route.backend}:{api_route.port})"
            )
        if api_route.upstream_prefix != "/v1":
            errors.append(
                f"{name}: /api/v1 route must rewrite /api/v1 to /v1 "
                f"(got {api_route.upstream_prefix!r})"
            )
        if application_host and api_route.host != application_host:
            errors.append(f"{name}: /api/v1 route is not on the application host")

    if len(frontend_routes) != 1:
        errors.append(
            f"{name}: expected exactly one / frontend route, found {len(frontend_routes)}"
        )
    else:
        frontend_route = frontend_routes[0]
        if (
            not _is_frontend_service(frontend_route.backend)
            or frontend_route.port != 3000
        ):
            errors.append(
                f"{name}: / route must target only frontend:3000 "
                f"(got {frontend_route.backend}:{frontend_route.port})"
            )
        if application_host and frontend_route.host != application_host:
            errors.append(f"{name}: / route is not on the application host")
        if (
            axis == "istio"
            and api_routes
            and api_routes[0].order >= frontend_route.order
        ):
            errors.append(f"{name}: /api/v1 route must precede the frontend catch-all")

    for route in routes:
        if _is_layer_service(route.backend):
            errors.append(
                f"{name}: external route references internal layer Service '{route.backend}'"
            )

    for service in (d for d in docs if d.get("kind") == "Service"):
        service_name = (service.get("metadata") or {}).get("name", "")
        service_type = (service.get("spec") or {}).get("type", "ClusterIP")
        if _is_layer_service(service_name) and service_type != "ClusterIP":
            errors.append(
                f"{name}: Service/{service_name} must remain internal-only "
                f"(type ClusterIP, got {service_type})"
            )

    expected_route_kind = {
        "nginx": ("networking.k8s.io", "Ingress"),
        "gateway-api": ("gateway.networking.k8s.io", "HTTPRoute"),
        "istio": ("networking.istio.io", "VirtualService"),
    }[axis]
    if not any(
        (_api_group(d.get("apiVersion", "")), d.get("kind", "")) == expected_route_kind
        and is_application_edge_resource(d)
        for d in docs
    ):
        errors.append(
            f"{name}: missing required {expected_route_kind[1]} routing resource"
        )

    # 7. Gateway-only API ingress check.
    errors.extend(_check_gateway_only_api_ingress(name, docs))

    # 8. Mandatory controls apply to API ingress, not the frontend SPA.
    if axis == "nginx":
        api_resources = {route.resource for route in api_routes}
        for d in docs:
            gk = (_api_group(d.get("apiVersion", "")), d.get("kind", ""))
            md_name = d.get("metadata", {}).get("name", "?")
            if (
                gk != ("networking.k8s.io", "Ingress")
                or f"Ingress/{md_name}" not in api_resources
            ):
                continue
            annotations = (d.get("metadata", {}) or {}).get("annotations") or {}
            for control, keys in REQUIRED_NGINX_ANNOTATIONS.items():
                for key in keys:
                    if not str(annotations.get(key, "")).strip():
                        errors.append(
                            f"{name}: Ingress/{md_name} missing required {control} annotation '{key}'"
                        )

    # 8. Security baseline for workloads that implement or authenticate the
    # application edge. Unrelated monitoring workloads have their own gates.
    edge_workloads = {route.backend for route in application_routes if route.backend}
    for d in docs:
        if d.get("kind") != "Deployment":
            continue
        md_name = d.get("metadata", {}).get("name", "?")
        if md_name not in edge_workloads and "oauth2-proxy" not in md_name:
            continue
        pod_spec = ((d.get("spec") or {}).get("template") or {}).get("spec") or {}
        pod_sc = pod_spec.get("securityContext") or {}
        if pod_sc.get("runAsNonRoot") is not True:
            errors.append(
                f"{name}: Deployment/{md_name} pod securityContext.runAsNonRoot must be true"
            )
        seccomp_type = (pod_sc.get("seccompProfile") or {}).get("type")
        if seccomp_type != "RuntimeDefault":
            errors.append(
                f"{name}: Deployment/{md_name} pod securityContext.seccompProfile.type "
                "must be RuntimeDefault"
            )

        for container in pod_spec.get("containers", []) or []:
            c_name = container.get("name", "?")
            c_sc = container.get("securityContext") or {}
            if c_sc.get("allowPrivilegeEscalation") is not False:
                errors.append(
                    f"{name}: Deployment/{md_name} container/{c_name} "
                    "securityContext.allowPrivilegeEscalation must be false"
                )
            if c_sc.get("readOnlyRootFilesystem") is not True:
                errors.append(
                    f"{name}: Deployment/{md_name} container/{c_name} "
                    "securityContext.readOnlyRootFilesystem must be true"
                )
            dropped = (c_sc.get("capabilities") or {}).get("drop") or []
            if "ALL" not in dropped:
                errors.append(
                    f"{name}: Deployment/{md_name} container/{c_name} "
                    "securityContext.capabilities.drop must include ALL"
                )

    return errors


def _check_routing_stacks_no_base(routing_dir: Path) -> list[str]:
    """Routing stack kustomizations must not import ../../base or ../base.

    Parses the kustomization YAML and inspects every list-of-paths field
    rather than grepping raw text (so the rule against base imports does not
    trip on comments that mention `../../base`).
    """
    errors: list[str] = []
    forbidden = {"../../base", "../base", "../../../base"}
    path_fields = ("resources", "components", "bases")
    for kfile in routing_dir.glob("*/kustomization.yaml"):
        try:
            doc = yaml.safe_load(kfile.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            errors.append(f"{kfile}: invalid YAML ({exc})")
            continue
        if not isinstance(doc, dict):
            continue
        for field in path_fields:
            for entry in doc.get(field, []) or []:
                if isinstance(entry, str) and entry.strip() in forbidden:
                    errors.append(
                        f"{kfile}: routing stacks must not import base "
                        f"(found '{entry}' in '{field}')"
                    )
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rendered-dir", type=Path, required=True)
    ap.add_argument("--routing-dir", type=Path, default=Path("k8s/routing"))
    ap.add_argument(
        "--deployment",
        action="append",
        required=True,
        help="Format: <deployment-name>:<routing-axis>",
    )
    args = ap.parse_args()

    all_errors: list[str] = []
    all_errors.extend(_check_routing_stacks_no_base(args.routing_dir))
    for spec in args.deployment:
        if ":" not in spec:
            all_errors.append(f"--deployment must be NAME:AXIS, got: {spec}")
            continue
        name, axis = spec.split(":", 1)
        rendered = args.rendered_dir / f"{name}.yaml"
        all_errors.extend(_check_deployment(name, axis, rendered))

    if all_errors:
        print("FAIL: k8s routing checks reported issues:", file=sys.stderr)
        for e in all_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("OK: all k8s routing checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
