/**
 * Canonical Error Shape - Cross-Layer Standard
 *
 * CONTRACT.md §2.5 - Agent Output Shape and Traceability
 * CONTRACT.md §2.3 - Middleware and Auth Flow (Error Boundary)
 * CONTRACT.md §2.4 - Tool Invocation Boundary (ToolResult)
 *
 * This module defines the canonical error structure used across all layers:
 * - Tool results (ToolResult.error)
 * - Agent outputs (AgentOutput with error metadata)
 * - API error responses (ErrorResponse)
 * - Middleware error boundary serialization
 *
 * All errors in Fabric 4L must conform to this shape.
 */

// ============================================================================
// Core Error Types
// ============================================================================

/**
 * Machine-readable error codes for programmatic handling.
 *
 * CONTRACT.md §2.5:
 * - Error codes are standardized across all layers
 * - Agents can reason about failures using these codes
 * - Enables automated retry/recovery decisions
 */
export type ErrorCode =
  // Authentication/Authorization
  | "AUTHENTICATION_FAILED"
  | "AUTHORIZATION_DENIED"
  | "TENANT_ACCESS_DENIED"
  | "TOKEN_EXPIRED"
  | "TOKEN_INVALID"
  | "RATE_LIMIT_EXCEEDED"
  // Validation
  | "VALIDATION_FAILED"
  | "INVALID_PARAMETER"
  | "MISSING_REQUIRED_FIELD"
  | "TYPE_MISMATCH"
  // Resource
  | "NOT_FOUND"
  | "ALREADY_EXISTS"
  | "CONFLICT"
  | "GONE"
  // Business Logic
  | "BUSINESS_RULE_VIOLATION"
  | "INSUFFICIENT_QUOTA"
  | "OPERATION_NOT_ALLOWED"
  | "DEPENDENCY_FAILED"
  // Agent/Tool
  | "TOOL_EXECUTION_FAILED"
  | "AGENT_EXECUTION_FAILED"
  | "SCHEMA_VALIDATION_FAILED"
  | "RETRY_EXHAUSTED"
  // System
  | "INTERNAL_ERROR"
  | "SERVICE_UNAVAILABLE"
  | "TIMEOUT"
  | "CIRCUIT_BREAKER_OPEN";

/**
 * Severity levels for error classification.
 */
export type ErrorSeverity = "error" | "warning" | "info";

/**
 * Canonical error structure - used across all layers.
 *
 * CONTRACT.md §2.5:
 * - Machine-readable code for programmatic handling
 * - Human-readable message for debugging
 * - Recoverable flag for retry decisions
 * - Structured details for additional context
 */
export interface CanonicalError {
  /** Machine-readable error code */
  code: ErrorCode;

  /** Human-readable description for debugging and logs */
  message: string;

  /**
   * Whether the error is recoverable.
   *
   * CONTRACT.md §2.5:
   * - true: Agent can retry (transient failure, parameter fix needed)
   * - false: Permanent failure (don't retry)
   */
  recoverable: boolean;

  /** Additional structured context for debugging */
  details?: Record<string, unknown>;

  /** Field-level validation errors (for VALIDATION_FAILED) */
  field_errors?: Array<{
    field: string;
    message: string;
    code: string;
  }>;
}

// ============================================================================
// Tool Result Shape
// ============================================================================

/**
 * Tool execution status values.
 *
 * CONTRACT.md §2.4:
 * - "success": Tool executed successfully
 * - "error": Tool failed, check error field
 * - "partial": Partial success (e.g., 8/10 records processed)
 */
export type ToolStatus = "success" | "error" | "partial";

/**
 * Tool execution result - canonical shape for all tool outputs.
 *
 * CONTRACT.md §2.4:
 * - All tools must return this shape
 * - Never throw exceptions - always return error shape
 * - Metadata always present for observability
 */
export interface ToolResult<T> {
  /** Execution status */
  status: ToolStatus;

  /** Result data on success/partial */
  data?: T;

  /** Error details on error/partial */
  error?: CanonicalError;

  /** Execution telemetry - always present */
  metadata: {
    /** Wall-clock execution time */
    execution_time_ms: number;

    /** Tenant ID for audit trail */
    tenant_id: string;

    /** Tool version executed */
    tool_version: string;

    /** Trace ID for correlation */
    trace_id: string;
  };
}

