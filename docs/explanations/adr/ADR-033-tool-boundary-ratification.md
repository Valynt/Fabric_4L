# ADR-033: Tool Invocation Boundary Contract Ratification

## Status: ACCEPTED

Date: 2026-07-10  
Author: Platform Engineering Staff  
Approver: Architecture Review Board  
Supersedes: ADR-011 (Inline Tool Definitions), ADR-013 (Framework-Specific Tool Wrappers)

---

## Context

### The Problem

Tool definitions in Fabric 4L have proliferated across layers without a unifying contract. The same business capability — querying a database, calling an external API, performing a calculation — is implemented multiple times, each tailored to a specific agent framework's calling conventions. This duplication creates version skew, inconsistent error handling, and a combinatorial testing burden.

**Pattern A: Inline Lambda Definitions** (used in `services/orchestrator/src/agents/`, `tools/legacy/`)
Tools are defined as anonymous functions inside agent configuration objects, often hundreds of lines long, with business logic interleaved with framework-specific boilerplate. These functions are not independently testable, not discoverable by other agents, and not versioned. When the same capability is needed by a different agent, it is copy-pasted and diverges within weeks.

**Pattern B: Framework-Specific Wrappers with Duplicated Logic** (used in `integrations/langchain/`, `integrations/crewai/`, `integrations/mcp/`)
Each integration maintains its own tool definition that wraps the same underlying capability. The LangChain tool handles input parsing one way; the CrewAI tool handles it another; the MCP tool handles it a third. When a bug is fixed in one wrapper, the same bug persists in the others. The `execute_sql_query` capability currently has four separate implementations with subtly different parameter validation, timeout handling, and error formatting.

**Pattern C: Exception-Based Error Handling** (used across all integrations)
Tools throw JavaScript exceptions on failure. The calling agent catches these and attempts to interpret them, but without a structured error contract, the agent cannot distinguish between retryable failures (database timeout) and permanent failures (invalid query syntax). This leads to agents retrying non-retryable errors and giving up on retryable ones.

**Pattern D: Missing or Ambiguous Schemas** (used in ~40% of production tools)
Tools lack JSON Schema descriptions for their inputs, or the descriptions are one-line strings like "The query to execute" without specifying syntax, length limits, or expected format. LLMs selecting tools based on these descriptions make poor choices, leading to incorrect tool invocations and failed agent runs.

### Operational Impact

| Incident ID | Root Cause | Date |
|-------------|-----------|------|
| INC-2026-0210 | LangChain and CrewAI `execute_sql_query` tools had different timeout configs; CrewAI version timed out on legitimate long-running analytics query, causing agent to retry 5 times and exhaust rate limit | 2026-02-10 |
| INC-2026-0430 | Inline tool definition copy-pasted between agents had stale database table reference; one agent updated, the other queried non-existent table | 2026-04-30 |
| INC-2026-0530 | Tool threw generic `Error` on database connection failure; agent could not determine retryability, returned incorrect result to user | 2026-05-30 |
| INC-2026-0620 | LLM selected `send_email` tool for a data-analysis task because tool description was ambiguous; no guard prevented invocation with mismatched intent | 2026-06-20 |

### Current Tool Landscape

| Tool Name | LangChain | CrewAI | MCP | Inline | Canonical? |
|-----------|-----------|--------|-----|--------|------------|
| execute_sql_query | Yes | Yes | Yes | No | No — 3 variants |
| search_documentation | Yes | No | Yes | No | No — 2 variants |
| create_workflow | No | No | No | Yes | No — 2 inline copies |
| validate_schema | Yes | Yes | No | No | No — 2 variants |
| send_notification | No | Yes | No | Yes | No — fragmented |

The platform has 47 distinct tool capabilities but 89 tool implementations due to duplication across frameworks.

### Decision Forces

