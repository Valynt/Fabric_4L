/**
 * Error Boundary - Canonical Implementation
 *
 * CONTRACT.md §2.3 - Middleware and Auth Flow (Error Boundary Phase)
 * CONTRACT.md §2.5 - Agent Output Shape and Traceability
 *
 * The error boundary is the global catch-all that:
 * - Catches any error from any phase
 * - Normalizes to canonical error shape
 * - Logs with trace context
 * - Serializes error response
 *
 * This file demonstrates both HTTP API error boundaries and
 * React component error boundaries.
 */

import { CanonicalError, ErrorCode, ErrorResponse } from "./error-shape";

// ============================================================================
// Types
// ============================================================================

/** Error context for logging */
export interface ErrorContext {
  requestId: string;
  traceId: string;
  tenantId?: string;
  userId?: string;
  route?: string;
  phase?: string;
}

/** Error boundary configuration */
export interface ErrorBoundaryConfig {
  /** Include stack traces in error responses (dev only) */
  includeStackTrace: boolean;

  /** Callback for custom error logging */
  onError?: (error: Error, context: ErrorContext, canonicalError: CanonicalError) => void;

  /** Fallback handler for unrecoverable errors */
  onFatal?: (error: unknown) => void;
}

// ============================================================================
// HTTP Error Boundary
// ============================================================================

/**
 * Global error boundary for HTTP request processing.
 *
 * CONTRACT.md §2.3:
 * - Catches errors from any middleware phase
 * - Normalizes to canonical error shape
 * - Logs with trace context
 * - Always produces valid HTTP response
 */
export class HttpErrorBoundary {
  constructor(private config: ErrorBoundaryConfig) {}

  /**
   * Catch and normalize any error.
   *
   * CONTRACT.md §2.3, §2.5:
   * - All errors normalized to canonical shape
   * - PII protection via sanitized messages
   * - Complete trace context for debugging
   *
   * @param error The error that was thrown
   * @param context Request context for correlation
   * @returns HTTP response with canonical error
   */
  catch(error: unknown, context: ErrorContext): ErrorResponse & { statusCode: number } {
    // Convert to canonical error
    const canonicalError = this.normalizeError(error, context);

    // Log with full context
    this.logError(error, context, canonicalError);

    // Build response
    const response: ErrorResponse = {
      success: false,
      error: canonicalError,
      meta: {
        request_id: context.requestId,
        trace_id: context.traceId,
        timestamp: new Date().toISOString(),
      },
    };

    const statusCode = mapErrorCodeToHttpStatus(canonicalError.code);

    return { ...response, statusCode };
  }

  /**
   * Normalize any error type to canonical shape.
   *
   * Handles:
   * - Native Error objects
   * - Custom error classes
   * - String errors
   * - Unknown types
   */
  private normalizeError(error: unknown, context: ErrorContext): CanonicalError {
    // Already canonical error
    if (this.isCanonicalError(error)) {
      return error;
    }

    // Native Error or custom error class
    if (error instanceof Error) {
      return this.normalizeNativeError(error, context);
    }

    // String error
    if (typeof error === "string") {
      return {
        code: "INTERNAL_ERROR",
        message: this.sanitizeForProduction(error),
        recoverable: false,
      };
    }

    // Unknown error type
    return {
      code: "INTERNAL_ERROR",
      message: "An unexpected error occurred",
      recoverable: false,
      details: this.config.includeStackTrace
        ? { errorType: typeof error }
        : undefined,
    };
  }

  private normalizeNativeError(error: Error, context: ErrorContext): CanonicalError {
    // Check for specific error types by name or constructor
    const errorName = error.name;
    const message = error.message;

    // Map known error types
    switch (errorName) {
      case "ValidationError":
      case "ZodError":
        return {
          code: "VALIDATION_FAILED",
          message: "Request validation failed",
          recoverable: true,
          details: this.config.includeStackTrace ? { originalMessage: message } : undefined,
        };

      case "UnauthorizedError":
      case "AuthenticationError":
        return {
          code: "AUTHENTICATION_FAILED",
          message: "Authentication required",
          recoverable: false,
        };

      case "ForbiddenError":
      case "AuthorizationError":
        return {
          code: "AUTHORIZATION_DENIED",
          message: "Access denied",
          recoverable: false,
        };

      case "NotFoundError":
        return {
          code: "NOT_FOUND",
          message: this.sanitizeForProduction(message),
          recoverable: false,
        };

      case "RateLimitError":
        return {
          code: "RATE_LIMIT_EXCEEDED",
          message: "Rate limit exceeded",
          recoverable: true,
        };

      case "TimeoutError":
        return {
          code: "TIMEOUT",
          message: "Request timeout",
          recoverable: true,
        };

      default:
        // Generic error - sanitize for production
        return {
          code: "INTERNAL_ERROR",
          message: this.sanitizeForProduction(message),
          recoverable: false,
          details: this.config.includeStackTrace
            ? {
                errorName,
                stack: error.stack?.split("\n").slice(0, 5),
                phase: context.phase,
              }
            : undefined,
        };
    }
  }

