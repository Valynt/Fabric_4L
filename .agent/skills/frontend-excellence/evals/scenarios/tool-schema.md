# Scenario: Precise Tool Schema Design

**Skill rule under test:** tool schemas must be precise and scoped — strict
input typing, `additionalProperties: false`, explicit outputs, tenant derived
from auth context, not requested from the agent. This is the #1 failure point.

## RED expectation (no skill)

Agent writes a loose schema with open-ended string fields, no enums, no
`additionalProperties: false`, and asks the agent for a `tenant_id` in the
inputs. Rationalizations captured verbatim.

## GREEN expectation (with skill)

Agent scopes the tool to one action, types every field (enum/format/example),
sets `additionalProperties: false`, declares a distinguishable error shape with
a machine-readable code, and derives tenant from auth context. It validates the
schema with the same validator the backend uses.

## Prompt

IMPORTANT: This is a real task. Do the actual work, don't theorize.

You are designing the agent→backend tool layer for a multi-tenant audit
service. The agent's job is to trigger repo audits. Backend enforces tenant
isolation from the authenticated context.

Write the JSON Schema for the agent tool that creates an audit run. Keep it
under 40 lines. Show the actual schema you'd ship.