1. **Single source of truth:** Each business capability is implemented exactly once.
2. **Framework independence:** Tool definitions are not coupled to LangChain, CrewAI, MCP, or any other framework.
3. **Type safety:** Tool inputs and outputs are statically typed; JSON Schema is generated from types, not hand-written.
4. **Structured errors:** Tools return discriminated error objects with retryability signals, not exceptions.
5. **LLM-optimized schemas:** JSON Schema descriptions are mandatory, detailed, and tested for LLM selection accuracy.
6. **Discoverability:** All tools are registered in a central registry with metadata for discovery, permissions, and observability.
7. **Tenant isolation:** Tools automatically inherit tenant context from the orchestrating agent; no tool can access cross-tenant data.
8. **Thin bindings:** Framework bindings are auto-generated, contain zero business logic, and are at most 10 lines.

---

## Decision

We will adopt a **single canonical pattern: Schema-First Unified Tool Registry with Generated Framework Bindings**. Every tool is defined once as a strongly-typed TypeScript function with a generated JSON Schema input contract. Framework bindings are thin, auto-generated wrappers. All tools are registered in a central `ToolRegistry`.

### Specification

#### 1. Tool Definition

A tool is a TypeScript function exported from a file in `tools/` with the following structure:

```typescript
// tools/execute-sql-query.ts
import { defineTool } from "@fabric/platform/tools";
import { z } from "zod";

const inputSchema = z.object({
  query: z.string()
    .min(1)
    .max(10000)
    .describe("A single SQL SELECT statement. Must start with 'SELECT'. No DDL or DML."),
  timeout_ms: z.number()
    .int()
    .min(1000)
    .max(300000)
    .default(30000)
    .describe("Maximum execution time in milliseconds. Default 30s, max 5min."),
});

const outputSchema = z.object({
  columns: z.array(z.string()).describe("Column names from the query result"),
  rows: z.array(z.record(z.unknown())).describe("Result rows as objects"),
  row_count: z.number().describe("Total rows returned"),
});

export const executeSqlQuery = defineTool({
  name: "execute_sql_query",
  description: `
    Execute a read-only SQL query against the tenant's analytics database.
    Use this when the user asks for data analysis, counts, aggregations, or reports.
    Do NOT use this for: modifying data (use create_workflow), sending messages
    (use send_notification), or schema changes (use validate_schema).
    Example: "SELECT COUNT(*) FROM orders WHERE created_at > NOW() - INTERVAL '7 days'"
  `.trim(),
  inputSchema,
  outputSchema,
  handler: async (input, context): Promise<ToolResult<z.infer<typeof outputSchema>>> => {
    const tenantCtx = getTenantContextOrThrow();
    const db = await getDbFromContext(tenantCtx);

    const startTime = performance.now();
    try {
      const result = await db.query(input.query, { timeout: input.timeout_ms });
      return {
        status: "success",
        data: {
          columns: result.fields.map(f => f.name),
          rows: result.rows,
          row_count: result.rowCount ?? 0,
        },
        metadata: {
          execution_time_ms: Math.round(performance.now() - startTime),
          tenant_id: tenantCtx.tenant_id,
          tool_version: "2.1.0",
          trace_id: context.trace_id,
        },
      };
    } catch (error) {
      return {
        status: "error",
        error: {
          code: "QUERY_EXECUTION_ERROR",
          message: error instanceof Error ? error.message : "Unknown error",
          recoverable: isRecoverableDbError(error),
          details: { query: input.query.substring(0, 200) },
        },
        metadata: {
          execution_time_ms: Math.round(performance.now() - startTime),
          tenant_id: tenantCtx.tenant_id,
          tool_version: "2.1.0",
          trace_id: context.trace_id,
        },
      };
    }
  },
});
```

#### 2. Tool Registration

All tools are registered in a central `ToolRegistry` at application startup:

```typescript
// tools/registry.ts
import { ToolRegistry } from "@fabric/platform/tools";
import { executeSqlQuery } from "./execute-sql-query";
import { searchDocumentation } from "./search-documentation";
import { createWorkflow } from "./create-workflow";

export const toolRegistry = new ToolRegistry({
  tools: [
    executeSqlQuery,
    searchDocumentation,
    createWorkflow,
    // ... all tools
  ],
  // Validation runs at startup
  validateOnRegister: true,
  // Enforce description quality
  minDescriptionLength: 50,
  // Enforce schema field descriptions
  requireFieldDescriptions: true,
  // Max top-level parameters for LLM performance
  maxTopLevelParams: 8,
});
```

