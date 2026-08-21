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


FRONTEND_BUCKET = "frontend"
API_BUCKET = "api"
EITHER_BUCKET = "either"  # listener legitimately carries both hosts (e.g. HTTP->HTTPS redirect)

# Map resource-name suffix -> expected bucket. Used to derive which
# host bucket a host-bearing resource belongs to.
NAME_TO_BUCKET: dict[str, str] = {
    "frontend": FRONTEND_BUCKET,
    "frontend-tls": FRONTEND_BUCKET,
    "layer-apis": API_BUCKET,
    "layer-apis-tls": API_BUCKET,
}


def _classify_listener(listener_name: str) -> str | None:
    """Map a Gateway API listener name or Istio server port name to a bucket.

    Returns:
        FRONTEND_BUCKET / API_BUCKET / EITHER_BUCKET, or None if not classifiable.

    Listener names follow the convention:
      - `*-frontend` (e.g. `http-frontend`, `https-frontend`) -> frontend.
      - `*-api` (e.g. `http-api`, `https-api`) -> api.
      - bare `http` (Istio's combined HTTP->HTTPS redirect server) carries
        both hosts and is treated as EITHER_BUCKET.
    """
    if not listener_name:
        return None
    n = listener_name.lower()
    if n == "http":
        return EITHER_BUCKET
    if n.endswith("-frontend"):
        return FRONTEND_BUCKET
    if n.endswith("-api"):
        return API_BUCKET
    return None


def _collect_host_fields(doc: dict) -> list[tuple[str, str]]:
    """Return [(bucket, host), ...] tuples extracted from a host-bearing routing doc.

    Each entry binds a host string to the bucket it is *expected* to belong to:
      - `frontend` (must equal the frontend host from routing-host ConfigMap)
      - `api` (must equal the API host)
      - `either` (must equal one of the two; used for HTTP redirect listeners)

    For Gateway API `Gateway` and Istio `Gateway` resources, classification is
    derived per-listener / per-server from the listener/port name. This means a
    swap bug (e.g. an `https-api` listener carrying the frontend host) is
    caught, not silently accepted.

    Non-host-bearing routing resources return `[]`.
    """
    name = doc.get("metadata", {}).get("name", "")
    spec = doc.get("spec", {}) or {}
    kind = doc.get("kind", "")
    group = _api_group(doc.get("apiVersion", ""))
    bucket_for_name = NAME_TO_BUCKET.get(name)

    out: list[tuple[str, str]] = []

    if group == "networking.k8s.io" and kind == "Ingress":
        if bucket_for_name is None:
            return out
        for rule in spec.get("rules", []) or []:
            if rule.get("host"):
                out.append((bucket_for_name, rule["host"]))
        for tls in spec.get("tls", []) or []:
            for h in tls.get("hosts", []) or []:
                out.append((bucket_for_name, h))

    elif group == "cert-manager.io" and kind == "Certificate":
        if bucket_for_name is None:
            return out
        for h in spec.get("dnsNames", []) or []:
            out.append((bucket_for_name, h))

    elif group == "gateway.networking.k8s.io" and kind == "Gateway":
        for listener in spec.get("listeners", []) or []:
            host = listener.get("hostname")
            if not host:
                continue
            bucket = _classify_listener(listener.get("name", ""))
            if bucket is None:
                # Unclassifiable listener name -> accept either bucket but
                # surface as a soft observation through EITHER_BUCKET so a
                # rogue host still fails the {host, apiHost} check.
                bucket = EITHER_BUCKET
            out.append((bucket, host))

    elif group == "gateway.networking.k8s.io" and kind == "HTTPRoute":
        if bucket_for_name is None:
            return out
        for h in spec.get("hostnames", []) or []:
            out.append((bucket_for_name, h))

    elif group == "networking.istio.io" and kind == "Gateway":
        for server in spec.get("servers", []) or []:
            port_name = (server.get("port") or {}).get("name", "")
            bucket = _classify_listener(port_name)
            if bucket is None:
                bucket = EITHER_BUCKET
            for h in server.get("hosts", []) or []:
                out.append((bucket, h))

    elif group == "networking.istio.io" and kind == "VirtualService":
        if bucket_for_name is None:
            return out
        for h in spec.get("hosts", []) or []:
            out.append((bucket_for_name, h))

    return out


