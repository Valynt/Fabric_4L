# Routing Stack: Istio

> **Status: production-capable when cluster prerequisites are installed.** This
> routing variant depends on a cluster-installed Istio service mesh and external
> edge controls listed below.

## Public routing contract

This parity stack uses one `__HOST__` listener and one ordered `VirtualService`:

```text
/api/v1/<path> -> rewrite /v1/<path> -> api-gateway:8000
/<path>        -> frontend:3000
```

The API route is first because Istio evaluates HTTP routes sequentially. No public route targets L1–L6; those Services remain `ClusterIP` and NetworkPolicy-restricted. NGINX is the canonical production edge, and only one edge mode should be active.

The stack also defines `DestinationRule` resources with `ISTIO_MUTUAL`.

- `PeerAuthentication` with STRICT server-side mTLS for the `value-fabric`
  namespace.
- Baseline `AuthorizationPolicy` for ingress and namespace-internal traffic.

## Remaining Edge Controls

### Edge Authentication: NOT IMPLEMENTED

No `AuthorizationPolicy` or `RequestAuthentication` configured. Options:

- **JWT Validation**: Use `RequestAuthentication` with JWKS endpoint
- **OAuth2/OIDC**: Use external auth service + `AuthorizationPolicy` header rules
- **mTLS-based**: Use `PeerAuthentication` + `AuthorizationPolicy` with source principals

**Status**: Documented pattern only. Production requires implementation.

### Rate Limiting: NOT IMPLEMENTED

Options:

- **Local rate limiting**: Envoy local rate limit filter
- **Global rate limiting**: Redis-backed rate limiting service
- **Mixer-less**: Use EnvoyFilter with rate limiting WASM

**Status**: Documented pattern only. Production requires implementation.

### Security Headers: NOT FULLY IMPLEMENTED

`DestinationRule` does not support response header manipulation. Requires:

- `EnvoyFilter` to inject security headers (HSTS, X-Frame-Options, etc.)
- OR application-layer header handling

### NetworkPolicy

The composed deployment includes an API-gateway policy and layer policies. Configure its ingress namespace as `istio-system`; only the ingress gateway may enter the API gateway on port 8000, and only approved internal callers may reach L1–L6.

### CORS Enforcement: NOT IMPLEMENTED

Use `VirtualService` CORS policy or application-layer CORS handling.

### WAF / Input Validation: NOT IMPLEMENTED

No WAF at Istio layer. Requires:

- External WAF (Cloudflare, AWS WAF)
- OR custom Envoy WASM filters

## Production Readiness Checklist

Before applying this routing stack:

- [x] Add `PeerAuthentication` STRICT mode for server-side mTLS enforcement
- [x] Add baseline namespace `AuthorizationPolicy`
- [ ] Implement edge authentication (`AuthorizationPolicy` + `RequestAuthentication`)
- [ ] Implement rate limiting (local or global)
- [ ] Add security headers via `EnvoyFilter` or application layer
- [ ] Harden NetworkPolicy (allow from `istio-system` only)
- [ ] Configure WAF or document external WAF prerequisite
- [ ] Validate TLS 1.0/1.1 rejection at ingress gateway
- [ ] Add CI gates for all security controls

This stack does **not** import `../../base`. It is composed under
`k8s/deployments/prod-istio/`.

## Required cluster prerequisites

- **Istio** 1.20+ installed (https://istio.io/latest/docs/setup/install/).
- The `value-fabric` namespace labeled for sidecar injection:
  ```bash
  kubectl label namespace value-fabric istio-injection=enabled
  ```
- TLS Secret `frontend-tls` present **in the `istio-system` namespace** (Istio Gateway requirement). Operators typically use cert-manager with the `istio-csr` integration or sync Secrets across namespaces.
- One DNS A record for `__HOST__` pointing at the `istio-ingressgateway` external IP / LoadBalancer.

## Apply

```bash
kustomize build k8s/deployments/prod-istio | kubectl apply -f -
```

## Validation

```bash
kustomize build k8s/deployments/prod-istio | \
  kubeconform -strict -summary \
    -schema-location default \
    -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
    -

kubectl -n value-fabric get gateway,virtualservice,destinationrule
istioctl analyze -n value-fabric
make production-edge-smoke APPLICATION_URL=https://<your-host>
# If edge authentication requires credentials, set EDGE_SMOKE_AUTHORIZATION
# (for example, "Bearer ...") or EDGE_SMOKE_COOKIE in the environment.
```

## Troubleshooting

- **503 from gateway**: VirtualService backend Service may not exist or be in
  a different namespace. `istioctl proxy-config routes <ingressgateway-pod>`.
- **TLS handshake failure**: the `frontend-tls` Secret must be in `istio-system`, not `value-fabric`.
- **Sidecar not injected**: namespace label missing or pods predate label.
- **Sentinel `__HOST__` visible in cluster**: deployment overlay's
  `replacements:` did not run.