The registry performs these validations at startup:
- All tool names are unique and match `/^[a-z_][a-z0-9_]*$/`
- All descriptions are at least 50 characters
- All input schema fields have descriptions
- No more than 8 top-level parameters
- All handlers are async functions
- No handler uses `throw` (must return structured errors)

#### 3. Framework Bindings

Framework bindings are auto-generated at build time. The generator reads tool definitions from the registry and produces thin wrappers:

**Generated LangChain binding:**
```typescript
// .generated/langchain-tools/execute-sql-query.ts (AUTO-GENERATED — DO NOT EDIT)
import { executeSqlQuery } from "../../tools/execute-sql-query";

export const langchainExecuteSqlQuery = new DynamicStructuredTool({
  name: executeSqlQuery.name,
  description: executeSqlQuery.description,
  schema: executeSqlQuery.inputSchema,  // Zod schema compatible with LangChain
  func: async (input) => {
    const result = await executeSqlQuery.handler(input, {
      trace_id: getCurrentTraceId(),
      agent_id: getCurrentAgentId(),
    });
    if (result.status === "error") {
      return `Error [${result.error.code}]: ${result.error.message}`;
    }
    return JSON.stringify(result.data);
  },
});
// Lines of business logic: 0. Lines of wrapper: 8.
```

**Generated MCP binding:**
```typescript
// .generated/mcp-tools/execute-sql-query.ts (AUTO-GENERATED — DO NOT EDIT)
import { executeSqlQuery } from "../../tools/execute-sql-query";

export const mcpExecuteSqlQuery = {
  name: executeSqlQuery.name,
  description: executeSqlQuery.description,
  inputSchema: zodToJsonSchema(executeSqlQuery.inputSchema),
  handler: async (args) => {
    const result = await executeSqlQuery.handler(args, {
      trace_id: getCurrentTraceId(),
      agent_id: getCurrentAgentId(),
    });
    return {
      content: [{ type: "text", text: JSON.stringify(result) }],
    };
  },
};
// Lines of business logic: 0. Lines of wrapper: 10.
```

#### 4. Tool Output Contract

All tools return the canonical `ToolResult<T>` shape:

```typescript
interface ToolResult<T> {
  status: "success" | "error" | "partial";
  data?: T;
  error?: {
    code: string;
    message: string;
    recoverable: boolean;
    details?: Record<string, unknown>;
  };
  metadata: {
    execution_time_ms: number;
    tenant_id: string;
    tool_version: string;
    trace_id: string;
  };
}
```

- `status: "success"` — operation completed, `data` contains result
- `status: "error"` — operation failed, `error` contains structured error info
- `status: "partial"` — operation partially completed (e.g., paginated results truncated), both `data` and `error` may be present
- `error.recoverable` — `true` if retry may succeed (transient failures), `false` if retry will not help (permanent failures)

#### 5. Observability

Every tool invocation creates an OpenTelemetry span:
- Span name: `tool.<tool_name>`
- Attributes: `tool.name`, `tool.version`, `tenant.id`, `agent.id`
- Events: `tool.input_received`, `tool.execution_start`, `tool.execution_complete`
- Error spans: `tool.error` with `error.code` and `error.recoverable` attributes

#### 6. Authentication and Tenant Context

Tools do not accept `tenant_id` as a parameter. They call `getTenantContextOrThrow()` to obtain the tenant context established by the orchestrating agent. This guarantees that a tool invoked by Agent A on behalf of Tenant X cannot access Tenant Y's data, even if the LLM fabricates a different `tenant_id` in tool input.

### Why Schema-First Registry over alternatives

| Alternative | Reason for rejection |
|-------------|---------------------|
| Framework-native definitions (LangChain tools, CrewAI tools) | Locks us into vendor abstractions; duplicative across frameworks |
| gRPC/Protobuf service definitions | Overly complex for internal tool calls; schema not natively LLM-friendly |
| OpenAPI-defined tools | Good for external APIs but verbose for internal tools; harder to version per-tool |
| Plain functions with JSDoc | No runtime schema validation; LLM sees only description, not structured input contract |
| Database-stored tool definitions | Adds operational complexity; harder to code-review; no static analysis |