// ============================================================================
// Agent Output Shape
// ============================================================================

/**
 * Individual tool call record within an agent run.
 *
 * CONTRACT.md §2.5:
 * - Complete audit trail of all tool invocations
 * - Ordered list in execution sequence
 * - Input hashed for PII protection
 */
export interface ToolCall {
  /** Tool name from registry */
  tool_name: string;

  /** SHA-256 hash of serialized input arguments */
  input_hash: string;

  /** Execution status from ToolResult */
  output_status: ToolStatus;

  /** Execution time for this specific call */
  latency_ms: number;

  /** Reference to OTel span for this call */
  span_id: string;
}

/**
 * Token usage metrics for cost tracking.
 */
export interface TokenUsage {
  prompt: number;
  completion: number;
  total: number;
}

/**
 * Complete agent run output - canonical shape.
 *
 * CONTRACT.md §2.5:
 * - All agent outputs must conform to this shape
 * - Structured generation enforces schema at generation time
 * - Pydantic validates at runtime
 * - Retry count tracks reliability
 */
export interface AgentOutput<T> {
  /** Strongly-typed result from Pydantic model */
  result: T;

  /** Chain-of-thought or explanation summary */
  reasoning?: string;

  /** Complete ordered list of tool calls */
  tool_calls: ToolCall[];

  /** Confidence score 0.0-1.0 */
  confidence: number;

  /** Reference to full OTel trace */
  trace_id: string;

  /** Session ID for multi-turn continuity */
  session_id: string;

  /** Execution metadata */
  metadata: {
    /** Model identifier (e.g., "gpt-4o-2024-08-06") */
    model: string;

    /** Provider's model version */
    model_version: string;

    /** Total wall-clock time */
    latency_ms: number;

    /** Token consumption */
    token_usage: TokenUsage;

    /** Whether Pydantic validation passed */
    validation_passed: boolean;

    /** Retry attempts needed (0 = first try success) */
    retry_count: number;

    /** Model's finish reason */
    finish_reason: string;
  };
}

// ============================================================================
// API Response Shapes
// ============================================================================

/**
 * HTTP API error response - returned by all layers.
 *
 * CONTRACT.md §2.3:
 * - Error boundary normalizes all errors to this shape
 * - Consistent structure regardless of failure phase
 * - Includes trace context for debugging
 */
export interface ErrorResponse {
  /** Error always false for error responses */
  success: false;

  /** Canonical error details */
  error: CanonicalError;

  /** Request correlation identifiers */
  meta: {
    request_id: string;
    trace_id: string;
    timestamp: string;
  };
}

/**
 * HTTP API success response wrapper.
 */
export interface SuccessResponse<T> {
  /** Success always true */
  success: true;

  /** Response data */
  data: T;

  /** Response metadata */
  meta: {
    request_id: string;
    trace_id: string;
    timestamp: string;
  };
}

/**
 * Union type for all API responses.
 */
export type ApiResponse<T> = SuccessResponse<T> | ErrorResponse;

// ============================================================================
// Factory Functions
// ============================================================================

/**
 * Create a successful tool result.
 *
 * @example
 * ```typescript
 * return success({ invoice_id: "inv-123" }, {
 *   execution_time_ms: Date.now() - startTime,
 *   tenant_id: ctx.tenant_context!.tenant_id,
 *   tool_version: "1.0.0",
 *   trace_id: ctx.trace_id,
 * });
 * ```
 */
export function success<T>(data: T, metadata: ToolResult<T>["metadata"]): ToolResult<T> {
  return {
    status: "success",
    data,
    metadata,
  };
}

/**
 * Create an error tool result.
 *
 * CONTRACT.md §2.4:
 * - Never throw exceptions - always return this shape
 * - Set recoverable flag appropriately for retry logic
 *
 * @example
 * ```typescript
 * return error(
 *   {
 *     code: "NOT_FOUND",
 *     message: `Customer ${input.customer_id} not found`,
 *     recoverable: false,
 *   },
 *   { execution_time_ms: Date.now() - startTime, ... }
 * );
 * ```
 */
export function error<T>(
  errorDetails: CanonicalError,
  metadata: ToolResult<T>["metadata"]
): ToolResult<T> {
  return {
    status: "error",
    error: errorDetails,
    metadata,
  };
}

