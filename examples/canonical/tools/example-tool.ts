/**
 * Example Tool - Canonical Implementation Reference
 *
 * CONTRACT.md §2.4 - Tool Invocation Boundary
 *
 * This file demonstrates the canonical pattern for implementing a tool.
 * Copy this file and modify fewer than 10 lines to create a new tool:
 * 1. Change tool name and description
 * 2. Update input schema for your use case
 * 3. Implement the business logic in the implementation function
 * 4. Update required_permissions
 * 5. Adjust version and timeout as needed
 *
 * @types/node required for process.env access
 */

import { defineTool, toolRegistry, type ToolExecutionContext } from "./registry";
import { success, error, type ToolResult } from "../errors/error-shape";

// ============================================================================
// Constants
// ============================================================================

/** Tool name - single source of truth */
const TOOL_NAME = "example_customer_crud";

/** Tool version - semver */
const TOOL_VERSION = "1.0.0";

/** Default timeout for tool execution */
const DEFAULT_TIMEOUT_MS = 30000;

/** Customer ID pattern for validation */
const CUSTOMER_ID_PATTERN = /^cust_[a-z0-9]+$/;

// ============================================================================
// Input/Output Types
// ============================================================================

/**
 * Input parameters for the example tool.
 *
 * CONTRACT.md §2.4:
 * - Maximum 5-8 top-level parameters
 * - Each field must have a clear description
 * - Use enums for constrained values
 */
export interface ExampleToolInput {
  /** The customer identifier to look up */
  customer_id: string;

  /** Operation to perform on the customer record */
  operation: "get" | "update" | "delete";

  /** Optional data for update operations */
  data?: {
    /** Customer name (max 100 chars) */
    name?: string;

    /** Customer email address */
    email?: string;
  };
}

/**
 * Output type for successful tool execution.
 */
export interface ExampleToolOutput {
  /** The customer record */
  customer: {
    id: string;
    name: string;
    email: string;
    created_at: string;
  };

  /** The operation that was performed */
  operation: string;
}

// ============================================================================
// Tool Definition
// ============================================================================

/**
 * Example tool demonstrating the canonical pattern.
 *
 * This tool performs CRUD operations on customer records.
 * It demonstrates:
 * - Proper input schema with descriptions
 * - ToolResult return shape
 * - Error handling without exceptions
 * - Metadata population
 * - Permission checking
 *
 * Copy this file and modify:
 * 1. Tool name (line 89)
 * 2. Description (line 90-95)
 * 3. Input schema properties (line 104-126)
 * 4. Required permissions (line 130)
 * 5. Implementation function (line 143-199)
 */
