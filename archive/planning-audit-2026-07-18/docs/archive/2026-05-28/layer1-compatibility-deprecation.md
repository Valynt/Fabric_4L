# Layer 1 Compatibility Routes and Legacy Frontend Aliases

## Scope

This document tracks temporary compatibility surfaces that must be removed after usage verification.

## Backend compatibility routes

| Route | Canonical replacement | Telemetry status | Deprecation status | Target removal date |
|---|---|---|---|---|
| `POST /v1/ingest` | `POST /api/v1/ingestion/targets` and related `/api/v1/ingestion/*` routes | Emits `layer1_compatibility_route_accessed` structured log event | Deprecated | 2026-07-15 |
| `POST /api/v1/ingestion/sources` | Canonical ingestion source route in Layer 1 contract | Emits `layer1_compatibility_route_accessed` structured log event | Deprecated | 2026-07-15 |
| `GET /api/v1/ingestion/sources/{source_id}` | Canonical ingestion source read route in Layer 1 contract | Emits `layer1_compatibility_route_accessed` structured log event | Deprecated | 2026-07-15 |

All compatibility endpoints now return deprecation headers:

- `Deprecation: true`
- `Sunset: 2026-07-15`
- `Link: </api/v1/ingestion>; rel="successor-version"`

## Frontend route aliases

| Alias route | Canonical route | Status |
|---|---|---|
| `/context/command-center` | `/command-center` | Removed in this slice |

## Slice-based removal plan

1. Add telemetry and deprecation headers (completed in this slice).
2. Observe usage in production logs for one release window.
3. Remove one alias/endpoint per slice after confirmed inactivity.
4. Preserve canonical route behavior with contract tests on each slice.