/**
 * Create a partial success tool result.
 *
 * @example
 * ```typescript
 * return partial(
 *   { processed: 8, failed: 2, failed_ids: ["a", "b"] },
 *   {
 *     code: "PARTIAL_SUCCESS",
 *     message: "8 of 10 records processed successfully",
 *     recoverable: true,
 *     details: { failed_count: 2 },
 *   },
 *   { execution_time_ms: Date.now() - startTime, ... }
 * );
 * ```
 */
export function partial<T>(
  data: T,
  errorDetails: CanonicalError,
  metadata: ToolResult<T>["metadata"]
): ToolResult<T> {
  return {
    status: "partial",
    data,
    error: errorDetails,
    metadata,
  };
}

// ============================================================================
// Error Builders
// ============================================================================

/**
 * Builder for common error patterns.
 */
export const Errors = {
  notFound: (resource: string, id: string): CanonicalError => ({
    code: "NOT_FOUND",
    message: `${resource} with id "${id}" not found`,
    recoverable: false,
  }),

  validationFailed: (
    message: string,
    fieldErrors?: CanonicalError["field_errors"]
  ): CanonicalError => ({
    code: "VALIDATION_FAILED",
    message,
    recoverable: true,
    field_errors: fieldErrors,
  }),

  unauthorized: (message = "Authentication required"): CanonicalError => ({
    code: "AUTHORIZATION_DENIED",
    message,
    recoverable: false,
  }),

  tenantAccessDenied: (tenantId: string): CanonicalError => ({
    code: "TENANT_ACCESS_DENIED",
    message: `Access denied for tenant "${tenantId}"`,
    recoverable: false,
  }),

  rateLimited: (retryAfter?: number): CanonicalError => ({
    code: "RATE_LIMIT_EXCEEDED",
    message: "Rate limit exceeded",
    recoverable: true,
    details: retryAfter ? { retry_after_seconds: retryAfter } : undefined,
  }),

  internalError: (message = "Internal server error"): CanonicalError => ({
    code: "INTERNAL_ERROR",
    message,
    recoverable: false,
  }),

  toolExecutionFailed: (toolName: string, cause: string): CanonicalError => ({
    code: "TOOL_EXECUTION_FAILED",
    message: `Tool "${toolName}" failed: ${cause}`,
    recoverable: true,
  }),
};

// ============================================================================
// HTTP Response Helpers
// ============================================================================

/**
 * Create HTTP error response with status code mapping.
 */
export function createErrorResponse(
  error: CanonicalError,
  requestId: string,
  traceId: string
): { response: ErrorResponse; statusCode: number } {
  const statusCode = mapErrorCodeToStatus(error.code);

  return {
    response: {
      success: false,
      error,
      meta: {
        request_id: requestId,
        trace_id: traceId,
        timestamp: new Date().toISOString(),
      },
    },
    statusCode,
  };
}

function mapErrorCodeToStatus(code: ErrorCode): number {
  const mapping: Record<ErrorCode, number> = {
    AUTHENTICATION_FAILED: 401,
    AUTHORIZATION_DENIED: 403,
    TENANT_ACCESS_DENIED: 403,
    TOKEN_EXPIRED: 401,
    TOKEN_INVALID: 401,
    RATE_LIMIT_EXCEEDED: 429,
    VALIDATION_FAILED: 400,
    INVALID_PARAMETER: 400,
    MISSING_REQUIRED_FIELD: 400,
    TYPE_MISMATCH: 400,
    NOT_FOUND: 404,
    ALREADY_EXISTS: 409,
    CONFLICT: 409,
    GONE: 410,
    BUSINESS_RULE_VIOLATION: 422,
    INSUFFICIENT_QUOTA: 402,
    OPERATION_NOT_ALLOWED: 405,
    DEPENDENCY_FAILED: 424,
    TOOL_EXECUTION_FAILED: 500,
    AGENT_EXECUTION_FAILED: 500,
    SCHEMA_VALIDATION_FAILED: 500,
    RETRY_EXHAUSTED: 500,
    INTERNAL_ERROR: 500,
    SERVICE_UNAVAILABLE: 503,
    TIMEOUT: 504,
    CIRCUIT_BREAKER_OPEN: 503,
  };

  return mapping[code] || 500;
}
