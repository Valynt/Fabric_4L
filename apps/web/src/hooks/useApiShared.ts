/**
 * Shared utilities for API hooks
 *
 * Single source of truth for cache durations, retry logic, and error handling.
 * All hooks MUST import stale-time values from here instead of defining local
 * constants. This prevents divergence and makes cache tuning a one-line change.
 */

import type { ZodError } from 'zod';
import { ApiError } from '@/api/client';

// ── Cache duration constants (milliseconds) ───────────────────────────────────
export const STALE_TIME = {
  // Short-lived — frequently changing data (job queues, sync status)
  realtime:  1_000,           //  1 second  — live job/extraction status
  poll:      30_000,          // 30 seconds — lists, bindings, ingestion jobs
  // Medium-lived — moderately changing data
  list:      30_000,          // 30 seconds — generic list queries
  stats:     60_000,          //  1 minute  — aggregate stats
  activity:  5 * 60_000,      //  5 minutes — account activity, filter options
  // Long-lived — rarely changing reference data
  detail:    5 * 60_000,      //  5 minutes — single-item detail views
  reference: 10 * 60_000,     // 10 minutes — provenance, ontology, value packs
  // Aliases kept for backward compatibility with hooks already using STALE_TIME
  bindings:  30_000,          // 30 seconds (= poll)
  // Domain-specific durations (previously scattered across individual hook files)
  policies:  60_000,          //  1 minute  — benchmark/governance policies
  approvals: 10_000,          // 10 seconds — pending approval queues
  tenant:    30_000,          // 30 seconds — Clerk org → Fabric tenant mapping
} as const;

// ── Retry configuration ───────────────────────────────────────────────────────
// Vitest detection disables retries to prevent test timeouts
// Vitest defines globalThis.VITEST or process.env.VITEST in test environment
const isTestEnv = 
  (typeof process !== 'undefined' && process.env?.VITEST === 'true') ||
  (typeof globalThis !== 'undefined' && (globalThis as Record<string, unknown>).VITEST === true);

export const RETRY_CONFIG = {
  maxRetries: isTestEnv ? false : 3,
  retryDelay: (attemptIndex: number) => Math.min(1_000 * 2 ** attemptIndex, 30_000),
} as const;

// ── Zod error formatting ──────────────────────────────────────────────────────
/**
 * Format Zod validation errors into a human-readable string.
 *
 * @param error - The ZodError to format
 * @param context - Description of what was being validated (e.g., 'formula response')
 * @returns Formatted error message with issue details
 */
export function formatZodError(error: ZodError, context: string): string {
  const details = error.issues.map(e => `${String(e.path)}: ${e.message}`).join(', ');
  return `Invalid ${context}: ${details}`;
}

// ── Base API error class ──────────────────────────────────────────────────────
export class BaseApiError extends Error {
  public errorCode?: string;
  public traceId?: string | null;

  constructor(
    message: string,
    public statusCode?: number,
    public responseData?: unknown,
    errorCode?: string,
    traceId?: string | null
  ) {
    super(message);
    this.name = 'BaseApiError';
    this.errorCode = errorCode;
    this.traceId = traceId;
  }
}

export type ApiErrorClass = typeof BaseApiError;

// ── Error wrapper ─────────────────────────────────────────────────────────────
/**
 * Wraps an API call with standardized error handling.
 * Extracts status code and response data from axios-style errors or ApiError instances.
 */
export async function withApiError<T, E extends BaseApiError>(
  promise: Promise<T>,
  ErrorClass: new (message: string, statusCode?: number, responseData?: unknown) => E
): Promise<T> {
  try {
    return await promise;
  } catch (err: unknown) {
    if (err instanceof ApiError) {
      const newError = new ErrorClass(err.message, err.statusCode, undefined);
      newError.errorCode = err.errorCode;
      newError.traceId = err.traceId;
      newError.cause = err;
      throw newError;
    }

    // Handle axios-style errors
    if (err instanceof Error && 'response' in err) {
      const axiosErr = err as { response?: { status?: number; data?: unknown } };
      const newError = new ErrorClass(
        err.message,
        axiosErr.response?.status,
        axiosErr.response?.data
      );
      if (typeof axiosErr.response?.data === 'object' && axiosErr.response?.data !== null) {
        const responseData = axiosErr.response.data as Record<string, unknown>;
        const envelope = responseData.error;
        if (typeof envelope === 'object' && envelope !== null) {
          const errorEnvelope = envelope as Record<string, unknown>;
          newError.errorCode = typeof errorEnvelope.code === 'string' ? errorEnvelope.code : undefined;
          newError.traceId = typeof errorEnvelope.request_id === 'string' ? errorEnvelope.request_id : null;
        }
      }
      newError.cause = err;
      throw newError;
    }
    const newError = new ErrorClass(err instanceof Error ? err.message : 'Unknown error');
    if (err instanceof Error) {
      newError.cause = err;
    }
    throw newError;
  }
}
