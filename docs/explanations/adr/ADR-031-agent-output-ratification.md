# ADR-031: Agent Output Shape and Traceability Contract Ratification

## Status: ACCEPTED

Date: 2026-07-10  
Author: Platform Engineering Staff  
Approver: Architecture Review Board  
Supersedes: ADR-016 (JSON Mode Output), ADR-018 (Raw Text Parsing)

---

## Context

### The Problem

Agent outputs in Fabric 4L are consumed by downstream services, stored for audit, rendered in the UI, and used as inputs to subsequent agent runs. Without a canonical output shape, every integration point requires custom parsing, error handling is inconsistent, and observability is fragmented. The current state is a patchwork of three competing patterns, each with distinct failure modes.

**Pattern A: JSON Mode with Post-Hoc Parsing** (used in `services/orchestrator/src/agents/`, `services/web/src/api/agents.ts`)
Agents are configured with `response_format: { type: "json_object" }` and downstream code calls `JSON.parse(response.choices[0].message.content)` to extract structured data. This pattern has three critical flaws: (1) `json_object` mode guarantees valid JSON but not valid schema — fields may be missing, types may be wrong; (2) `JSON.parse()` on unsanitized LLM output has caused prototype pollution incidents when the model emitted `__proto__` keys; (3) parsing errors surface as generic `SyntaxError`, losing the context needed for debugging.

**Pattern B: Raw Text with Regex Extraction** (used in `tools/legacy-agents/`, `services/analytics/src/nl-to-sql.ts`)
Agents generate raw text; downstream code applies regular expressions or string splitting to extract structured data. This is the least reliable pattern: regexes break when the model changes output formatting (e.g., switching from bullet points to numbered lists), and extraction failures are silent data corruption rather than explicit errors. In May 2026, a change in model behavior caused the `nl-to-sql` agent to wrap SQL in markdown code fences; the extraction regex did not account for this, and malformed SQL was executed against production databases.

