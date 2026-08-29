# Billing Provider Observation Schemas

## Scope
JSON Schema contracts for normalized observations from external billing providers (e.g., Stripe, Chargebee, Paddle). These are internal data shapes, not public API contracts.

## Owner
platform/billing

## Authoring Direction
`CODE_FIRST_WITH_GENERATED_SCHEMA` — Observations are modeled in Python Pydantic or TypeScript Zod within the billing ingestion service; schemas are generated and committed here. Do not hand-edit generated files without updating the source model and regenerating.

## Compatibility
Default: `ADDITIVE_WITHIN_MAJOR`. No breaking changes within a major version.