export const exampleTool = defineTool<ExampleToolInput, ExampleToolOutput>({
  // -------------------------------------------------------------------------
  // 1. Tool Name - unique identifier in registry
  // -------------------------------------------------------------------------
  name: TOOL_NAME,

  // -------------------------------------------------------------------------
  // 2. Description - minimum 50 characters, include:
  //    - When to use this tool
  //    - When NOT to use this tool
  //    - Example of correct usage
  //
  // CONTRACT.md §2.4: Poor descriptions are the #1 cause of tool misuse by LLMs
  // -------------------------------------------------------------------------
  description: `
    Performs CRUD operations on customer records. Use this tool when you need to
    read, update, or delete customer information. Do NOT use this tool for creating
    new customers - use the create_customer tool instead. Example: To update a
    customer's email, call with operation="update" and data.email="new@example.com".
  `.trim(),

  // -------------------------------------------------------------------------
  // 3. Input Schema - JSON Schema with descriptions on every field
  //
  // CONTRACT.md §2.4:
  // - Maximum 5-8 top-level parameters
  // - Descriptions help LLM select correct values
  // - Enum constraints for discrete choices
  // - additionalProperties: false (enforced by registry)
  // -------------------------------------------------------------------------
  input_schema: {
    type: "object",
    required: ["customer_id", "operation"],
    properties: {
      customer_id: {
        type: "string",
        description: "The unique customer identifier (e.g., 'cust_abc123')",
        pattern: "^cust_[a-z0-9]+$",
        minLength: 8,
        maxLength: 32,
      },
      operation: {
        type: "string",
        description: "The CRUD operation to perform on the customer record",
        enum: ["get", "update", "delete"],
      },
      data: {
        type: "object",
        description: "Data payload for update operations (required when operation='update')",
        properties: {
          name: {
            type: "string",
            description: "Customer full name (1-100 characters)",
            minLength: 1,
            maxLength: 100,
          },
          email: {
            type: "string",
            description: "Customer email address (must be valid email format)",
            pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
          },
        },
        additionalProperties: false,
      },
    },
    additionalProperties: false,
  },

  // -------------------------------------------------------------------------
  // 4. Required Permissions - user must have ALL of these scopes
  // -------------------------------------------------------------------------
  required_permissions: ["customers:read", "customers:write"],

  // -------------------------------------------------------------------------
  // 5. Tenant Scoped - most tools operate on tenant data
  //
  // Set to false only for global tools (e.g., system health checks)
  // -------------------------------------------------------------------------
  tenant_scoped: true,

  // -------------------------------------------------------------------------
  // 6. Version - follow semver, increment on any behavior change
  // -------------------------------------------------------------------------
  version: TOOL_VERSION,

  // -------------------------------------------------------------------------
  // 7. Timeout - maximum execution time before cancellation
  // -------------------------------------------------------------------------
  timeout_ms: DEFAULT_TIMEOUT_MS,

  // -------------------------------------------------------------------------
  // 8. Supports Partial - true if tool can return partial results
  //
  // Example: bulk operations where some items succeed and some fail
  // -------------------------------------------------------------------------
  supports_partial: false,

  // -------------------------------------------------------------------------
  // 9. Implementation - the business logic
  //
  // CONTRACT.md §2.4:
  // - Never throw exceptions - always return ToolResult
  // - Call getTenantContext() to access tenant (never pass as parameter)
  // - Populate metadata for observability
  // - Use success(), error(), or partial() helpers
  // -------------------------------------------------------------------------
  implementation: async (
    input: ExampleToolInput,
    ctx: ToolExecutionContext
  ): Promise<ToolResult<ExampleToolOutput>> => {
    const startTime = Date.now();

    // -----------------------------------------------------------------------
    // Step 1: Validate tenant context (auto-populated from async scope)
    //
    // CONTRACT.md §2.1: Tools inherit tenant context from orchestrating agent
    // Never accept tenant_id as a parameter
    // -----------------------------------------------------------------------
    if (!ctx.tenant_context) {
      return error<ExampleToolOutput>(
        {
          code: "TENANT_ACCESS_DENIED",
          message: "No tenant context available for tool execution",
          recoverable: false,
        },
        {
          execution_time_ms: Date.now() - startTime,
          tenant_id: "unknown",
          tool_version: TOOL_VERSION,
          trace_id: ctx.trace_id,
        }
      );
    }

    const tenantId = ctx.tenant_context.tenant_id;

    // Helper to build consistent metadata
    const buildMetadata = (executionTimeMs: number) => ({
      execution_time_ms: executionTimeMs,
      tenant_id: tenantId,
      tool_version: ctx.tool_version,
      trace_id: ctx.trace_id,
    });

    try {
      // -----------------------------------------------------------------------
      // Step 2: Validate input (additional validation beyond schema)
      //
      // Schema validation happens automatically before implementation is called
      // Add business logic validation here
      // -----------------------------------------------------------------------
      // Validate customer_id format (defense in depth beyond schema)
      if (!CUSTOMER_ID_PATTERN.test(input.customer_id)) {
        return error<ExampleToolOutput>(
          {
            code: "VALIDATION_FAILED",
            message: `Invalid customer_id format: "${input.customer_id}"`,
            recoverable: true,
            details: { field: "customer_id", pattern: "^cust_[a-z0-9]+$" },
          },
          buildMetadata(Date.now() - startTime)
        );
      }

      if (input.operation === "update" && !input.data) {
        return error<ExampleToolOutput>(
          {
            code: "VALIDATION_FAILED",
            message: "data object is required when operation='update'",
            recoverable: true,
            details: { field: "data", operation: input.operation },
          },
          buildMetadata(Date.now() - startTime)
        );
      }

      // -----------------------------------------------------------------------
      // Step 3: Execute business logic
      //
      // This is where your actual implementation goes.
      // - Query databases using tenant-scoped sessions
      // - Call external APIs
      // - Perform calculations
      // -----------------------------------------------------------------------
      const customer = await fetchCustomerFromDatabase(
        input.customer_id,
        tenantId
      );

      if (!customer) {
        // Return structured error - never throw
        return error<ExampleToolOutput>(
          {
            code: "NOT_FOUND",
            message: `Customer "${input.customer_id}" not found in tenant "${tenantId}"`,
            recoverable: false,
            details: { customer_id: input.customer_id, tenant_id: tenantId },
          },
          buildMetadata(Date.now() - startTime)
        );
      }

      // Perform the requested operation
      switch (input.operation) {
        case "get":
          // Just return the customer data
          break;

        case "update":
          // Update customer with provided data
          if (input.data?.name) customer.name = input.data.name;
          if (input.data?.email) customer.email = input.data.email;
          await saveCustomerToDatabase(customer, tenantId);
          break;

        case "delete":
          // Soft delete the customer
          await deleteCustomerFromDatabase(input.customer_id, tenantId);
          break;
      }

      // -----------------------------------------------------------------------
      // Step 4: Return success with metadata
      //
      // CONTRACT.md §2.4: Metadata always present for observability
      // -----------------------------------------------------------------------
      return success<ExampleToolOutput>(
        {
          customer: {
            id: customer.id,
            name: customer.name,
            email: customer.email,
            created_at: customer.created_at,
          },
          operation: input.operation,
        },
        buildMetadata(Date.now() - startTime)
      );
    } catch (unexpectedError) {
      // -----------------------------------------------------------------------
      // Step 5: Handle unexpected errors
      //
      // CONTRACT.md §2.4: Never let exceptions escape - always return ToolResult
      // Log the full error internally, return safe message to agent
      // -----------------------------------------------------------------------
      // Log structured error for observability
      console.error(`[Tool Error] ${TOOL_NAME}:`, unexpectedError);

      return error<ExampleToolOutput>(
        {
          code: "INTERNAL_ERROR",
          message: "An unexpected error occurred while processing the customer request",
          recoverable: true, // Agent can retry
          details: {
            // Include error type but not sensitive details
            error_type: unexpectedError instanceof Error ? unexpectedError.name : "Unknown",
          },
        },
        buildMetadata(Date.now() - startTime)
      );
    }
  },
});