---

## Consequences

### Positive

- **Single implementation:** Each business capability exists in exactly one file. Bug fixes apply everywhere.
- **Framework independence:** Adding a new agent framework requires only a binding generator, not reimplementing 47 tools.
- **Type safety:** Zod schemas provide both static TypeScript types and runtime validation. JSON Schema generation ensures LLMs receive accurate input specifications.
- **Structured errors:** Agents can make intelligent decisions about retry, fallback, and user messaging based on `error.recoverable` and `error.code`.
- **Discoverability:** The central registry enables tooling: auto-generated documentation, permission matrices, dependency graphs.
- **Testability:** Tool handlers are pure async functions with typed inputs and outputs. Unit testing requires no framework mocking.
- **LLM selection accuracy:** Detailed descriptions and well-documented schemas reduce incorrect tool selection.
- **Security:** Tenant context inheritance prevents cross-tenant tool invocation.
- **Observability:** Standardized spans across all tools enable cross-tool latency analysis and error trending.

### Negative

- **Build-time generation:** Framework bindings must be regenerated when tools change. CI must verify generated code is up-to-date.
- **Zod dependency:** All tools depend on Zod. Migration from other validation libraries requires upfront work.
- **Registry startup cost:** Validating 47 tools at startup adds ~200ms to cold start. Mitigated by running validation in CI and skipping in production (registry loaded from validated snapshot).
- **Description maintenance:** Description quality gates require ongoing attention. Poor descriptions fail CI.
- **Migration cost:** 89 existing tool implementations must be consolidated into 47 canonical definitions.

---

## Compliance

### Automated Enforcement (Three Layers)

**IDE / Local Development:**
- ESLint rule `no-inline-tool-definition`: Error on tool implementations outside `tools/` directory.
- ESLint rule `no-throw-in-tool`: Error on `throw` statements in tool handler functions.
- ESLint rule `no-tenant-param-in-tool`: Error on `tenantId` or `tenant_id` parameters in tool handlers.
- TypeScript: `ToolRegistry` generic enforces that all registered tools match `ToolDefinition<TInput, TOutput>`.

**Pre-commit:**
- `lint-staged` runs ESLint on changed files.
- `tool-description-check` warns if a tool description is below 50 characters or missing field descriptions.

**CI Gate:**
- `check_tool_registry` job runs on every PR:
  - ESLint rules are errors
  - Tool registry validation: all tools pass uniqueness, description length, schema quality checks
  - Framework binding parity: generated bindings compile and match tool definitions
  - Tool unit test coverage: minimum 80% per tool handler
  - Generated code freshness: `git diff --exit-code` on `.generated/` fails if bindings are stale

### Runtime Enforcement
- `ToolRegistry` rejects registration of tools with invalid schemas or duplicate names.
- Tool handlers that throw (rather than return structured errors) are caught by the executor and converted to `INTERNAL_TOOL_ERROR` with `recoverable: false`.
- Tenant context is injected by the executor before calling the handler; handlers cannot override it.

### Manual Verification
- Quarterly review: 5 random tools audited for description quality and schema completeness.
- Architecture review: new tools must use `defineTool()`; no inline definitions approved.

---

## Migration

### Timeline

| Phase | Version | Date | Behavior |
|-------|---------|------|----------|
| Soft deprecation | v1.2.0 | 2026-07-10 | ESLint warnings, registry available, new tools must use `defineTool()` |
| Hard enforcement | v1.3.0 | 2026-10-10 | ESLint errors, CI fails, all tools must be registry-registered |
| Removal | v1.4.0 | 2027-01-10 | Inline tool code removed, framework binding generators mandatory |

### Codemod: `migrate-tool-definition`

```bash
npx @fabric/codemod migrate-tool-definition --target ./tools --framework langchain --write
```

**Before (inline lambda in agent config):**
```typescript
// services/orchestrator/src/agents/analytics-agent.ts
const analyticsAgent = new Agent({
  name: "analytics",
  tools: [
    {
      name: "execute_sql_query",
      description: "Run a SQL query",
      func: async ({ query }) => {
        const db = await getDb();
        const result = await db.query(query);  // No tenant context!
        return result.rows;
      },
    },
    {
      name: "send_email",
      description: "Send email",
      func: async ({ to, subject, body }) => {
        await emailClient.send({ to, subject, body });  // Throws on error — no structured response
      },
    },
  ],
});
```