  private isCanonicalError(error: unknown): error is CanonicalError {
    return (
      typeof error === "object" &&
      error !== null &&
      "code" in error &&
      "message" in error &&
      "recoverable" in error
    );
  }

  private sanitizeForProduction(message: string): string {
    if (this.config.includeStackTrace) {
      return message;
    }

    // In production, sanitize potentially sensitive error messages
    // Remove file paths, SQL, tokens, etc.
    const sanitized = message
      .replace(/\/[^:]+:\d+/g, "[PATH_REDACTED]") // File paths
      .replace(/SELECT\s+.+?FROM/gi, "[SQL_REDACTED]") // SQL queries
      .replace(/Bearer\s+\S+/gi, "Bearer [TOKEN_REDACTED]") // Tokens
      .replace(/eyJ[a-zA-Z0-9_-]*/g, "[JWT_REDACTED]"); // JWTs

    // If message is too technical, replace with generic
    if (sanitized.length > 200 || sanitized.includes("at ") || sanitized.includes("Error:")) {
      return "An unexpected error occurred";
    }

    return sanitized;
  }

  private logError(error: unknown, context: ErrorContext, canonicalError: CanonicalError): void {
    const logEntry = {
      level: canonicalError.recoverable ? "warn" : "error",
      error_code: canonicalError.code,
      error_message: canonicalError.message,
      recoverable: canonicalError.recoverable,
      request_id: context.requestId,
      trace_id: context.traceId,
      tenant_id: context.tenantId,
      user_id: context.userId,
      route: context.route,
      phase: context.phase,
      timestamp: new Date().toISOString(),
      // Full error details for internal logging
      original_error:
        error instanceof Error
          ? {
              name: error.name,
              message: error.message,
              stack: error.stack,
            }
          : error,
    };

    // Console output (production would use structured logger)
    console.error("[ErrorBoundary]", JSON.stringify(logEntry, null, 2));

    // Custom error handler if configured
    if (this.config.onError && error instanceof Error) {
      try {
        this.config.onError(error, context, canonicalError);
      } catch (handlerError) {
        console.error("[ErrorBoundary] Custom error handler failed:", handlerError);
      }
    }
  }
}

// ============================================================================
// React Error Boundary (for Frontend)
// ============================================================================

import type { Component, ErrorInfo, ReactNode } from "react";

interface ReactErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ReactErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

/**
 * React Error Boundary component.
 *
 * Catches React rendering errors and displays fallback UI.
 * Reports errors to monitoring service.
 */
export class ReactErrorBoundary extends Component<
  ReactErrorBoundaryProps,
  ReactErrorBoundaryState
> {
  constructor(props: ReactErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ReactErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log to console
    console.error("[ReactErrorBoundary] Component error:", error);
    console.error("[ReactErrorBoundary] Component stack:", errorInfo.componentStack);

    // Call custom handler
    this.props.onError?.(error, errorInfo);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      // Render fallback UI
      return (
        this.props.fallback || (
          <div className="error-fallback">
            <h2>Something went wrong</h2>
            <p>Please refresh the page or contact support if the problem persists.</p>
            <button onClick={() => window.location.reload()}>Refresh Page</button>
          </div>
        )
      );
    }

    return this.props.children;
  }
}

// ============================================================================
// Agent Error Boundary
// ============================================================================

import { AgentOutput, ToolResult } from "./error-shape";

/**
 * Error boundary for agent execution.
 *
 * CONTRACT.md §2.5:
 * - Structured generation errors handled gracefully
 * - Retry logic integrated
 * - Returns typed default on failure
 */
export class AgentErrorBoundary {
  private maxRetries = 2;