// ============================================================================
// Database Helpers (Mock implementations - replace with real ORM calls)
// ============================================================================

interface CustomerRecord {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

async function fetchCustomerFromDatabase(
  customerId: string,
  tenantId: string
): Promise<CustomerRecord | null> {
  // CONTRACT.md §2.2: Use tenant-scoped database sessions
  // db.getSession() automatically applies tenant scoping

  // Mock implementation - replace with actual ORM query
  // Example with Prisma:
  // return await db.getSession().customer.findUnique({
  //   where: { id: customerId, tenant_id: tenantId }
  // });

  if (customerId === "cust_notfound") {
    return null;
  }

  return {
    id: customerId,
    name: "Example Customer",
    email: "customer@example.com",
    created_at: "2024-01-15T10:30:00Z",
  };
}

async function saveCustomerToDatabase(
  customer: CustomerRecord,
  tenantId: string
): Promise<void> {
  // Mock implementation - replace with actual ORM update
  console.log(`[DB] Updated customer ${customer.id} in tenant ${tenantId}`);
}

async function deleteCustomerFromDatabase(
  customerId: string,
  tenantId: string
): Promise<void> {
  // Mock implementation - replace with actual ORM delete
  console.log(`[DB] Deleted customer ${customerId} in tenant ${tenantId}`);
}

// ============================================================================
// Registration
// ============================================================================

/**
 * Register this tool with the global registry.
 *
 * Call this at application startup.
 */
export function registerExampleTool(): void {
  toolRegistry.register(exampleTool);
  console.log(`[Tool] Registered ${TOOL_NAME}`);
}

// Auto-register when imported (for development)
if (process.env.NODE_ENV !== "test") {
  registerExampleTool();
}