**After (canonical tool definition + generated binding):**
```typescript
// tools/execute-sql-query.ts
export const executeSqlQuery = defineTool({
  name: "execute_sql_query",
  description: "Execute a read-only SQL query...", // 120 chars, detailed
  inputSchema: z.object({ /* ... */ }),
  outputSchema: z.object({ /* ... */ }),
  handler: async (input, context) => {
    const tenantCtx = getTenantContextOrThrow();
    // ... structured error handling, metadata
  },
});

// services/orchestrator/src/agents/analytics-agent.ts
import { toolRegistry } from "@fabric/tools/registry";
import { toLangChainTools } from "@fabric/platform/tools/langchain";

const analyticsAgent = new Agent({
  name: "analytics",
  tools: toLangChainTools(toolRegistry.getTools(["execute_sql_query", "send_notification"])),
});
```

**Before (framework-specific wrapper with duplicated logic):**
```typescript
// integrations/langchain/src/tools/sql-query.ts
const langchainSqlTool = new DynamicStructuredTool({
  name: "execute_sql_query",
  schema: z.object({ query: z.string() }),
  func: async ({ query }) => {
    // Business logic duplicated here
    const db = await getDb();
    const result = await db.query(query);
    return JSON.stringify(result.rows);
  },
});

// integrations/crewai/src/tools/sql-query.ts
@tool("execute_sql_query")
async function crewaiSqlTool(query: string) {
  // Same business logic, different wrapper
  const db = await getDb();
  const result = await db.query(query);
  return result.rows;
}
```

**After (single definition, generated wrappers):**
```typescript
// tools/execute-sql-query.ts — SINGLE CANONICAL DEFINITION
export const executeSqlQuery = defineTool({ /* ... */ });

// .generated/langchain-tools/execute-sql-query.ts — AUTO-GENERATED
// .generated/crewai-tools/execute-sql-query.ts — AUTO-GENERATED
// .generated/mcp-tools/execute-sql-query.ts — AUTO-GENERATED
```

### Consolidation Map

| Tool Name | Implementations Before | Canonical Location | Owner | Target |
|-----------|----------------------|---------------------|-------|--------|
| execute_sql_query | 4 (LC, CrewAI, MCP, inline) | `tools/execute-sql-query.ts` | @team-data | 2026-08-15 |
| search_documentation | 2 (LC, MCP) | `tools/search-documentation.ts` | @team-platform | 2026-08-01 |
| create_workflow | 2 (inline x2) | `tools/create-workflow.ts` | @team-agents | 2026-08-30 |
| validate_schema | 2 (LC, CrewAI) | `tools/validate-schema.ts` | @team-platform | 2026-08-15 |
| send_notification | 3 (CrewAI, inline, MCP) | `tools/send-notification.ts` | @team-agents | 2026-09-01 |

### Checklist Per Tool

- [ ] Create canonical definition with `defineTool()` in `tools/<tool-name>.ts`
- [ ] Write Zod input/output schemas with field descriptions
- [ ] Write detailed description (min 50 chars, include use/don't-use guidance)
- [ ] Implement handler with structured error returns (no `throw`)
- [ ] Add unit tests for handler (min 80% coverage)
- [ ] Remove all inline/duplicate implementations
- [ ] Register in `ToolRegistry`
- [ ] Verify generated framework bindings compile
- [ ] Run integration test: tool executes correctly via each framework
- [ ] Tag PR with `contract-adr-030`

---

## References

- CONTRACT.md Section 2.4: Tool Invocation Boundary
- ADR-028: Tenant Context Propagation Contract Ratification
- ADR-031: Agent Output Shape Contract Ratification
- `examples/canonical/tools/registry.ts`: Reference implementation
- `examples/canonical/tools/example-tool.ts`: Example tool definition
- `test/tool-registry-validation.spec.ts`: Compliance test
- INC-2026-0210, INC-2026-0430, INC-2026-0530, INC-2026-0620: Incident reports
