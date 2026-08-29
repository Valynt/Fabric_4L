# Billing Event Schemas

## Scope
JSON Schema contracts for Billing domain events (event data payloads carried inside the common event envelope).

## Owner
platform/billing

## Authoring Direction
`SCHEMA_FIRST` — Event schemas are authored by hand in this directory. Producers and consumers must validate payloads against the published schema version.

## Compatibility
Default: `ADDITIVE_WITHIN_MAJOR`. No breaking changes within a major version.
