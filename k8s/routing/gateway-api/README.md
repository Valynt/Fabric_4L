# Routing Stack: Gateway API (EXPERIMENTAL)

> **Status: EXPERIMENTAL.** This routing variant is **NOT** production-ready.
> It is missing critical security controls and remains render-only in CI.
>
> **Use `prod-nginx` for production deployments.**

## Public routing contract

This parity stack uses one application listener and one same-host `HTTPRoute`:

```text
/api/v1/<path> -> URLRewrite /v1/<path> -> api-gateway:8000
/<path>        -> frontend:3000
```

Gateway API prefix specificity ensures the API rule wins over `/`. No public route targets L1–L6; those Services remain `ClusterIP` and NetworkPolicy-restricted. NGINX is the canonical production edge, and only one edge mode should be active.

The selected controller must support the standard `URLRewrite` filter. cert-manager provides the single `frontend-tls` certificate.

## Security Gaps (NOT IMPLEMENTED)

The following security controls are **NOT** implemented in this stack:

### Edge Authentication: NOT IMPLEMENTED

Gateway API does not have a standardized external auth mechanism. Options:

- **Envoy Gateway**: Use `SecurityPolicy` with `extAuth` (requires Envoy Gateway v1.0+)
- **Istio Gateway API**: Use `AuthorizationPolicy` with JWT validation
- **Cilium**: Use Cilium Network Policy with L7 rules

**Status**: Documented pattern only. Production requires implementation.

### Rate Limiting: NOT IMPLEMENTED

Options:

- **Envoy Gateway**: Use `RateLimitFilter` with Redis backend
- **Cilium**: Use bandwidth rate limiting at CNI level
- **Controller-specific**: Each GatewayClass controller has different rate limiting

**Status**: Documented pattern only. Production requires implementation.

### Security Headers: NOT IMPLEMENTED

Gateway API does not have standardized header manipulation. Options:

- **Envoy Gateway**: Use `ResponseHeaderModifier` filter
- **Istio Gateway API**: Use EnvoyFilter or VirtualService overlay

### NetworkPolicy

The composed deployment includes an API-gateway policy and layer policies. Set `__INGRESS_NAMESPACE__` to the installed controller namespace; only that controller may enter the gateway on port 8000, and only approved internal callers may reach L1–L6.

### CORS Enforcement: NOT IMPLEMENTED

CORS must be enforced at application layer or via controller-specific policy.

### WAF / Input Validation: NOT IMPLEMENTED

No WAF rules at Gateway API layer. Requires:

- External WAF (Cloudflare, AWS WAF)
- OR Envoy Gateway WASM filters (experimental)

## Production Readiness Checklist

Before promoting from EXPERIMENTAL:

- [ ] Implement edge authentication (external auth or JWT validation)
- [ ] Implement rate limiting (per-client, per-path)
- [ ] Add security headers (HSTS, X-Frame-Options, etc.)
- [ ] Harden NetworkPolicy (remove blanket namespace allowances)
- [ ] Configure WAF or document external WAF prerequisite
- [ ] Validate TLS 1.0/1.1 rejection
- [ ] Add CI gates for all security controls

## Required Cluster Prerequisites

This stack does **not** import `../../base`. It is composed under
`k8s/deployments/prod-gateway-api/`.

## Required Cluster Prerequisites

Before deploying this routing stack, verify all prerequisites are met:

### 1. Gateway API CRDs v1.0+

```bash
# Install standard channel (recommended)
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml

# Verify CRDs are installed
kubectl get crd gateways.gateway.networking.k8s.io httproutes.gateway.networking.k8s.io
```

### 2. GatewayClass Controller

Choose and install a GatewayClass controller. The reference manifests default
to `envoy-gateway` but support `cilium`, `contour`, `istio`, or others.

