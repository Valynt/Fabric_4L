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
helm install fabric ./fabric-chart -f values-prod.yaml
```

## Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.environment` | Deployment environment | `dev` |
| `global.imageRegistry` | Container registry | `""` |
| `services.layer1.enabled` | Enable Layer 1 | `true` |
| `services.layer1.replicaCount` | Layer 1 replicas | `2` |
| `services.layer4.resources.limits.memory` | Layer 4 memory limit | `4Gi` |

## Services

- **L1**: Ingestion (port 8001)
- **L2**: Extraction (port 8002)
- **L3**: Knowledge Graph (port 8003)
- **L4**: Agents (port 8004)
- **L5**: Ground Truth (port 8005)
- **L6**: Benchmarks (port 8006)
- **Billing**: Billing (port 8007)