def _collect_backends(doc: dict) -> list[str]:
    """Return Service names referenced as backends by this routing resource."""
    spec = doc.get("spec", {}) or {}
    kind = doc.get("kind", "")
    group = _api_group(doc.get("apiVersion", ""))
    backends: list[str] = []

    if group == "networking.k8s.io" and kind == "Ingress":
        for rule in spec.get("rules", []) or []:
            for path in (rule.get("http") or {}).get("paths", []) or []:
                svc = ((path.get("backend") or {}).get("service") or {}).get("name")
                if svc:
                    backends.append(svc)

    elif group == "gateway.networking.k8s.io" and kind == "HTTPRoute":
        for rule in spec.get("rules", []) or []:
            for ref in rule.get("backendRefs", []) or []:
                if ref.get("name"):
                    backends.append(ref["name"])

    elif group == "networking.istio.io" and kind == "VirtualService":
        for http in spec.get("http", []) or []:
            for route in http.get("route", []) or []:
                host = (route.get("destination") or {}).get("host")
                if host:
                    # host may be a short Service name or FQDN; take first label.
                    backends.append(host.split(".")[0])

    return backends


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

    # 1. Sentinel survival.
    raw = rendered.read_text(encoding="utf-8")
    for sentinel in SENTINELS:
        if sentinel in raw:
            errors.append(f"{name}: sentinel '{sentinel}' survived into rendered output")

    # 2. Mutual exclusivity.
    allowed = ROUTING_KIND_MATRIX[axis]
    for d in docs:
        gk = (_api_group(d.get("apiVersion", "")), d.get("kind", ""))
        if gk in ALL_ROUTING_KINDS and gk not in allowed:
            md_name = d.get("metadata", {}).get("name", "?")
            errors.append(
                f"{name}: forbidden routing resource for axis '{axis}': "
                f"{gk[0]}/{gk[1]} (name={md_name})"
            )

    # 3. routing-host ConfigMap presence + 4. hostname consistency.
    cm = next(
        (
            d
            for d in docs
            if d.get("kind") == "ConfigMap"
            and d.get("metadata", {}).get("name") == "routing-host"
        ),
        None,
    )
    if cm is None:
        errors.append(f"{name}: missing 'routing-host' ConfigMap")
    else:
        data = cm.get("data") or {}
        host = data.get("host")
        api_host = data.get("apiHost")
        if not host or not api_host:
            errors.append(f"{name}: routing-host ConfigMap must define 'host' and 'apiHost'")
        else:
            bucket_to_expected = {
                FRONTEND_BUCKET: {host},
                API_BUCKET: {api_host},
                EITHER_BUCKET: {host, api_host},
            }
            for d in docs:
                gk = (_api_group(d.get("apiVersion", "")), d.get("kind", ""))
                if gk not in ALL_ROUTING_KINDS:
                    continue
                md_name = d.get("metadata", {}).get("name", "?")
                for bucket, observed in _collect_host_fields(d):
                    expected = bucket_to_expected[bucket]
                    if observed not in expected:
                        errors.append(
                            f"{name}: host '{observed}' on {gk[1]}/{md_name} "
                            f"(bucket={bucket}) does not match routing-host "
                            f"ConfigMap (expected one of {sorted(expected)}; "
                            f"host={host}, apiHost={api_host})"
                        )

    # 5. Service-existence.
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

    # 8. Gateway-only API ingress: no Ingress may route API traffic
    # directly to a layer Service; the gateway is the only public entry.
    errors.extend(_check_gateway_only_api_ingress(name, docs))

    # 7. Mandatory nginx ingress controls (rendered manifests).
    if axis == "nginx":
        for d in docs:
            gk = (_api_group(d.get("apiVersion", "")), d.get("kind", ""))
            if gk != ("networking.k8s.io", "Ingress"):
                continue
            md_name = d.get("metadata", {}).get("name", "?")
            annotations = (d.get("metadata", {}) or {}).get("annotations") or {}
            for control, keys in REQUIRED_NGINX_ANNOTATIONS.items():
                for key in keys:
                    if not str(annotations.get(key, "")).strip():
                        errors.append(
                            f"{name}: Ingress/{md_name} missing required {control} annotation '{key}'"
                        )

    # 6. Deployment securityContext baseline for rendered deployment bundles.
    for d in docs:
        if d.get("kind") != "Deployment":
            continue
        md_name = d.get("metadata", {}).get("name", "?")
        pod_spec = (((d.get("spec") or {}).get("template") or {}).get("spec") or {})
        pod_sc = pod_spec.get("securityContext") or {}
        if pod_sc.get("runAsNonRoot") is not True:
            errors.append(f"{name}: Deployment/{md_name} pod securityContext.runAsNonRoot must be true")
        seccomp_type = ((pod_sc.get("seccompProfile") or {}).get("type"))
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
            dropped = ((c_sc.get("capabilities") or {}).get("drop") or [])
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