| Controller    | GatewayClass Name | Installation                                                                  |
| ------------- | ----------------- | ----------------------------------------------------------------------------- |
| Envoy Gateway | `envoy-gateway`   | https://gateway.envoyproxy.io/                                                |
| Cilium        | `cilium`          | https://docs.cilium.io/en/stable/network/servicemesh/gateway-api/gateway-api/ |
| Contour       | `contour`         | https://projectcontour.io/docs/main/config/gateway-api/                       |
| Istio         | `istio`           | https://istio.io/latest/docs/tasks/traffic-management/ingress/gateway-api/    |

**To use a different controller:** Edit `gateway.yaml` and change
`spec.gatewayClassName` from `envoy-gateway` to your controller's class name.

Verify the GatewayClass exists:

```bash
kubectl get gatewayclass
# Should show your chosen class (e.g., envoy-gateway) with AGE and CONTROLLER
```

### 3. cert-manager with Gateway API Support

```bash
# Install cert-manager v1.13+ with Gateway API support
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Verify cert-manager is running
kubectl get pods -n cert-manager

# If using versions prior to v1.12, enable Gateway API support:
# --feature-gates=ExperimentalGatewayAPISupport=true
```

### 4. DNS Configuration

After deployment, create DNS A records pointing to the Gateway's external IP:

```bash
# Wait for Gateway to be assigned an IP
kubectl wait -n value-fabric gateway/value-fabric-gateway --for=condition=Programmed

# Get the external IP
kubectl get gateway -n value-fabric value-fabric-gateway -o jsonpath='{.status.addresses[0].value}'

# Create one DNS A record:
# app.value-fabric.example.com -> <GATEWAY_IP>
```

## Apply

```bash
kustomize build k8s/deployments/prod-gateway-api | kubectl apply -f -
```

## Validation

```bash
kustomize build k8s/deployments/prod-gateway-api | \
  kubeconform -strict -summary \
    -schema-location default \
    -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
    -

kubectl -n value-fabric get gateway,httproute,certificate
make production-edge-smoke APPLICATION_URL=https://<your-host>
# If edge authentication requires credentials, set EDGE_SMOKE_AUTHORIZATION
# (for example, "Bearer ...") or EDGE_SMOKE_COOKIE in the environment.
```

## Troubleshooting

### Gateway `Programmed: False` or `Programmed: Unknown`

The GatewayClass controller is not installed or not watching this namespace:

```bash
# Check GatewayClass exists
kubectl get gatewayclass

# Check Gateway status for details
kubectl describe gateway -n value-fabric value-fabric-gateway

# Verify controller pods are running (example for envoy-gateway)
kubectl get pods -n envoy-gateway-system

# Common fix: Install the GatewayClass controller for your chosen implementation
```

### HTTPRoute `Accepted: False`

Backend Service does not exist or cross-namespace references are not allowed:

```bash
# Verify Services exist
kubectl get services -n value-fabric

# Check the same-origin HTTPRoute status
kubectl describe httproute -n value-fabric application

# Verify the env overlay rendered the internal gateway and frontend Services
kustomize build k8s/deployments/prod-gateway-api | grep -A5 "kind: Service"
```

### Certificate not issuing (TLS secrets not created)

```bash
# Check Certificate status
kubectl describe certificate -n value-fabric frontend-tls

# Verify cert-manager is running
kubectl get pods -n cert-manager

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Common fix: Ensure cert-manager has Gateway API support enabled
```

### Sentinel `__HOST__` visible in cluster

The Kustomize `replacements:` did not run. This happens when the deployment overlay
is not used directly:

```bash
# Always use the deployment overlay, not the routing stack directly
# WRONG: kustomize build k8s/routing/gateway-api
# CORRECT: kustomize build k8s/deployments/prod-gateway-api
```

### DNS not resolving

```bash
# Get the actual Gateway IP
kubectl get gateway -n value-fabric value-fabric-gateway -o jsonpath='{.status.addresses[0].value}'

# Verify the application DNS record
nslookup app.value-fabric.example.com

# If using LoadBalancer, ensure the Service type is correct
kubectl get service -n envoy-gateway-system  # (or your controller's namespace)
```
