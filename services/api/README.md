# API Gateway

Shared auth enforcement and request routing for all Value Fabric services.

## Port

No dedicated public port; runs as a sidecar or ingress component depending on
deployment topology.

## Responsibilities

- JWT/API-key validation
- Tenant context extraction and propagation
- Rate limiting
- Request routing to upstream layers

## Local development

The gateway is typically exercised through \`docker-compose.full.yml\` or via
the frontend dev server proxy.
