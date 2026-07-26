# Fabric 4L Canonical Reference Implementation

This directory contains a production-quality reference implementation demonstrating all six canonical contracts from [CONTRACT.md](../../contract.md).

## Quick Start

### Creating a New Tool (Copy-Modify Pattern)

Copy [`tools/example-tool.ts`](./tools/example-tool.ts) and modify fewer than 10 lines:

```bash
# Copy template
cp tools/example-tool.ts tools/my-new-tool.ts

# Modify:
# 1. Tool name (line 89)
# 2. Description (line 90-95)  
# 3. Input schema (line 104-126)
# 4. Required permissions (line 130)
# 5. Implementation logic (line 143-199)
```

### Adding a New Route (Copy-Modify Pattern)

Copy from [`ui/route-manifest.ts`](./ui/route-manifest.ts) and fill in:

```typescript
const routeManifest: RouteManifest = {
  "/my-new-page": {
    state: "my_new_page",
    guards: [requireTenantContext],
    onEnter: [fetchData],
    transitions: {
      "NEXT": "next_state",
    },
  },
};
```

## File Reference

| File | Contract Section | Purpose | Lines to Modify |
|------|-----------------|---------|-----------------|
| `context/tenant-context.ts` | §2.1 | AsyncLocalStorage context management | Use as-is |
| `db/session-manager.ts` | §2.2 | Tenant-aware database sessions | Use as-is |
| `middleware/pipeline.ts` | §2.3 | Eight-phase middleware stack | Use as-is |
| `tools/registry.ts` | §2.4 | Tool registry and bindings | Use as-is |
| `tools/example-tool.ts` | §2.4 | **Template** for new tools | ~8 lines |
| `agent/orchestrator.ts` | §2.5 | Structured generation agent | Use as-is |
| `ui/route-manifest.ts` | §2.6 | State-machine routes | ~5 lines per route |
| `ui/guards.ts` | §2.6 | Route guard examples | Copy guard patterns |
| `errors/error-shape.ts` | §2.5 | Canonical error structures | Use as-is |
| `errors/error-boundary.ts` | §2.3 | Error handling | Use as-is |

## Usage Patterns

### Tenant Context (§2.1)

```typescript
import { getTenantContext, withTenantContext } from "./context/tenant-context";

// Access context (never pass as parameter!)
const ctx = getTenantContext();
if (!ctx) {
  throw new Error("Tenant context not available");
}
console.log(ctx.tenant_id);  // Safe to use

// Establish context scope (called by auth middleware)
await withTenantContext(tenantContext, async () => {
  // All code here can use getTenantContext()
  await processRequest();
});
```

### Tool Definition (§2.4)

```typescript
import { defineTool, toolRegistry } from "./tools/registry";
import { success, error } from "./errors/error-shape";

const myTool = defineTool<Input, Output>({
  name: "my_tool",
  description: "Clear description with when to use, when not, example...",
  input_schema: {
    type: "object",
    required: ["param"],
    properties: {
      param: { type: "string", description: "Parameter description" },
    },
    additionalProperties: false,
  },
  required_permissions: ["scope:action"],
  tenant_scoped: true,
  version: "1.0.0",
  timeout_ms: 30000,
  supports_partial: false,
  implementation: async (input, ctx) => {
    // NEVER throw - always return ToolResult
    try {
      const result = await doWork(input);
      return success(result, {
        execution_time_ms: Date.now() - startTime,
        tenant_id: ctx.tenant_context!.tenant_id,
        tool_version: ctx.tool_version,
        trace_id: ctx.trace_id,
      });
    } catch (e) {
      return error({
        code: "INTERNAL_ERROR",
        message: "Work failed",
        recoverable: true,
      }, metadata);
    }
  },
});

toolRegistry.register(myTool);
```

### Route Definition (§2.6)

```typescript
import { navigate, type RouteManifest } from "./ui/route-manifest";
import { requireTenantContext } from "./ui/guards";

const manifest: RouteManifest = {
  "/dashboard": {
    state: "dashboard",
    guards: [requireTenantContext],
    onEnter: [fetchData],
    transitions: {
      "VIEW_REPORT": "report_view",
    },
  },
};

// Navigate (never use router.push!)
navigate("report_view", { reportId: "123" });
```

## Testing

Each file includes usage examples in JSDoc comments. Run the full test suite:

```bash
# Test reference implementation
npm test -- examples/canonical/

# Test specific contract
npm test -- examples/canonical/context/tenant-context.test.ts
```

## Contract Compliance

These files serve as the source of truth for contract validation. The CI gate compares the actual codebase against these patterns:

```bash
# Run contract compliance check
make gate-contract

# Run drift detection only
make contract-drift
```

## Contributing

When modifying these reference files:
1. Ensure all changes comply with [CONTRACT.md](../../contract.md)
2. Update JSDoc examples to reflect changes
3. Run `make verify` before committing
4. Update this README if file structure changes

## See Also

- [CONTRACT.md](../../contract.md) - Full contract specification
- [DEPRECATIONS.md](../../DEPRECATIONS.md) - Migration tracking
- [../../Makefile](../../Makefile) - Build targets including `gate-contract`
