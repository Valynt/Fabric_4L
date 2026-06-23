# Deployment: prod-gateway-api (Conditionally Supported)

> **Status: Conditionally Supported.** Ready for production use when all
> prerequisites are met. Requires cluster-specific Gateway API controller and
> CRDs that must be installed by the cluster operator before deployment.
>
> **Default Path:** Use `prod-nginx` for the standard production deployment.
> Use `prod-gateway-api` only when Gateway API is your preferred ingress solution.

Composes `envs/prod` + `routing/gateway-api`.

## Prerequisites Checklist

Before deploying, verify all prerequisites:

```bash
# 1. Gateway API CRDs are installed
kubectl get crd gateways.gateway.networking.k8s.io httproutes.gateway.networking.k8s.io

# 2. GatewayClass exists (default: envoy-gateway)
kubectl get gatewayclass

# 3. cert-manager is running with Gateway API support
kubectl get pods -n cert-manager

# 4. (Optional) Choose your GatewayClass controller
# Edit gateway.yaml to change spec.gatewayClassName if not using envoy-gateway
```

## Apply

```bash
# Install Gateway API CRDs and a controller first, then:
kustomize build k8s/deployments/prod-gateway-api \
  --load-restrictor=LoadRestrictionsNone | kubectl apply -f -
```

## Hosts

| Field | Value |
|---|---|
| Frontend host | `www.valuepact.ai` |
| API host | `api.valuepact.ai` |

Edit `hostname-config.yaml` to change these values before deployment.

## GatewayClass Configuration

The default GatewayClass is `envoy-gateway`. To use a different controller:

```bash
# Option 1: Edit gateway.yaml directly (permanent)
sed -i 's/gatewayClassName: envoy-gateway/gatewayClassName: your-class/' \
  k8s/routing/gateway-api/gateway.yaml

# Option 2: Use a Kustomize patch (recommended for GitOps)
cat > k8s/deployments/prod-gateway-api/gatewayclass-patch.yaml << 'EOF'
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: value-fabric-gateway
spec:
  gatewayClassName: your-class  # e.g., cilium, contour, istio
EOF

# Then add to kustomization.yaml patches:
# patches:
#   - path: gatewayclass-patch.yaml
```

## Validation

### Schema Validation (CI/CD)

```bash
# Validate with CRD catalog (ignores missing Gateway API schemas in default set)
kustomize build k8s/deployments/prod-gateway-api --load-restrictor=LoadRestrictionsNone | \
  kubeconform -strict -summary \
    -schema-location default \
    -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
    -
```

### Post-Deployment Verification

```bash
# Verify Gateway is programmed (assigned an IP)
kubectl wait -n value-fabric gateway/value-fabric-gateway --for=condition=Programmed --timeout=120s

# Check Gateway status
kubectl get gateway -n value-fabric value-fabric-gateway

# Verify HTTPRoutes are accepted
kubectl get httproute -n value-fabric

# Check TLS Certificates
kubectl get certificate -n value-fabric

# Verify DNS resolves
nslookup www.valuepact.ai
nslookup api.valuepact.ai
```

## Troubleshooting

See `k8s/routing/gateway-api/README.md` for detailed troubleshooting steps for:
- Gateway `Programmed: False`
- HTTPRoute `Accepted: False`
- Certificate not issuing
- DNS not resolving

## Required Cluster Prerequisites

Full prerequisite documentation: `k8s/routing/gateway-api/README.md`

Summary:
1. Gateway API CRDs v1.0+ installed
2. GatewayClass controller installed (envoy-gateway, cilium, contour, or istio)
3. cert-manager v1.13+ with Gateway API support
4. DNS A records pointing to Gateway external IP
