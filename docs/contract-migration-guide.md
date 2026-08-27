# Fabric 4L Contract Migration Guide

> Version: 1.2.0  
> Last updated: 2026-07-10  
> Applies to: All engineering teams  
> Enforcement: Soft deprecation (v1.2.0) → Hard enforcement (v1.3.0) → Legacy removal (v1.4.0)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Migration Timeline](#2-migration-timeline)
3. [Contract 1: Tenant Context Propagation](#3-contract-1-tenant-context-propagation-adr-028)
4. [Contract 2: Middleware and Auth Flow](#4-contract-2-middleware-and-auth-flow-adr-029)
5. [Contract 3: Tool Invocation Boundary](#5-contract-3-tool-invocation-boundary-adr-030)
6. [Contract 4: Agent Output Shape](#6-contract-4-agent-output-shape-adr-031)
7. [Contract 5: UI Route/State Progression](#7-contract-5-ui-routestate-progression-adr-032)
8. [Master Migration Checklist](#8-master-migration-checklist)
9. [Emergency Escalation](#9-emergency-escalation)

---

## 1. Overview

This guide is the single source of truth for migrating Fabric 4L services from deprecated cross-layer patterns to the five newly ratified canonical contracts (ADR-028, ADR-029, ADR-033, ADR-031, and ADR-032). Each section contains:

- **What you need to change** — specific code patterns to eliminate
- **Before/after code examples** — realistic Python and TypeScript
- **Timeline** — soft deprecation, hard enforcement, and removal dates
- **Automated migration** — codemod commands and their limitations
- **Per-service ownership** — who is responsible for what

### Guiding Principles

1. **The right way is the easy way.** Codemods automate mechanical changes. Reference implementations show the pattern. ESLint rules catch regressions.
2. **Migrate incrementally.** One service at a time, one contract at a time. Each PR should be reviewable in under 30 minutes.
3. **Don't break production.** Soft deprecation means warnings, not errors. Hard enforcement gives a 3-month runway.
4. **Ask for help.** `#fabric-contract-migration` Slack channel; @team-platform for Tenant Context and Middleware; @team-agents for Tools and Agent Output; @team-web for UI.

---

## 2. Migration Timeline

### Platform-Wide Schedule

```
2026-07-10  v1.2.0  RATIFICATION — All 5 contracts ratified
            ├─ ESLint warnings for deprecated patterns
            ├─ Codemods available for all contracts
            ├─ New code SHOULD use canonical patterns
            └─ Legacy code continues to work

2026-08-15  ────    Target: 50% of deprecated patterns migrated
            ├─ Tenant Context: services/web complete
            ├─ Middleware: services/web complete
            ├─ Tools: new tools use defineTool()
            └─ UI: /setup and /configure pages migrated

2026-09-15  ────    Target: 90% of deprecated patterns migrated
            ├─ All Tier-1 services compliant
            ├─ Integration tests passing
            └─ Remaining legacy code has migration tickets

2026-10-10  v1.3.0  HARD ENFORCEMENT
            ├─ ESLint warnings → ERRORS (CI fails)
            ├─ New code MUST use canonical patterns
            ├─ Remaining legacy code tracked in deprecation dashboard
            └─ No new deprecated patterns allowed

2027-01-10  v1.4.0  LEGACY REMOVAL
            ├─ All deprecated pattern adapters removed
            ├─ 100% compliance required
            └─ Non-compliant code is a P0 bug
```

### Per-Contract Schedule

| Contract | Soft Deprecation | Hard Enforcement | Legacy Removal |
|----------|-----------------|-------------------|----------------|
| ADR-028: Tenant Context | v1.2.0 (2026-07-10) | v1.3.0 (2026-10-10) | v1.4.0 (2027-01-10) |
| ADR-029: Middleware Flow | v1.2.0 (2026-07-10) | v1.3.0 (2026-10-10) | v1.4.0 (2027-01-10) |
| ADR-033: Tool Boundary | v1.2.0 (2026-07-10) | v1.3.0 (2026-10-10) | v1.4.0 (2027-01-10) |
| ADR-031: Agent Output | v1.2.0 (2026-07-10) | v1.3.0 (2026-10-10) | v1.4.0 (2027-01-10) |
| ADR-032: UI Route/State | v1.2.0 (2026-07-10) | v1.3.0 (2026-10-10) | v1.4.0 (2027-01-10) |

---

## 3. Contract 1: Tenant Context Propagation (ADR-028)

### What You Need to Change

Eliminate these three patterns:

| Anti-Pattern | What to do |
|-------------|-----------|
| Passing `tenantId` as a function parameter | Remove from all signatures below the HTTP handler layer; use `getTenantContext()` instead |
| Reading `req.tenant` or `req.headers["x-tenant-id"]` | Use `getTenantContext()` or `getTenantContextOrThrow()` |
| Storing mutable tenant state on the request object | Remove all `req.tenant = ...` assignments; context is immutable |

### Before/After Examples

**Before (parameter passing through service layers):**
```typescript
// services/api/src/workflows/service.ts
async function processWorkflow(
  workflowId: string,
  tenantId: string,           // ← ANTI-PATTERN: parameter pollution
  options: ProcessOptions,
): Promise<WorkflowResult> {
  const db = await getDbForTenant(tenantId);
  const rules = await loadRules(tenantId, workflowId);
  const audit = await createAuditEntry(tenantId, "workflow_process", workflowId);
  // 5 more functions, each needing tenantId forwarded...
  return { workflowId, status: "processed" };
}

async function loadRules(
  tenantId: string,            // ← ANTI-PATTERN: forwarded only for downstream
  workflowId: string,
): Promise<RuleSet> {
  // loadRules doesn't use tenantId itself, but needs it for getDbForTenant
  const db = await getDbForTenant(tenantId);
  return db.query("SELECT * FROM rules WHERE workflow_id = $1", [workflowId]);
}

// Route handler — passes tenantId from request
router.post("/workflows/:id/process", auth, async (req, res) => {
  const result = await processWorkflow(req.params.id, req.tenant.id, req.body);
  res.json(result);
});
```

**After (async context propagation):**
```typescript
// services/api/src/workflows/service.ts
import { getTenantContext, getTenantContextOrThrow } from "@fabric/platform/context";

async function processWorkflow(
  workflowId: string,
  options: ProcessOptions,     // ✓ Clean: only business parameters
): Promise<WorkflowResult> {
  const ctx = getTenantContextOrThrow();  // ✓ Retrieved from async context
  const db = await getDbFromContext(ctx);
  const rules = await loadRules(workflowId);  // ✓ No tenantId forwarding needed
  const audit = await createAuditEntry("workflow_process", workflowId);
  return { workflowId, status: "processed" };
}

async function loadRules(workflowId: string): Promise<RuleSet> {
  const ctx = getTenantContextOrThrow();  // ✓ Available anywhere in async scope
  const db = await getDbFromContext(ctx);
  return db.query("SELECT * FROM rules WHERE workflow_id = $1", [workflowId]);
}

// Route handler — context set by middleware, no parameter needed
router.post("/workflows/:id/process", auth, async (req, res) => {
  const result = await processWorkflow(req.params.id, req.body);
  res.json(result);
});
```

**Before (direct header access):**
```typescript
// services/analytics/src/reports/generator.ts
async function generateReport(reportType: string, req: Request): Promise<Report> {
  // ANTI-PATTERN: Reading headers outside auth middleware
  const tenantId = req.headers["x-tenant-id"] as string;
  // ANTI-PATTERN: No signature verification
  const db = await getDbForTenant(tenantId);
  return db.query("SELECT * FROM reports WHERE type = $1", [reportType]);
}
```

**After (context-driven access):**
```typescript
// services/analytics/src/reports/generator.ts
import { getTenantContextOrThrow } from "@fabric/platform/context";

async function generateReport(reportType: string): Promise<Report> {
  const ctx = getTenantContextOrThrow();  // ✓ Already validated by middleware
  const db = await getDbFromContext(ctx);
  return db.query("SELECT * FROM reports WHERE type = $1", [reportType]);
}
```

**Before (Python — parameter passing):**
```python
# services/orchestrator/src/agents/runner.py
async def execute_agent_run(
    run_id: str,
    tenant_id: str,  # ANTI-PATTERN
    agent_config: AgentConfig,
) -> RunResult:
    db = await get_db_for_tenant(tenant_id)
    rules = await load_rules(tenant_id, agent_config.workflow_id)
    # ...
```

**After (Python — contextvars):**
```python
# services/orchestrator/src/agents/runner.py
from fabric.platform.context import get_tenant_context_or_throw

async def execute_agent_run(
    run_id: str,
    agent_config: AgentConfig,  # ✓ Clean signature
) -> RunResult:
    ctx = get_tenant_context_or_throw()  # ✓ From contextvars
    db = await get_db_from_context(ctx)
    rules = await load_rules(agent_config.workflow_id)
    # ...
```

### Automated Migration

```bash
# Install the codemod
npm install -g @fabric/codemod

# Run against your service
npx @fabric/codemod migrate-tenant-context --target ./services/api --write

# Review changes
gh pr create --title "ADR-028: Migrate tenant context in api service" \
             --body "Automated + manual migration of tenant context pattern"
```

**What the codemod handles:**
- Removes `tenantId` parameters from function signatures (when parameter is unused after forwarding removal)
- Replaces `getDbForTenant(tenantId)` with `getDbFromContext(getTenantContextOrThrow())`
- Replaces `req.tenant.id` with `getTenantContextOrThrow().tenant_id`
- Adds the import statement for `@fabric/platform/context`

**What you must handle manually:**
- Complex destructuring patterns (`const { tenantId, ...rest } = options`)
- Default parameters (`tenantId = "default"`)
- Dynamic tenantId usage in string templates or conditional logic
- Background job processors that need `tenantContextStore.run()` wrapping

### Service Ownership

| Service | Anti-Pattern | Call Sites | Owner | Target Date |
|---------|-------------|------------|-------|-------------|
| `services/api/` | Parameter passing | 120 | @team-platform | 2026-08-15 |
| `services/orchestrator/` | Parameter passing | 85 | @team-agents | 2026-08-30 |
| `services/web/` | Request-object mutation | 40 | @team-web | 2026-08-01 |
| `services/analytics/` | Direct header access | 95 | @team-data | 2026-09-15 |

### Testing Your Migration

```bash
# Run the tenant context integration test
cd services/api && npm run test:integration -- --grep "cross-tenant isolation"

# Run ESLint to verify no new anti-patterns
npx eslint src/ --rule 'no-tenant-id-parameter: error'

# Verify getTenantContext() returns null outside scope
npm run test -- --grep "tenant context scope"
```

---

## 4. Contract 2: Middleware and Auth Flow (ADR-029)

### What You Need to Change

Eliminate these four patterns:

| Anti-Pattern | What to do |
|-------------|-----------|
| `app.use(middleware)` scattered through route files | Consolidate all into `pipeline.config.ts` |
| Re-verifying auth in route handlers or business logic | Trust `ctx.identity` and `ctx.tenantContext` set by auth phase |
| Hand-written Zod/Joi/Yup schemas in route files | Use OpenAPI-generated validators |
| `res.status().json()` or `res.send()` in middleware | Throw errors; let the error boundary handle responses |

### Before/After Examples

**Before (scattered inline middleware):**
```typescript
// services/api/src/routes/workflows.ts
import { Router } from "express";
import { authMiddleware } from "../middleware/auth";
import { validateWorkflowBody } from "../validation/workflows";  // Hand-written Zod
import { rateLimiter } from "../middleware/rate-limit";
import { corsMiddleware } from "../middleware/cors";

const router = Router();

// Scattered middleware — order depends on module load order!
router.use(corsMiddleware);
router.use(rateLimiter);

router.post(
  "/workflows",
  authMiddleware,
  validateWorkflowBody,  // Duplicates OpenAPI spec
  async (req, res) => {
    // ANTI-PATTERN: Re-validates auth inside handler
    const token = req.headers.authorization?.split(" ")[1];
    const payload = jwt.verify(token, JWT_SECRET);  // DUPLICATED AUTH
    const tenantId = payload.tenant_id;

    const workflow = await createWorkflow(req.body, tenantId);
    res.status(201).json(workflow);
  },
);

// Error handler in different file, writes response directly
router.use((err, req, res, next) => {
  res.status(500).json({ error: err.message, stack: err.stack });  // LEAKS STACK
});
```

**After (ordered phase pipeline):**
```typescript
// services/api/src/pipeline.config.ts
import { definePipeline } from "@fabric/platform/pipeline";

export const pipelineConfig = definePipeline({
  phases: [
    "request_id",
    "correlation",
    "auth",         // ✓ Single auth validation point
    "tenant_scope",
    "rate_limit",
    "validation",   // ✓ OpenAPI-generated validators
    "handler",
    "response",
  ],
  errorBoundary: "error_boundary",  // ✓ Centralized error handling
});

// services/api/src/routes/workflows.ts
import { defineRoute } from "@fabric/platform/pipeline";

export const createWorkflowRoute = defineRoute({
  path: "/workflows",
  method: "POST",
  phases: ["request_id", "correlation", "auth", "tenant_scope", "rate_limit", "validation", "handler", "response"],
  openApiSpec: "#/paths/workflows/post",  // ✓ Validation generated from spec
  handler: async (ctx: PipelineContext): Promise<Workflow> => {
    // ✓ Auth already validated; tenant context available via ctx
    const { tenantContext, validatedBody } = ctx;
    const workflow = await createWorkflow(validatedBody, tenantContext!.tenant_id);
    return workflow;  // ✓ Response phase serializes
  },
});
```

**Before (auth re-validation in business logic):**
```typescript
// services/orchestrator/src/agents/runner.ts
async function executeAgentRun(
  runId: string,
  tenantId: string,
  agentConfig: AgentConfig,
): Promise<RunResult> {
  // ANTI-PATTERN: Re-validates tenant access
  const hasAccess = await checkTenantAccess(tenantId, agentConfig.required_scope);
  if (!hasAccess) throw new AuthError("Access denied");

  // ANTI-PATTERN: Re-parses JWT
  const token = await getTokenFromCache(tenantId);
  const claims = jwt.verify(token, JWT_SECRET);

  // ... actual business logic
}
```

**After (trust auth context):**
```typescript
// services/orchestrator/src/agents/runner.ts
import { getTenantContextOrThrow } from "@fabric/platform/context";

async function executeAgentRun(
  runId: string,
  agentConfig: AgentConfig,
): Promise<RunResult> {
  const ctx = getTenantContextOrThrow();
  // ✓ Tenant access already validated by tenant_scope phase
  // ✓ ctx.scope contains granted permissions from auth phase
  if (!ctx.scope.includes(agentConfig.required_scope)) {
    throw new AuthorizationError(`Missing scope: ${agentConfig.required_scope}`);
  }
  // ... actual business logic — no auth re-validation
}
```

**Before (middleware writing response directly):**
```typescript
// services/api/src/middleware/error-handler.ts
export function errorHandler(err: Error, req: Request, res: Response, next: NextFunction) {
  console.error(err);  // ANTI-PATTERN: raw log
  // ANTI-PATTERN: middleware writes response
  res.status(500).json({
    error: err.message,
    stack: err.stack,     // LEAKS INTERNAL STATE
    internalCode: err.code,
  });
}
```

**After (error boundary handles responses):**
```typescript
// services/api/src/pipeline.config.ts
export const pipelineConfig = definePipeline({
  // ... phases ...
  errorBoundary: async (err: PipelineError, ctx: PipelineContext) => {
    // ✓ Centralized error formatting
    const response = formatCanonicalError(err, ctx);
    // ✓ Consistent logging via telemetry
    telemetry.recordException(err, {
      request_id: ctx.requestId,
      tenant_id: ctx.tenantContext?.tenant_id,
    });
    return response;  // Response phase writes this
  },
});
```

### Automated Migration

```bash
# Extract inline middleware into phase functions
npx @fabric/codemod migrate-middleware-pipeline --target ./services/api --write

# Validate OpenAPI spec alignment
npx @fabric/lint check-openapi-alignment --spec ./openapi.yaml --routes ./src/routes
```

**What the codemod handles:**
- Extracts `app.use()` calls into a `pipeline.config.ts` skeleton
- Converts Express middleware signatures to phase function signatures
- Removes `res.send()`/`res.json()` from middleware, replacing with `throw` statements
- Identifies hand-written validation schemas and flags them for OpenAPI migration

**What you must handle manually:**
- Ordering of middleware (codemod preserves file order; you may need to reorder)
- Converting per-route middleware variations into route manifest phase declarations
- Removing JWT re-validation from business logic (requires understanding each call site)
- Migrating hand-written schemas to OpenAPI spec changes

### Service Ownership

| Service | Anti-Pattern | Instances | Owner | Target Date |
|---------|-------------|-----------|-------|-------------|
| `services/api/` | Inline scatter-gather | 12 route files | @team-platform | 2026-09-01 |
| `services/web/` | Inline scatter-gather | 6 route files | @team-web | 2026-08-15 |
| `services/orchestrator/` | Auth re-validation | 8 agent runners | @team-agents | 2026-09-15 |
| `services/analytics/` | Custom Zod schemas | 15 schemas | @team-data | 2026-08-30 |

### Testing Your Migration

```bash
# Verify pipeline manifest validator passes at startup
npm run dev 2>&1 | grep "Pipeline manifest validated"

# Verify all routes return correct status codes
npm run test:integration -- --grep "route status codes"

# Verify auth phase executes before validation
npm run test:integration -- --grep "phase ordering"

# Verify no middleware writes responses directly
npx eslint src/ --rule 'no-middleware-res-write: error'
```

---

## 5. Contract 3: Tool Invocation Boundary (ADR-033)

### What You Need to Change

Eliminate these four patterns:

| Anti-Pattern | What to do |
|-------------|-----------|
| Inline tool lambdas in agent configs | Extract to `tools/` directory with `defineTool()` |
| Framework-specific wrappers with duplicated logic | Use auto-generated bindings from canonical definition |
| `throw` in tool implementations | Return structured `ToolResult` with `status: "error"` |
| Ambiguous/missing JSON Schema descriptions | Add detailed descriptions (min 50 chars, use/don't-use guidance) |

### Before/After Examples

**Before (inline lambda in agent config):**
```typescript
// services/orchestrator/src/agents/analytics-agent.ts
const analyticsAgent = new Agent({
  name: "analytics",
  tools: [
    {
      name: "execute_sql_query",
      description: "Run a SQL query",  // ← ANTI-PATTERN: too vague
      func: async ({ query }) => {
        // ANTI-PATTERN: inline business logic, no tenant context
        const db = await getDb();  // No tenant isolation!
        const result = await db.query(query);
        return result.rows;  // ANTI-PATTERN: raw return, no structured envelope
      },
    },
    {
      name: "send_email",
      description: "Send email",  // ← ANTI-PATTERN: too vague
      func: async ({ to, subject, body }) => {
        // ANTI-PATTERN: throws on error instead of structured response
        await emailClient.send({ to, subject, body });
      },
    },
  ],
});
```

**After (canonical tool definition + generated binding):**
```typescript
// tools/execute-sql-query.ts
import { defineTool } from "@fabric/platform/tools";
import { z } from "zod";

const inputSchema = z.object({
  query: z.string()
    .min(1)
    .max(10000)
    .describe("A single SQL SELECT statement. Must start with 'SELECT'. No DDL or DML."),
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
  `.trim(),  // ✓ Detailed description with use/don't-use guidance
  inputSchema,
  outputSchema,
  handler: async (input, context): Promise<ToolResult<z.infer<typeof outputSchema>>> => {
    const tenantCtx = getTenantContextOrThrow();  // ✓ Automatic tenant isolation
    const db = await getDbFromContext(tenantCtx);

    const startTime = performance.now();
    try {
      const result = await db.query(input.query);
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
      return {  // ✓ Structured error, no throw
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

// services/orchestrator/src/agents/analytics-agent.ts
import { toolRegistry } from "@fabric/tools/registry";
import { toLangChainTools } from "@fabric/platform/tools/langchain";

const analyticsAgent = new Agent({
  name: "analytics",
  // ✓ Single canonical definition, generated binding
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
  // Same business logic, different wrapper, different behavior
  const db = await getDb();
  const result = await db.query(query);
  return result.rows;  // Returns raw rows, not JSON string
}
```

**After (single definition, generated wrappers):**
```typescript
// tools/execute-sql-query.ts — SINGLE CANONICAL DEFINITION
export const executeSqlQuery = defineTool({ /* ... as above ... */ });

// .generated/langchain-tools/execute-sql-query.ts — AUTO-GENERATED (8 lines)
// .generated/crewai-tools/execute-sql-query.ts — AUTO-GENERATED (10 lines)
// .generated/mcp-tools/execute-sql-query.ts — AUTO-GENERATED (10 lines)
```

**Before (Python — inline tool with no schema):**
```python
# integrations/crewai/src/tools/data_tools.py
@tool("query_database")
def query_database(query: str) -> str:
    """Run a database query."""  # ANTI-PATTERN: too vague
    db = get_db()  # ANTI-PATTERN: no tenant context
    result = db.execute(query)
    return str(result)  # ANTI-PATTERN: no structured envelope
```

**After (Python — canonical tool definition):**
```python
# tools/query_database.py
from fabric.platform.tools import define_tool
from pydantic import BaseModel, Field

class QueryDatabaseInput(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="A single SQL SELECT statement. Must start with 'SELECT'. No DDL or DML.",
    )

class QueryDatabaseOutput(BaseModel):
    columns: list[str] = Field(description="Column names from the query result")
    rows: list[dict] = Field(description="Result rows as objects")
    row_count: int = Field(description="Total rows returned")

async def query_database_handler(
    input: QueryDatabaseInput,
    context: ToolContext,
) -> ToolResult[QueryDatabaseOutput]:
    tenant_ctx = get_tenant_context_or_throw()
    db = await get_db_from_context(tenant_ctx)

    start_time = time.monotonic()
    try:
        result = await db.execute(input.query)
        return ToolResult.success(
            data=QueryDatabaseOutput(
                columns=result.keys(),
                rows=[dict(row) for row in result],
                row_count=len(result),
            ),
            metadata=build_metadata(start_time, tenant_ctx, context),
        )
    except Exception as e:
        return ToolResult.error(  # Structured error, no throw
            code="QUERY_EXECUTION_ERROR",
            message=str(e),
            recoverable=is_recoverable_db_error(e),
        )

query_database_tool = define_tool(
    name="query_database",
    description=(
        "Execute a read-only SQL query against the tenant's analytics database. "
        "Use this when the user asks for data analysis. "
        "Do NOT use this for modifying data or sending messages."
    ),
    input_schema=QueryDatabaseInput,
    output_schema=QueryDatabaseOutput,
    handler=query_database_handler,
)
```

### Automated Migration

```bash
# Extract inline tools to canonical definitions
npx @fabric/codemod migrate-tool-definition --target ./tools --framework langchain --write

# Validate registry
npx @fabric/tools validate-registry

# Generate framework bindings
npm run generate:tool-bindings
```

**What the codemod handles:**
- Extracts inline tool lambdas from agent configs into separate files
- Wraps existing business logic in `defineTool()` structure
- Generates skeleton Zod schemas from TypeScript types
- Creates registry registration boilerplate

**What you must handle manually:**
- Writing detailed tool descriptions (min 50 chars with use/don't-use guidance)
- Adding field descriptions to Zod schemas
- Converting `throw` statements to structured error returns
- Ensuring tenant context is obtained via `getTenantContextOrThrow()`, not parameters
- Testing generated framework bindings

### Service Ownership

| Tool Name | Implementations Before | Canonical Location | Owner | Target Date |
|-----------|----------------------|---------------------|-------|-------------|
| execute_sql_query | 4 (LC, CrewAI, MCP, inline) | `tools/execute-sql-query.ts` | @team-data | 2026-08-15 |
| search_documentation | 2 (LC, MCP) | `tools/search-documentation.ts` | @team-platform | 2026-08-01 |
| create_workflow | 2 (inline x2) | `tools/create-workflow.ts` | @team-agents | 2026-08-30 |
| validate_schema | 2 (LC, CrewAI) | `tools/validate-schema.ts` | @team-platform | 2026-08-15 |
| send_notification | 3 (CrewAI, inline, MCP) | `tools/send-notification.ts` | @team-agents | 2026-09-01 |

### Testing Your Migration

```bash
# Validate tool registry at startup
npm run dev 2>&1 | grep "Tool registry validated: 47 tools"

# Verify framework bindings compile
npm run build --workspace=@fabric/generated-bindings

# Run tool unit tests
npm run test -- --grep "tool:"  # Runs tests for all tools

# Verify no throw in tool handlers
npx eslint tools/ --rule 'no-throw-in-tool: error'
```

---

## 6. Contract 4: Agent Output Shape (ADR-031)

### What You Need to Change

Eliminate these three patterns:

| Anti-Pattern | What to do |
|-------------|-----------|
| `JSON.parse()` on LLM response variables | Use `defineAgent()` with `outputSchema` and structured generation |
| Regex extraction from raw LLM text | Use structured generation with typed schemas |
| Ad-hoc output shapes per agent | Use canonical `AgentOutput<T>` envelope |

### Before/After Examples

**Before (JSON mode + manual parse):**
```typescript
// services/orchestrator/src/agents/analytics-agent.ts
const analyticsAgent = {
  name: "analytics",
  model: "gpt-4o",  // ANTI-PATTERN: no version pin
  generate: async (query: string) => {
    const response = await openai.chat.completions.create({
      model: "gpt-4o",
      response_format: { type: "json_object" },  // ANTI-PATTERN: no schema enforcement
      messages: [{ role: "user", content: `Analyze: ${query}` }],
    });
    // ANTI-PATTERN: raw parse, no validation
    const parsed = JSON.parse(response.choices[0].message.content!);
    return parsed;  // Could be any shape; no type safety
  },
};

// Consumer has to handle any possible shape
async function consumeAnalytics(output: unknown) {
  // Defensive coding because shape is unknown
  const summary = (output as any).summary ?? (output as any).result ?? "No summary";
  const confidence = (output as any).confidence ?? 0;
}
```

**After (structured generation with schema):**
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

// agents/analytics-agent.ts
import { defineAgent } from "@fabric/platform/agents";
import { AnalyticsOutputSchema } from "./analytics/output-schema";

export const analyticsAgent = defineAgent({
  name: "analytics",
  model: "gpt-4o",
  model_version: "2024-08-06",  // ✓ Pinned version
  outputSchema: AnalyticsOutputSchema,
  generate: async (input, context) => {
    // ✓ Structured generation — schema enforced at generation time
    const output = await context.generateStructured({
      messages: [{ role: "user", content: `Analyze: ${input.query}` }],
    });
    return output.result;  // ✓ Typed as AnalyticsOutput
  },
});

// Consumer uses typed output
async function consumeAnalytics(output: AgentOutput<AnalyticsOutput>) {
  const summary = output.result.summary;  // ✓ Type-safe access
  const confidence = output.confidence;    // ✓ Always present in envelope
  const modelVersion = output.metadata.model_version;  // ✓ Audit trail
}
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
  // ANTI-PATTERN: fragile regex extraction
  const match = text.match(/SELECT\s+.*;/is);
  return match ? match[0] : text;  // Silent failure on format change
}

// Incident: model started wrapping in ```sql fences
// Regex didn't match, malformed SQL executed
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

// Consumer
async function useNlToSql(output: AgentOutput<SqlOutputSchema>) {
  const sql = output.result.sql;           // ✓ Type-safe, validated
  const explanation = output.result.explanation;
  // No regex extraction needed — schema guarantees shape
}
```

**Before (Python — JSON mode):**
```python
# services/orchestrator/src/agents/support_agent.py
class SupportAgent:
    model = "gpt-4o"  # No version pin

    async def generate(self, query: str) -> dict:
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": query}],
        )
        content = response.choices[0].message.content
        return json.loads(content)  # No validation, no retry
```

**After (Python — structured generation):**
```python
# agents/support_agent.py
from pydantic import BaseModel, Field
from fabric.platform.agents import define_agent

class SupportOutput(BaseModel):
    response: str = Field(description="Response to the user's question")
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_docs: list[str] = Field(description="Relevant documentation links")

support_agent = define_agent(
    name="support",
    model="gpt-4o",
    model_version="2024-08-06",  # Pinned
    output_schema=SupportOutput,
)

async def handle_support_query(query: str) -> AgentOutput[SupportOutput]:
    result = await support_agent.generate_structured(
        messages=[{"role": "user", "content": query}],
    )
    return result  # Typed AgentOutput[SupportOutput]
```

### Automated Migration

```bash
# Migrate agent output patterns
npx @fabric/codemod migrate-agent-output --target ./services/orchestrator/src/agents --write

# Validate against golden test set
npm run test:golden -- --agent analytics

# Verify schema validation
npm run test -- --grep "agent:output:validation"
```

**What the codemod handles:**
- Replaces `JSON.parse()` with schema-driven `generateStructured()` calls
- Wraps agent definitions in `defineAgent()` with skeleton `outputSchema`
- Adds `model_version` pin (prompts for version)
- Converts return types to `AgentOutput<T>`

**What you must handle manually:**
- Defining the actual output Zod/Pydantic schema with field descriptions
- Writing regression tests with golden snapshots
- Updating consumers to use the `AgentOutput<T>` envelope
- Handling text-mode agents (conversational endpoints) that need explicit `output_mode: "text"`

### Service Ownership

| Agent | Pattern Before | Migration Effort | Owner | Target Date |
|-------|---------------|-----------------|-------|-------------|
| `analytics-agent` | JSON mode + parse | Medium | @team-data | 2026-08-30 |
| `workflow-agent` | Raw text + regex | High | @team-agents | 2026-09-15 |
| `invoice-agent` | Ad-hoc struct | Low | @team-billing | 2026-08-01 |
| `support-agent` | JSON mode + parse | Medium | @team-support | 2026-08-30 |
| `orchestrator` | Mixed | High | @team-platform | 2026-09-30 |

### Testing Your Migration

```bash
# Verify all agents have outputSchema
npx eslint agents/ --rule 'agent-output-schema-required: error'

# Run golden regression tests
npm run test:golden

# Verify audit persistence
npm run test:integration -- --grep "agent:audit:persistence"

# Verify no JSON.parse on LLM output
npx eslint src/ --rule 'no-json-parse-agent-output: error'
```

---

## 7. Contract 5: UI Route/State Progression (ADR-032)

### What You Need to Change

Eliminate these four patterns:

| Anti-Pattern | What to do |
|-------------|-----------|
| `router.push("/path")` in components | Use `navigate("TRANSITION_NAME")` via state machine |
| `window.location.href = "/path"` | Use `navigate("TRANSITION_NAME")` |
| Reading `router.query` or `window.location` for routing decisions | Use `useNavigationState()` hook |
| Browser history as source of workflow state | Use state machine history stack |

### Before/After Examples

**Before (imperative navigation):**
```tsx
// apps/web/src/components/setup/SetupForm.tsx
import { useRouter } from "next/router";

export function SetupForm() {
  const router = useRouter();

  const handleComplete = async () => {
    await saveSetup(config);
    // ANTI-PATTERN: imperative navigation, no workflow validation
    router.push("/configure");
  };

  const handleCancel = () => {
    // ANTI-PATTERN: direct URL manipulation
    window.location.href = "/";
  };

  const handleSkip = () => {
    // ANTI-PATTERN: invalid transition — setup → analyze bypasses configure and run
    router.push("/analyze");
  };

  return (
    <form>
      <button onClick={handleComplete}>Continue</button>
      <button onClick={handleCancel}>Cancel</button>
      <button onClick={handleSkip}>Skip to Results</button>
    </form>
  );
}
```

**After (state machine navigation):**
```tsx
// apps/web/src/components/setup/SetupForm.tsx
import { useNavigation } from "@fabric/platform/ui";

export function SetupForm() {
  const { navigate, canTransition } = useNavigation();

  const handleComplete = async () => {
    await saveSetup(config);
    // ✓ Validated transition — state machine verifies this is allowed
    await navigate("SETUP_COMPLETE");
  };

  const handleCancel = () => {
    navigate("SETUP_CANCEL");
  };

  // handleSkip removed — invalid transition is impossible by construction

  return (
    <form>
      <button onClick={handleComplete} disabled={!canTransition("SETUP_COMPLETE")}>
        Continue
      </button>
      <button onClick={handleCancel}>Cancel</button>
      {/* No "Skip to Results" — invalid transition */}
    </form>
  );
}
```

**Before (URL parsing in component):**
```tsx
// apps/web/src/components/shared/WorkflowHeader.tsx
import { useRouter } from "next/router";

export function WorkflowHeader() {
  const router = useRouter();
  // ANTI-PATTERN: fragile URL parsing
  const workflowId = router.query.id as string;
  const isRunPage = router.pathname.startsWith("/run");
  const tab = router.query.tab ?? "overview";

  return (
    <header>
      <h1>Workflow {workflowId}</h1>
      {isRunPage && <RunStatusBadge workflowId={workflowId} />}
      <TabNav activeTab={tab} />
    </header>
  );
}
```

**After (state-based rendering):**
```tsx
// apps/web/src/components/shared/WorkflowHeader.tsx
import { useNavigationState } from "@fabric/platform/ui";

export function WorkflowHeader() {
  const { currentState, params } = useNavigationState();
  // ✓ Stable — reads from state machine, not URL
  const workflowId = params.workflowId;
  const isRunPage = currentState === "workflow_run";

  return (
    <header>
      <h1>Workflow {workflowId}</h1>
      {isRunPage && <RunStatusBadge workflowId={workflowId} />}
    </header>
  );
}
```

**Before (browser history as workflow state):**
```tsx
// apps/web/src/hooks/use-workflow-state.ts
export function useWorkflowState() {
  const router = useRouter();

  const goBack = () => {
    // ANTI-PATTERN: browser back may go to external site
    router.back();
  };

  const currentStep = useMemo(() => {
    // ANTI-PATTERN: workflow state derived from URL
    const path = router.pathname;
    if (path.includes("setup")) return "setup";
    if (path.includes("configure")) return "configure";
    if (path.includes("run")) return "run";
    if (path.includes("analyze")) return "analyze";
    return "unknown";
  }, [router.pathname]);

  return { currentStep, goBack };
}
```

**After (state machine history):**
```tsx
// apps/web/src/hooks/use-workflow-state.ts
import { useNavigation } from "@fabric/platform/ui";

export function useWorkflowState() {
  const { currentState, goBack, canGoBack } = useNavigation();

  // ✓ State from state machine — consistent, validated
  const currentStep = currentState.replace("workflow_", "");

  // ✓ Back uses state machine history, not browser history
  const handleBack = () => {
    if (canGoBack) goBack();
  };

  return { currentStep, goBack: handleBack, canGoBack };
}
```

**Before (route guard with side effects):**
```tsx
// apps/web/src/guards/legacy/require-permissions.ts
export async function requirePermissions(router) {
  // ANTI-PATTERN: API call inside guard
  const response = await fetch("/api/permissions");
  const { permissions } = await response.json();

  // ANTI-PATTERN: Analytics tracking inside guard
  analytics.track("guard_check", { permissions });

  if (!permissions.includes("workflow:run")) {
    router.push("/unauthorized");
    return false;
  }
  return true;
}
```

**After (pure guard + lifecycle hooks):**
```tsx
// apps/web/src/routes/guards.ts
import { NavigationContext, GuardResult } from "@fabric/platform/ui";

// ✓ Pure function — reads from context only
export const requireWorkflowRunPermission = (
  ctx: NavigationContext,
): GuardResult => {
  if (!ctx.permissions.includes("workflow:run")) {
    return {
      passed: false,
      reason: "Missing workflow:run permission",
      redirectTo: "/unauthorized",
    };
  }
  return { passed: true };
};

// apps/web/src/routes/manifest.ts
export const routeManifest = defineRouteManifest({
  "/run": {
    state: "workflow_run",
    guards: [requireTenantContext, requireWorkflowRunPermission],
    onEnter: [
      fetchPermissions,        // ✓ Data fetching in onEnter, not guard
      trackPageView("run"),    // ✓ Analytics in onEnter, not guard
      initializeRun,
    ],
    transitions: { /* ... */ },
  },
});
```

### Automated Migration

```bash
# Migrate navigation patterns
npx @fabric/codemod migrate-navigation --target ./apps/web/src --write

# Validate route manifest
npx @fabric/ui validate-manifest --manifest ./src/routes/manifest.ts

# Check for dead transitions
npx @fabric/ui check-dead-transitions --manifest ./src/routes/manifest.ts
```

**What the codemod handles:**
- Replaces `router.push("/path")` with `navigate("TRANSITION_NAME")` (infers transition from route manifest)
- Replaces `window.location.href` with `navigate()`
- Replaces `useRouter()` routing decisions with `useNavigationState()`
- Extracts route guards into pure functions

**What you must handle manually:**
- Creating route manifest entries for pages that don't have them
- Naming transitions (the codemod generates names like `NAVIGATE_CONFIGURE`; you may want to customize)
- Moving side effects from guards to `onEnter` hooks
- Testing deep linking behavior
- Testing back navigation

### Service Ownership

| Page/Component | Pattern Before | Migration Effort | Owner | Target Date |
|----------------|---------------|-----------------|-------|-------------|
| `/setup` | Imperative router | Medium | @team-web | 2026-08-15 |
| `/configure` | Imperative + URL parse | Medium | @team-web | 2026-08-30 |
| `/run` | Browser history deps | High | @team-web | 2026-09-15 |
| `/analyze` | Imperative router | Medium | @team-web | 2026-09-01 |
| Shared components | Direct URL parse | High (34 components) | @team-web | 2026-09-30 |

### Testing Your Migration

```bash
# Verify all navigation uses state machine
npx eslint src/ --rule 'no-imperative-navigation: error'

# Verify no direct URL parsing
npx eslint src/ --rule 'no-direct-url-parse: error'

# Run UI integration tests
npm run test:e2e -- --spec "workflow-navigation"

# Verify deep linking
npm run test:e2e -- --spec "deep-linking"

# Verify back navigation
npm run test:e2e -- --spec "back-navigation"
```

---

## 8. Master Migration Checklist

### Per-Contract Checklist

Use this checklist for each contract migration. Copy into your PR description.

#### ADR-028: Tenant Context
- [ ] All `tenantId` parameters removed from function signatures (below HTTP handler layer)
- [ ] All `req.tenant` reads replaced with `getTenantContext()`
- [ ] All direct `req.headers["x-tenant-id"]` access removed
- [ ] All database access uses `getDbFromContext()` (not `getDbForTenant(tenantId)`)
- [ ] Background job processors wrap execution in `tenantContextStore.run()`
- [ ] ESLint `no-tenant-id-parameter` passes
- [ ] ESLint `no-req-tenant-access` passes
- [ ] Integration test `cross-tenant-isolation` passes
- [ ] Service README updated with Tenant Context section

#### ADR-029: Middleware Flow
- [ ] All `app.use()` calls extracted to `pipeline.config.ts`
- [ ] All middleware functions converted to phase functions
- [ ] All JWT re-validation removed from route handlers and business logic
- [ ] All hand-written validation schemas replaced with OpenAPI-generated
- [ ] All `res.send()`/`res.json()` removed from middleware (error boundary handles responses)
- [ ] Route manifests added for all routes with correct phase declarations
- [ ] ESLint `no-inline-middleware` passes
- [ ] ESLint `no-req-auth-revalidation` passes
- [ ] Pipeline manifest validator passes at startup
- [ ] Integration test `phase-ordering` passes

#### ADR-033: Tool Boundary
- [ ] All inline tool lambdas extracted to `tools/` with `defineTool()`
- [ ] All framework-specific business logic wrappers removed
- [ ] All tool handlers return `ToolResult<T>` (no `throw`)
- [ ] All tool descriptions are >= 50 chars with use/don't-use guidance
- [ ] All input schema fields have descriptions
- [ ] Tools registered in `ToolRegistry`
- [ ] Framework bindings generated and compile
- [ ] ESLint `no-inline-tool-definition` passes
- [ ] ESLint `no-throw-in-tool` passes
- [ ] Tool registry validation passes at startup

#### ADR-031: Agent Output
- [ ] All `JSON.parse()` on LLM output removed
- [ ] All regex extraction from LLM text removed
- [ ] All agents use `defineAgent()` with `outputSchema`
- [ ] All agents specify pinned `model_version`
- [ ] All consumers use `AgentOutput<T>` envelope
- [ ] Golden regression test snapshots created/updated
- [ ] Audit persistence verified (outputs stored with session/trace IDs)
- [ ] ESLint `no-json-parse-agent-output` passes
- [ ] ESLint `no-regex-extract-llm` passes

#### ADR-032: UI Route/State
- [ ] All `router.push()` replaced with `navigate("TRANSITION_NAME")`
- [ ] All `window.location` manipulation replaced with `navigate()`
- [ ] All direct URL parsing replaced with `useNavigationState()`
- [ ] Route manifest entries created for all pages
- [ ] Route guards converted to pure functions (no side effects)
- [ ] Side effects moved from guards to `onEnter` lifecycle hooks
- [ ] Deep linking works for all routes
- [ ] Back navigation uses state machine history
- [ ] ESLint `no-imperative-navigation` passes
- [ ] ESLint `no-url-concatenation` passes
- [ ] ESLint `no-direct-url-parse` passes

### Per-Service Migration Tracking

| Service | ADR-028 | ADR-029 | ADR-033 | ADR-031 | ADR-032 | Overall |
|---------|---------|---------|---------|---------|---------|---------|
| `services/api/` | ⬜ | ⬜ | — | — | — | 0/2 |
| `services/web/` | ⬜ | ⬜ | — | — | ⬜ | 0/3 |
| `services/orchestrator/` | ⬜ | ⬜ | ⬜ | ⬜ | — | 0/4 |
| `services/analytics/` | ⬜ | ⬜ | — | ⬜ | — | 0/3 |
| `apps/web/` | — | — | — | — | ⬜ | 0/1 |
| **Total** | **0/4** | **0/5** | **0/2** | **0/4** | **0/2** | **0/17** |

> Legend: ⬜ Not started | 🔄 In progress | ✅ Complete | — Not applicable

---

## 9. Emergency Escalation

### Migration Blockers

If a migration is blocked for more than 3 business days:

1. **Slack:** Post in `#fabric-contract-migration` with the `blocked` emoji and tag `@team-platform`
2. **Ticket:** File a `migration-blocker` ticket in Jira with:
   - Service name
   - Contract ADR number
   - Specific error message or ambiguity
   - What you've tried
   - What you need (decision, clarification, tooling fix)
3. **Escalation:** If no response within 24 hours, escalate to the Architecture Review Board via `arb@fabric.io`

### Legacy Pattern Exception Request

In rare cases, a legacy pattern cannot be migrated by the hard enforcement date. To request an exception:

1. File an exception request in Jira with:
   - Service name and team
   - Contract being excepted
   - Detailed justification (why migration is impossible, not just difficult)
   - Proposed alternative that meets the contract's safety goals
   - Target completion date for full migration
   - Risk assessment
2. The Architecture Review Board reviews within 5 business days
3. Approved exceptions are tracked in the contract dashboard with an `exception` badge and expiration date
4. No exceptions are granted past v1.4.0 (2027-01-10)

### CI Failure on Enforcement Date

When v1.3.0 hard enforcement begins:
- CI will fail for PRs introducing deprecated patterns
- CI will warn (not fail) for existing deprecated patterns in unchanged files
- Services with >95% compliance can request early hard enforcement
- Services with <50% compliance at v1.3.0 will be flagged for platform team pairing

---

*This guide is versioned. Check `docs/contract.md` for the authoritative contract specification and the ADR files for ratification rationale. For questions, use `#fabric-contract-migration`.*
