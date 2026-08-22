# Fabric_4L Helm Chart

Helm chart for deploying the Fabric_4L platform on Kubernetes.

## Prerequisites

- Kubernetes 1.27+
- Helm 3.12+
- Ingress controller (nginx) installed

## Installation

```bash
helm dependency update
helm install fabric ./fabric-chart -f values.yaml
```

## Environment Overrides

```bash
# Development
helm install fabric ./fabric-chart -f values-dev.yaml

# Production
helm install fabric ./fabric-chart -f values-prod.yaml \
  --set image.digest=sha256:<signed-image-digest>
```

## Configuration

| Parameter                                 | Description                                                                                                | Default                       |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ----------------------------- |
| `global.environment`                      | Deployment environment                                                                                     | `dev`                         |
| `global.imageRegistry`                    | Container registry                                                                                         | `""`                          |
| `image.repository`                        | Shared image repository                                                                                    | `ghcr.io/bmsull560/fabric_4l` |
| `image.tag`                               | Non-latest image tag used when `image.digest` is empty                                                     | `REQUIRED_IMAGE_TAG`          |
| `image.digest`                            | Optional sha256 digest; takes precedence over `image.tag` and is required for production policy compliance | `""`                          |
| `services.layer1.enabled`                 | Enable Layer 1                                                                                             | `true`                        |
| `services.layer1.replicaCount`            | Layer 1 replicas                                                                                           | `2`                           |
| `services.layer4.resources.limits.memory` | Layer 4 memory limit                                                                                       | `4Gi`                         |
| `ingress.application.host`                | Single public application hostname                                                                         | `app.fabric.local`            |
| `ingress.api.externalPrefix`              | Browser-visible gateway prefix                                                                             | `/api/v1`                     |
| `ingress.api.upstreamPrefix`              | Prefix forwarded to the gateway                                                                            | `/v1`                         |
| `ingress.frontend.externalPrefix`         | Frontend catch-all                                                                                         | `/`                           |

## Public routing

The chart renders two same-host NGINX Ingress resources so API rewrite and
security annotations cannot affect frontend assets:

```text
/api/v1/<path> -> <release>-fabric-4l-api:8000/v1/<path>
/<path>        -> <release>-fabric-4l-frontend:3000/<path>
```

The API path is the only public route to backend functionality. Layer 1–6
Services remain `ClusterIP` and must only be called through the API gateway or
an explicitly authorized internal workload. Override the production hostname
with `ingress.application.host`; do not configure a separate browser API host.

## Services

- **L1**: Ingestion (port 8001)
- **L2**: Extraction (port 8002)
- **L3**: Knowledge Graph (port 8003)
- **L4**: Agents (port 8004)
- **L5**: Ground Truth (port 8005)
- **L6**: Benchmarks (port 8006)
- **Billing**: Billing (port 8007)