**Pattern C: Ad-Hoc Structured Output per Agent** (historical example: `services/billing/src/agents/invoice-agent.ts` — legacy `services/billing/` package removed 2026-08-27, COMPAT-BILL-001; retain the pattern's lesson, not the path)
Each agent defines its own output structure without platform-level consistency. One agent returns `{ result: T, confidence: number }`; another returns `{ data: T, status: "ok" }`; a third returns `{ output: T }`. Consumers must write custom parsers for each agent. The platform cannot provide generic tooling for output validation, retry, or audit because there is no common contract.

### Operational Impact

| Incident ID | Root Cause | Date |
|-------------|-----------|------|
| INC-2026-0115 | `JSON.parse()` on LLM output with `__proto__` key caused prototype pollution in result cache | 2026-01-15 |
| INC-2026-0305 | Agent output changed shape on model version bump; downstream parser failed; 400 errors for 6 hours | 2026-03-05 |
| INC-2026-0520 | `nl-to-sql` regex extraction broke on markdown code fences; malformed SQL executed | 2026-05-20 |
| INC-2026-0625 | Missing `confidence` field in agent output caused division by zero in downstream aggregator | 2026-06-25 |

### Current Output Shape Landscape

| Agent | Output Pattern | Has Schema | Has Validation | Has Retry | Has Audit |
|-------|---------------|-----------|---------------|-----------|-----------|
| `analytics-agent` | JSON mode + parse | No | No | No | Partial |
| `workflow-agent` | Raw text + regex | No | No | No | No |
| `invoice-agent` | Ad-hoc struct | Yes (inline) | No | No | Yes |
| `support-agent` | JSON mode + parse | No | No | No | Partial |
| `orchestrator` | Mixed | No | No | No | Yes |

None of the 12 production agents comply with all five requirements: schema-defined output, runtime validation, retry on validation failure, complete audit trail, and trace correlation.

### Decision Forces

1. **Schema enforcement:** Agent outputs must conform to a predefined schema, validated at generation time and checked at runtime.
2. **Structured generation:** Use function-calling / tool-use mode with Pydantic/Zod schemas, not `json_object` mode or raw text.
3. **Canonical envelope:** All outputs wrap business data in a standardized envelope with status, metadata, and traceability fields.
4. **Retry with backoff:** Validation failures trigger structured retry (max 2 attempts) before returning a typed default or error.
5. **Full audit trail:** Every output is persisted with session ID, trace ID, input hash, and output JSON.
6. **Model version pinning:** Exact model versions prevent silent behavior changes.
7. **Raw text isolation:** Raw text generation is permitted only for explicitly marked conversational endpoints.
8. **PII protection:** Raw prompts and completions are never logged; only structured outputs with sanitized metadata are stored.

---

## Decision

We will adopt a **single canonical pattern: Structured Generation with Pydantic Schema Enforcement and OpenTelemetry Tracing**. All agent outputs are produced through function-calling/tool-use mode with a defined Pydantic/Zod schema. Raw text generation is restricted to endpoints explicitly marked `output_mode: "text"`. Every output follows the canonical `AgentOutput<T>` envelope.

### Specification

#### 1. Output Mode

| Mode | When to Use | How |
|------|------------|-----|
| `structured` (default) | All production agents | Function-calling with Pydantic/Zod schema |
| `text` | Conversational endpoints only | Raw text with `output_mode: "text"` declaration |

Structured generation uses the LLM's native function-calling API (OpenAI `tools`, Anthropic `tool_use`, Gemini `function_declarations`). The schema is passed as the tool definition; the model's tool call argument is the structured output. This provides schema enforcement at generation time — the model is constrained to produce valid JSON matching the schema.

#### 2. Schema Definition

Each agent defines its output as a Pydantic model (Python) or Zod schema (TypeScript):

**TypeScript (Zod):**
```typescript
// agents/analytics/output-schema.ts
import { z } from "zod";

export const AnalyticsOutputSchema = z.object({
  summary: z.string().min(1).describe("Executive summary of the analysis"),
  insights: z.array(z.object({
    title: z.string(),
    description: z.string(),
    confidence: z.number().min(0).max(1),
    supporting_data: z.record(z.unknown()),
  })).max(10),
  recommended_actions: z.array(z.string()).max(5),
  query_used: z.string().describe("The SQL query executed to produce this analysis"),
});

export type AnalyticsOutput = z.infer<typeof AnalyticsOutputSchema>;
```

**Python (Pydantic):**
```python
# agents/analytics/output_schema.py
from pydantic import BaseModel, Field
from typing import List

class Insight(BaseModel):
    title: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_data: dict

class AnalyticsOutput(BaseModel):
    summary: str = Field(min_length=1, description="Executive summary of the analysis")
    insights: List[Insight] = Field(max_length=10)
    recommended_actions: List[str] = Field(max_length=5)
    query_used: str = Field(description="The SQL query executed to produce this analysis")
```

#### 3. Canonical Agent Output Envelope

All agent outputs are wrapped in the canonical `AgentOutput<T>` envelope:

```typescript
interface AgentOutput<T> {
  // Business result — the agent's actual output, validated against schema
  result: T;

  // Optional chain-of-thought summary for debugging and auditing
  reasoning?: string;

  // Record of all tool calls made during this agent run
  tool_calls: ToolCall[];

  // Model's confidence in the overall result (0.0 - 1.0)
  confidence: number;

  // Trace correlation
  trace_id: string;
  session_id: string;

  // Execution metadata
  metadata: {
    model: string;                    // e.g., "gpt-4o"
    model_version: string;            // e.g., "2024-08-06" — pinned
    latency_ms: number;               // Total wall-clock time
    token_usage: {
      prompt: number;
      completion: number;
      total: number;
    };
    validation_passed: boolean;       // Did output pass schema validation?
    retry_count: number;              // 0, 1, or 2
    finish_reason: string;            // "stop", "tool_calls", "length", etc.
  };
}

interface ToolCall {
  tool_name: string;
  input_hash: string;                // SHA-256 of canonicalized input JSON
  output_status: "success" | "error" | "partial";
  latency_ms: number;
  span_id: string;
}
```

#### 4. Validation and Retry Policy

```typescript
async function generateStructuredOutput<T>(
  config: AgentConfig<T>,
  input: AgentInput,
): Promise<AgentOutput<T>> {
  const maxRetries = 2;
  let lastError: ValidationError | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const response = await llmClient.chat.completions.create({
      model: config.model,
      tools: [{ type: "function", function: { name: "output", parameters: zodToJsonSchema(config.outputSchema) } }],
      tool_choice: { type: "function", function: { name: "output" } },
      messages: buildMessages(input, attempt > 0 ? lastError : undefined),
    });

    const toolCall = response.choices[0].message.tool_calls?.[0];
    if (!toolCall) {
      lastError = new ValidationError("Model did not produce tool call");
      continue;
    }

    try {
      const parsed = config.outputSchema.parse(JSON.parse(toolCall.function.arguments));
      return buildAgentOutput(parsed, response, attempt);
    } catch (error) {
      lastError = error instanceof z.ZodError
        ? new ValidationError(`Schema validation failed: ${error.message}`)
        : new ValidationError(`Parse error: ${error}`);

      // Include validation error in next attempt's prompt for correction
      if (attempt < maxRetries) {
        telemetry.recordEvent("agent.output.validation_retry", {
          agent_id: config.id,
          attempt,
          error: lastError.message,
        });
      }
    }
  }

  // All retries exhausted — return typed default or error envelope
  return buildErrorOutput(lastError!, config);
}
```

#### 5. Session Management and Traceability

- **Session ID:** Passed via `x-fabric-session-id` header. Persists across multiple agent runs in a conversation.
- **Trace ID:** Generated per agent run. Each agent run is a single trace; phases (planning, tool selection, execution, validation) are spans within that trace.
- **State changes:** Recorded as OpenTelemetry span events with timestamp and state diff.
- **Persistence:** Every `AgentOutput` is stored in the audit database with:
  - `session_id`, `trace_id`, `input_hash` (SHA-256 of canonicalized input)
  - Full output JSON
  - Model version and finish reason
  - Token usage (for cost tracking)

#### 6. Model Version Pinning

Agent configurations specify exact model versions:

```yaml
# config/agents/analytics-agent.yaml
agent:
  name: analytics
  model: gpt-4o
  model_version: "2024-08-06"  # Pinned — changing this requires PR review
  output_mode: structured
  output_schema: agents/analytics/output-schema.ts
  max_retries: 2
```

Model version changes require a configuration PR with:
- Updated `model_version` field
- Regression test results comparing outputs on a golden test set
- Approval from ML platform team

#### 7. Raw Text Isolation

Endpoints using raw text generation must explicitly declare:

```typescript
const chatAgent = defineAgent({
  name: "chat",
  model: "gpt-4o",
  output_mode: "text",  // Required declaration
  // No output_schema — schema validation is skipped
});
```

The platform logs a warning when `output_mode: "text"` is used and requires a justification comment in the agent definition. Text-mode agents do not participate in downstream structured processing; their outputs are rendered directly to users.

### Why Structured Generation over alternatives

| Alternative | Reason for rejection |
|-------------|---------------------|
| `json_object` mode | No schema enforcement; valid JSON but invalid structure; no field-level constraints |
| Raw text + regex | Fragile, breaks on model behavior changes, silent data corruption |
| Constrained decoding (CFG, GBNF) | Excellent for syntax but complex to implement; limited model support |
| Post-hoc LLM validation | Adds latency, cost, and failure surface; not deterministic |
| Manual template filling | Inflexible, requires template maintenance per use case |

Function-calling with Pydantic/Zod schemas is supported by all major model providers, provides schema-level validation at generation time, and integrates cleanly with our existing TypeScript/Python type systems.

---

## Consequences

### Positive

- **Schema enforcement:** Outputs are guaranteed to match the expected shape. Missing fields, wrong types, and out-of-range values are caught at generation time or by runtime validation.
- **Retry resilience:** Up to 2 validation retries with feedback means transient schema failures (model hallucinations) are automatically recovered without user-visible errors.
- **Complete audit trail:** Every output is stored with full traceability. Debugging, compliance auditing, and output replay are all supported.
- **Cost visibility:** Token usage per agent run is tracked, enabling per-tenant cost allocation and optimization.
- **Model version safety:** Pinned versions prevent silent behavior changes. Version bumps require explicit approval and regression testing.
- **Downstream simplicity:** All consumers use the same `AgentOutput<T>` envelope. Generic UI components, logging, and metrics work across all agents.
- **PII protection:** Only structured, validated outputs are stored. Raw prompts and completions are never persisted.
- **Observability:** OpenTelemetry traces provide per-phase latency, tool call history, and validation outcomes for every agent run.

### Negative

- **Latency:** Schema validation and retry logic add ~50-200ms per agent run. This is offset by reduced downstream parsing failures and eliminated regex maintenance.
- **Schema maintenance:** Output schemas must be kept in sync with evolving business requirements. Schema changes require corresponding changes to the agent definition and regression tests.
- **Model provider compatibility:** Not all models support function-calling with the same fidelity. We maintain a capability matrix and fallback to `json_object` + Pydantic validation for models without native tool use.
- **Migration cost:** 12 production agents must be migrated from their current output patterns. Each requires schema definition, regression testing, and consumer updates.
- **Reasoning field size:** The `reasoning` field can grow large for complex agent runs. We cap it at 10KB and truncate with a "..." indicator.

---

## Compliance

### Automated Enforcement (Three Layers)

**IDE / Local Development:**
- ESLint rule `no-json-parse-agent-output`: Error on `JSON.parse()` calls on LLM response variables.
- ESLint rule `no-regex-extract-llm`: Error on regex operations on LLM response text.
- TypeScript: `defineAgent()` generic requires `outputSchema` when `output_mode` is `"structured"` (default).

**Pre-commit:**
- `lint-staged` runs ESLint on changed files.
- `agent-output-check` warns if an agent definition lacks `outputSchema` or `model_version`.

**CI Gate:**
- `check_agent_output` job runs on every PR:
  - ESLint rules are errors
  - All `defineAgent()` calls have `outputSchema` (structured mode) or explicit `output_mode: "text"`
  - All agents specify pinned `model_version`
  - Golden test regression: agent outputs on a fixed test set must match approved snapshots
  - Audit persistence test: every agent run result is queryable in audit database

### Runtime Enforcement
- `generateStructuredOutput()` rejects calls without a schema when `output_mode` is structured.
- Validation failures trigger retry (max 2); after exhaustion, a typed error envelope is returned.
- Model version mismatch (API returns different version than requested) logs a critical warning.
- All outputs are persisted to the audit database before being returned to the caller.

### Manual Verification
- Quarterly review: 3 random agents audited for schema completeness and description quality.
- Security audit: verify no raw prompts/completions in application logs.

---

## Migration

### Timeline

| Phase | Version | Date | Behavior |
|-------|---------|------|----------|
| Soft deprecation | v1.2.0 | 2026-07-10 | ESLint warnings, `defineAgent()` available, new agents use structured output |
| Hard enforcement | v1.3.0 | 2026-10-10 | ESLint errors, CI fails, all agents must use `defineAgent()` with schema or explicit text mode |
| Removal | v1.4.0 | 2027-01-10 | Legacy agent constructors removed, all agents must comply |

### Codemod: `migrate-agent-output`

```bash
npx @fabric/codemod migrate-agent-output --target ./services/orchestrator/src/agents --write
```

**Before (JSON mode + manual parse):**
```typescript
// services/orchestrator/src/agents/analytics-agent.ts
const analyticsAgent = {
  name: "analytics",
  model: "gpt-4o",
  generate: async (query: string) => {
    const response = await openai.chat.completions.create({
      model: "gpt-4o",
      response_format: { type: "json_object" },
      messages: [{ role: "user", content: `Analyze: ${query}` }],
    });
    // NO SCHEMA VALIDATION — raw parse
    const parsed = JSON.parse(response.choices[0].message.content!);
    return parsed;  // Could be any shape
  },
};
```

**After (structured generation with schema):**
```typescript
// agents/analytics-agent.ts
import { defineAgent } from "@fabric/platform/agents";
import { AnalyticsOutputSchema } from "./analytics/output-schema";

export const analyticsAgent = defineAgent({
  name: "analytics",
  model: "gpt-4o",
  model_version: "2024-08-06",
  outputSchema: AnalyticsOutputSchema,
  generate: async (input, context) => {
    // Structured generation — schema enforced by model + runtime validation
    const output = await context.generateStructured({
      messages: [{ role: "user", content: `Analyze: ${input.query}` }],
    });
    return output.result;  // Typed as AnalyticsOutput
  },
});
```

**Before (raw text + regex extraction):**
```typescript
// services/analytics/src/nl-to-sql.ts
async function naturalLanguageToSql(nlQuery: string): Promise<string> {
  const response = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: [
      { role: "system", content: "Convert to SQL. Return only the query." },
      { role: "user", content: nlQuery },
    ],
  });
  const text = response.choices[0].message.content!;
  // Fragile regex extraction
  const match = text.match(/SELECT\s+.*;/is);
  return match ? match[0] : text;  // Silent failure on format change
}
```

**After (structured generation):**
```typescript
// agents/nl-to-sql-agent.ts
import { defineAgent } from "@fabric/platform/agents";
import { z } from "zod";

const SqlOutputSchema = z.object({
  sql: z.string().describe("The generated SQL query"),
  explanation: z.string().describe("Explanation of what the query does"),
  tables_used: z.array(z.string()).describe("Tables referenced in the query"),
});

export const nlToSqlAgent = defineAgent({
  name: "nl_to_sql",
  model: "gpt-4o",
  model_version: "2024-08-06",
  outputSchema: SqlOutputSchema,
  generate: async (input, context) => {
    return context.generateStructured({
      messages: [
        { role: "system", content: "Convert natural language to SQL." },
        { role: "user", content: input.nlQuery },
      ],
    });
  },
});
```

### Agent-by-Agent Rollout

| Agent | Pattern Before | Migration Effort | Owner | Target Completion |
|-------|---------------|-----------------|-------|-------------------|
| `analytics-agent` | JSON mode + parse | Medium (define schema) | @team-data | 2026-08-30 |
| `workflow-agent` | Raw text + regex | High (schema + consumers) | @team-agents | 2026-09-15 |
| `invoice-agent` | Ad-hoc struct | Low (wrap in envelope) | @team-billing | 2026-08-01 |
| `support-agent` | JSON mode + parse | Medium (define schema) | @team-support | 2026-08-30 |
| `orchestrator` | Mixed | High (refactor core) | @team-platform | 2026-09-30 |

### Checklist Per Agent

- [ ] Define output schema (Zod/Pydantic) with field descriptions
- [ ] Replace `JSON.parse()` or regex extraction with `defineAgent()` + `generateStructured()`
- [ ] Add `model_version` pin to agent configuration
- [ ] Ensure `tool_calls` are recorded in output
- [ ] Update all consumers to use `AgentOutput<T>` envelope
- [ ] Add golden test snapshots for regression testing
- [ ] Verify audit persistence: outputs stored with session/trace IDs
- [ ] Run integration tests: all agent runs return valid envelope
- [ ] Tag PR with `contract-adr-031`

---

## Appendix: Agent Output Envelope (Full TypeScript)

```typescript
// platform/agents/types.ts
interface AgentOutput<T> {
  result: T;
  reasoning?: string;
  tool_calls: ToolCall[];
  confidence: number;
  trace_id: string;
  session_id: string;
  metadata: AgentMetadata;
}

interface ToolCall {
  tool_name: string;
  input_hash: string;
  output_status: "success" | "error" | "partial";
  latency_ms: number;
  span_id: string;
}

interface AgentMetadata {
  model: string;
  model_version: string;
  latency_ms: number;
  token_usage: TokenUsage;
  validation_passed: boolean;
  retry_count: number;
  finish_reason: string;
}

interface TokenUsage {
  prompt: number;
  completion: number;
  total: number;
}
```

---

## References

- CONTRACT.md Section 2.5: Agent Output Shape and Traceability
- ADR-028: Tenant Context Propagation Contract Ratification
- ADR-033: Tool Invocation Boundary Contract Ratification
- `examples/canonical/agent/orchestrator.ts`: Reference implementation
- `test/agent-output-validation.spec.ts`: Compliance test
- INC-2026-0115, INC-2026-0305, INC-2026-0520, INC-2026-0625: Incident reports
