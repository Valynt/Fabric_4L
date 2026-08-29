# Billing Command Schemas

## Scope
JSON Schema contracts for Billing command payloads (CQRS-style commands sent to command handlers).

## Owner
platform/billing

## Authoring Direction
`SCHEMA_FIRST` — Command schemas are authored by hand in this directory. Command handlers and API route DTOs are derived from these schemas.

## Compatibility
Default: `ADDITIVE_WITHIN_MAJOR`. No breaking changes within a major version.
