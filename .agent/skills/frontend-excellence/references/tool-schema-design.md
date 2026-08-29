# Tool / Function Schema Design

**Destination:** Agent-to-backend tool calls that succeed reliably. This is the #1 failure point in agentic systems — a loose schema makes the agent hallucinate arguments; a rigid one makes it fail on legit variations.

## Principles

1. **Smallest complete scope.** Each tool does one thing. If a tool needs a "mode" enum to decide behavior, split it.
2. **Strict input typing.** Every field has a type, optionality, description, and where possible an enum/format/example. The description tells the LLM *how to choose* the value, not just what it is.
3. **Explicit outputs.** Declare the success shape and a distinguishable error shape. Include a machine-readable error code, not prose.
4. **Fail closed on validation.** Unknown enum values, wrong types, or missing required fields → structured rejection. Never silently coerce.
5. **Deterministic contracts.** The backend tool/endpoint validates against the exact same JSON Schema that was shipped to the model. One source of truth.
6. **Tenant-scoped.** Tool inputs must never ask the agent for a tenant ID; the service derives it from auth context.

## Schema Template

See `templates/tool-schema.json` for the fillable template. Key fields:

- `name` — verb_noun, stable (rename = breaking change for the agent's training/evals)
- `description` — WHEN to use + what it returns + when it errors
- `input_schema` — `type: object`, strict `properties`, `required`, `additionalProperties: false`
- Descriptions per property that include acceptable values and boundary rules
- `output_schema` — success shape + `error` union with `code`, `message`

## Common Failure

**Open-ended description or weakly typed inputs.** e.g. `"analysis_notes": "string"` — the agent fills it with prose the backend can't parse, or omits fields the validator requires, producing a 422. The fix is a scoped enum/union with exact allowed values and an example.

## Verification

- Parse every tool schema with the same validator the backend uses (Pydantic/JSON Schema).
- Run the eval suite (`evals/README.md`) before/after any schema change — schemas are part of the prompt surface.
- Backend tool registry sync: run `tool-contract-sync` skill when adding/changing tools.