  /**
   * Execute agent with retry logic.
   *
   * CONTRACT.md §2.5:
   * - Max 2 retries on validation failure
   * - Return typed default after retry exhaustion
   * - Never throw - always return AgentOutput
   */
  async executeWithRetry<T>(
    agentFn: () => Promise<AgentOutput<T>>,
    defaultValue: T
  ): Promise<AgentOutput<T>> {
    let lastError: unknown;
    let retryCount = 0;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        const result = await agentFn();

        // Return successful result with retry count
        return {
          ...result,
          metadata: {
            ...result.metadata,
            retry_count: retryCount,
            validation_passed: true,
          },
        };
      } catch (error) {
        lastError = error;
        retryCount = attempt;

        // Log retry attempt
        console.warn(`[AgentErrorBoundary] Attempt ${attempt + 1} failed, retrying...`, error);

        // Don't retry on non-recoverable errors
        if (this.isNonRecoverable(error)) {
          break;
        }
      }
    }

    // All retries exhausted - return typed default
    console.error(`[AgentErrorBoundary] All ${this.maxRetries + 1} attempts failed`, lastError);

    return this.createDefaultOutput(defaultValue, retryCount, lastError);
  }

  private isNonRecoverable(error: unknown): boolean {
    // Check if error indicates non-recoverable failure
    if (error instanceof Error) {
      const nonRecoverablePatterns = [
        "authentication",
        "unauthorized",
        "permission",
        "not found",
        "does not exist",
      ];

      return nonRecoverablePatterns.some((pattern) =>
        error.message.toLowerCase().includes(pattern)
      );
    }

    return false;
  }

  private createDefaultOutput<T>(
    defaultValue: T,
    retryCount: number,
    error: unknown
  ): AgentOutput<T> {
    return {
      result: defaultValue,
      reasoning: `Failed after ${retryCount} retries. Using default value.`,
      tool_calls: [],
      confidence: 0,
      trace_id: generateTraceId(),
      session_id: generateSessionId(),
      metadata: {
        model: "unknown",
        model_version: "unknown",
        latency_ms: 0,
        token_usage: { prompt: 0, completion: 0, total: 0 },
        validation_passed: false,
        retry_count: retryCount,
        finish_reason: "error",
      },
    };
  }
}

// ============================================================================
// Tool Error Boundary
// ============================================================================

/**
 * Wraps tool execution with error normalization.
 *
 * CONTRACT.md §2.4:
 * - Tools never throw - always return ToolResult
 * - Errors caught and converted to canonical shape
 */
export class ToolErrorBoundary {
  /**
   * Execute tool with error handling.
   */
  async execute<T>(
    toolFn: () => Promise<T>,
    toolName: string,
    tenantId: string,
    toolVersion: string,
    traceId: string
  ): Promise<ToolResult<T>> {
    const startTime = Date.now();

    try {
      const data = await toolFn();

      return {
        status: "success",
        data,
        metadata: {
          execution_time_ms: Date.now() - startTime,
          tenant_id: tenantId,
          tool_version: toolVersion,
          trace_id: traceId,
        },
      };
    } catch (error) {
      // Convert any error to canonical ToolResult
      return {
        status: "error",
        error: {
          code: "TOOL_EXECUTION_FAILED",
          message: this.extractErrorMessage(error),
          recoverable: this.isRecoverable(error),
          details: this.extractErrorDetails(error),
        },
        metadata: {
          execution_time_ms: Date.now() - startTime,
          tenant_id: tenantId,
          tool_version: toolVersion,
          trace_id: traceId,
        },
      };
    }
  }

  private extractErrorMessage(error: unknown): string {
    if (error instanceof Error) {
      return error.message;
    }
    if (typeof error === "string") {
      return error;
    }
    return "Tool execution failed";
  }

  private isRecoverable(error: unknown): boolean {
    // Network errors, timeouts are recoverable
    // Validation errors, not found are not recoverable
    if (error instanceof Error) {
      const recoverablePatterns = ["timeout", "network", "connection", "retry", "rate limit"];
      const nonRecoverablePatterns = ["not found", "invalid", "unauthorized", "forbidden"];

      const message = error.message.toLowerCase();

      if (nonRecoverablePatterns.some((p) => message.includes(p))) {
        return false;
      }

      if (recoverablePatterns.some((p) => message.includes(p))) {
        return true;
      }
    }

    return true; // Default to recoverable
  }

  private extractErrorDetails(error: unknown): Record<string, unknown> | undefined {
    if (error instanceof Error) {
      return {
        error_name: error.name,
        ...(error.cause && { cause: String(error.cause) }),
      };
    }
    return undefined;
  }
}

// ============================================================================
// Utilities
// ============================================================================

function mapErrorCodeToHttpStatus(code: ErrorCode): number {
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

function generateTraceId(): string {
  return `trace_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// ============================================================================
// Singleton Exports
// ============================================================================

/** Global HTTP error boundary instance */
export const httpErrorBoundary = new HttpErrorBoundary({
  includeStackTrace: process.env.NODE_ENV !== "production",
});

/** Global agent error boundary instance */
export const agentErrorBoundary = new AgentErrorBoundary();

/** Global tool error boundary instance */
export const toolErrorBoundary = new ToolErrorBoundary();
