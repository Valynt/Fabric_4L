# Service Routing and API Version Matrix

> **Audit note (2026-07-18):** The external-port column is misleading for Layer 1, Layer 2, and Layer 4, which are shown as `8000`. The canonical localhost/service ports are 8001 (L1), 8002 (L2), 8003 (L3), 8004 (L4), 8005 (L5), and 8006 (L6). The `8000` entries may reflect container-internal ports in some compose overlays, not the external developer-facing ports. Clarify the distinction before using this matrix for routing configuration.

This document is the canonical routing and API version reference for all Value Fabric layers.

Use this matrix when configuring:
- ingress/gateway routing
- service-to-service URLs
- frontend API environment variables
- contract tests for base-path drift

## Canonical matrix

| Layer | External port | Internal service DNS | Base path prefix | Auth expectations |
|---|---:|---|---|---|
| Layer 1 Ingestion | `8000` | `layer1-ingestion.value-fabric.svc.cluster.local:8000` | mixed: `/api/v1`, `/v1`, and `/api` admin routes | service auth required for production; browser clients use session cookie + CSRF for mutating calls |
| Layer 2 Extraction | `8000` | `layer2-extraction.value-fabric.svc.cluster.local:8000` | `/v1` (plus `/health`) | service auth required for production; browser clients use session cookie + CSRF for mutating calls |
| Layer 3 Knowledge | `8003` | `layer3-knowledge.value-fabric.svc.cluster.local:8003` | mostly `/v1` (plus `/health`, `/graph`, `/entities/*`) | service auth required for production; browser clients use session cookie + CSRF for mutating calls |
| Layer 4 Agents | `8000` | `layer4-agents.value-fabric.svc.cluster.local:8000` | mixed root + `/v1` | OIDC/session auth for user routes; service auth for internal calls; CSRF for mutating browser calls |
| Layer 5 Ground Truth | `8005` | `layer5-ground-truth.value-fabric.svc.cluster.local:8005` | `/api/v1` | service auth required for production; browser clients use session cookie + CSRF for mutating calls |
| Layer 6 Benchmarks | `8006` | `layer6-benchmarks.value-fabric.svc.cluster.local:8006` | `/v1` (plus `/health`) | service auth required for production; browser clients use session cookie + CSRF for mutating calls |

## Frontend environment naming alignment

The frontend must use terminology that mirrors this matrix:

- `VITE_API_VERSION_PREFIX` (default: `/api/v1`) for the shared gateway base prefix.
- `VITE_LAYER1_ROUTE_PREFIX` ... `VITE_LAYER6_ROUTE_PREFIX` for per-layer route segments.

Current defaults used by the web app:

- L1: `/ingest`
- L2: `/extract`
- L3: `/graph`
- L4: `/agents`
- L5: `/truths`
- L6: `/benchmarks`

## Notes

- OpenAPI contract tests in `apps/web/src/api/__tests__/contract/` enforce base-path expectations against checked-in fixtures in `contracts/openapi/`.
- When a layer changes externally visible path versioning (`/v1` vs `/api/v1`), update this file first, then update service READMEs, frontend config comments, and contract tests in the same change.
