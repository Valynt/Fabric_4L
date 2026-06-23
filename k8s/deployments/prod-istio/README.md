# Deployment: prod-istio

> **Status: production-capable when operator prerequisites are satisfied.**
> Requires Istio service mesh, sidecar injection, and TLS secret prerequisites.

Composes `envs/prod` + `routing/istio`.

## Apply (operator opt-in)

```bash
# Install Istio and label the namespace for sidecar injection first.
kustomize build k8s/deployments/prod-istio | kubectl apply -f -
```

## Hosts

| Field | Value |
|---|---|
| Frontend host | `www.valuepact.ai` |
| API host | `api.valuepact.ai` |

## Validation

```bash
kustomize build k8s/deployments/prod-istio | kubeconform -strict -summary \
  -schema-location default \
  -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
  -
```

## Required cluster prerequisites

See `k8s/routing/istio/README.md`.
