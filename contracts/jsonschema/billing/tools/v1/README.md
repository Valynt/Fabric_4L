# Billing Tool Schemas

## Scope
JSON Schema contracts for Billing agent tools (input/output schemas consumed by Layer 4 LangGraph tool definitions).

## Owner
platform/billing

## Authoring Direction
`SCHEMA_FIRST` — Tool schemas are authored by hand in this directory. LangGraph tool definitions and any generated TypeScript tool-call types are derived from these schemas.

## Compatibility
Default: `ADDITIVE_WITHIN_MAJOR`. No breaking changes within a major version.
