import { safeAsync } from '@/lib/async';
/**
 * useJobStream.ts - Server-Sent Events hook for extraction job streaming
 *
 * Provides real-time updates for extraction jobs from L2 API.
 * Falls back to polling if SSE is not available.
 *
 * DEFENSIVE PROGRAMMING: All 7 mandates applied:
 * - M1: NULL/UNDEFINED SAFETY - Optional chaining and nullish coalescing throughout
 * - M2: TYPE SAFETY - Zod runtime validation replaces all `as` assertions
 * - M3: ERROR HANDLING - Every async operation has try/catch with context logging
 * - M4: INPUT VALIDATION - jobId format validated, SSE data validated
 * - M5: RACE CONDITION ELIMINATION - Ref comparison guards, jobId closure capture
 * - M6: RESOURCE LEAK PREVENTION - Guaranteed cleanup in all paths
 * - M7: BOUNDS SAFETY - All array operations have length checks
 */
import { useEffect, useRef, useState, useCallback } from "react";
import { z } from "zod";
import { apiGet } from "@/api/typedClient";
import {
  parseJobStreamEventJson,
  applyJobStreamEvent,
  mapJobStatus,
  logWarn,
  logError,
  type JobStreamState,
} from "./useJobStream.utils";
import {
  SSEBuilders,
  SSE_TIMEOUT_MS as SHARED_SSE_TIMEOUT_MS,
} from "./useSSEUtils";
import { parseExtractionJob, type ApiExtractedEntityDto, type ApiProgressLogDto } from "@/types/api";
import { POLL_INTERVALS } from "./usePolling";

// ============================================================================
// MANDATE 4: INPUT VALIDATION - Job ID Format Validation
// ============================================================================

/** Job ID must be non-empty string with alphanumeric/hyphen/underscore */
const JobIdSchema = z
  .string()
  .min(1)
  .regex(/^[a-zA-Z0-9_-]+$/);

/**
 * Validates jobId format. Returns null if invalid.
 */
function validateJobId(jobId: string | null): string | null {
  if (jobId === null) return null;
  const result = JobIdSchema.safeParse(jobId);
  if (!result.success) {
    logError("Invalid jobId format", { jobId, error: result.error.message });
    return null;
  }
  return result.data;
}

// ============================================================================
// MANDATE 3: ERROR HANDLING - Safe Logging Wrapper
// ============================================================================

// Logging helpers are imported from ./useJobStream.utils so that the pure
// parsing functions and the hook share a single feature logger.

// ============================================================================
// Types
// ============================================================================

export type { JobStreamState };

// ============================================================================
// Re-exports for existing consumers
// ============================================================================

export { parseJobStreamEvent, parseJobStreamEventJson } from "./useJobStream.utils";

// ============================================================================
// MANDATE 2: TYPE SAFETY - Runtime Validation Functions
// ============================================================================

// Pure parsing and state-reduction helpers live in ./useJobStream.utils.

/**
 * Subscribe to real-time job updates via SSE or polling fallback.
 *
 * MANDATE 5: RACE CONDITION ELIMINATION - Uses refs to track latest jobId
 * MANDATE 6: RESOURCE LEAK PREVENTION - All resources cleaned up in cleanup()
 *
 * @param jobId - The extraction job ID to stream
 * @returns Job stream state and connection status
 */
export function useJobStream(jobId: string | null) {
  // MANDATE 4: Validate jobId at entry point
  const validatedJobId = validateJobId(jobId);

  const [state, setState] = useState<JobStreamState>({
    progress: 0,
    status: "created",
    logs: [],
    entities: [],
  });
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // MANDATE 5: RACE CONDITION ELIMINATION - Track latest jobId in ref for comparison
  const jobIdRef = useRef<string | null>(validatedJobId);
  const eventSourceRef = useRef<EventSource | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const sseSupportedRef = useRef<boolean | null>(null);
  const isMountedRef = useRef<boolean>(true);
  const abortControllerRef = useRef<AbortController | null>(null);

  // MANDATE 5: Keep ref in sync (assign in an effect, never during render).
  // Declared before the connection effect below so the ref is updated first.
  useEffect(() => {
    jobIdRef.current = validatedJobId;
  }, [validatedJobId]);

  // ============================================================================
  // MANDATE 3: ERROR HANDLING - Polling with comprehensive error handling
  // ============================================================================
  const pollJobStatus = useCallback(async () => {
    // MANDATE 5: Capture jobId at call time to prevent race
    const currentJobId = jobIdRef.current;
    if (currentJobId === null) return;

    // MANDATE 6: Create abort controller for this request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      const response = await apiGet("l2", `/jobs/${currentJobId}`, {
        signal: abortControllerRef.current.signal,
      });

      // MANDATE 5: Check if still mounted and jobId hasn't changed
      if (!isMountedRef.current || jobIdRef.current !== currentJobId) return;

      const job = parseExtractionJob(response.data);

      setState(prev => ({
        progress: job.progress_percent_complete ?? prev.progress,
        status: mapJobStatus(job.status ?? ""),
        logs: (job.progress_logs ?? []).map((log: ApiProgressLogDto) => ({
          timestamp: log.timestamp ?? "",
          level: log.level ?? "INFO",
          message: log.message ?? "",
        })),
        entities: (job.extracted_entities ?? []).map((entity: ApiExtractedEntityDto) => ({
          type: entity.type ?? "unknown",
          name: entity.name ?? "Unknown",
        })),
      }));

      setError(null);

      // Stop polling if job is complete
      if (["COMPLETED", "FAILED", "CANCELLED"].includes(job.status ?? "")) {
        if (pollIntervalRef.current !== null) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
      }
    } catch (err) {
      // MANDATE 3: Don't set error if aborted (expected during cleanup)
      if (err instanceof Error && err.name === "AbortError") return;

      // MANDATE 5: Only update state if still relevant
      if (!isMountedRef.current || jobIdRef.current !== currentJobId) return;

      const errorMessage =
        err instanceof Error ? err.message : "Failed to fetch job status";
      logError("Polling failed", { jobId: currentJobId, error: errorMessage });
      setError(err instanceof Error ? err : new Error(errorMessage));
    }
  }, []); // MANDATE 5: No deps - uses refs for latest values

  // ============================================================================
  // MANDATE 6: RESOURCE LEAK PREVENTION - Cleanup helper
  // ============================================================================
  const cleanup = useCallback(() => {
    // MANDATE 3: Abort any in-flight requests
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // Clear timers
    if (timeoutRef.current !== null) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (pollIntervalRef.current !== null) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    // Close EventSource
    if (eventSourceRef.current !== null) {
      try {
        eventSourceRef.current.close();
      } catch (err) {
        logWarn("Error closing EventSource", { error: String(err) });
      }
      eventSourceRef.current = null;
    }
  }, []);

  useEffect(() => {
    // MANDATE 6: Mark as mounted
    isMountedRef.current = true;

    // MANDATE 4: Reset state when jobId becomes null
    if (validatedJobId === null) {
      cleanup();
      setState({ progress: 0, status: "created", logs: [], entities: [] });
      setIsConnected(false);
      setError(null);
      // MANDATE 6: Return a cleanup on every effect run so unmount/re-run
      // always guarantees resource cleanup, even when no connection opened.
      return () => {
        isMountedRef.current = false;
        cleanup();
      };
    }

    // MANDATE 4: Capture validated jobId for this effect instance
    const effectJobId = validatedJobId;

    // ============================================================================
    // SSE Connection Setup
    // ============================================================================
    const trySseConnection = (): void => {
      // MANDATE 6: Clean up any existing connection first
      cleanup();

      let url: string;
      try {
        url = SSEBuilders.l2(`/jobs/${effectJobId}/events`);
      } catch (err) {
        logError("Failed to build SSE URL", {
          jobId: effectJobId,
          error: String(err),
        });
        startPolling();
        return;
      }

      // MANDATE 3: EventSource creation can throw
      let es: EventSource;
      try {
        es = new EventSource(url);
      } catch (err) {
        logWarn("EventSource creation failed, falling back to polling", {
          jobId: effectJobId,
          error: String(err),
        });
        startPolling();
        return;
      }

      eventSourceRef.current = es;
      setIsConnected(true);
      setError(null);

      // MANDATE 6: Set up timeout for connection failure
      timeoutRef.current = setTimeout(() => {
        // MANDATE 5: Only act if this is still the current EventSource
        if (eventSourceRef.current === es && isMountedRef.current) {
          logWarn("SSE connection timeout, falling back to polling", {
            jobId: effectJobId,
          });
          cleanup();
          sseSupportedRef.current = false;
          setIsConnected(false);
          startPolling();
        }
      }, SHARED_SSE_TIMEOUT_MS);

      // ============================================================================
      // MANDATE 3: SSE Message Handler with full error handling
      // ============================================================================
      es.onmessage = (event: MessageEvent): void => {
        try {
          // MANDATE 6: Clear timeout on any valid message
          if (timeoutRef.current !== null) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
          }

          // MANDATE 5: Skip if component unmounted or job changed
          if (!isMountedRef.current || jobIdRef.current !== effectJobId) return;

          // MANDATE 2: Parse and validate event data
          const parsed = parseJobStreamEventJson(event.data);
          if (parsed === null) return;

          if (parsed.type === "complete" || parsed.type === "error") {
            cleanup();
            return;
          }

          setState((prev) => applyJobStreamEvent(prev, parsed));
        } catch (handlerErr) {
          // MANDATE 3: Log but don't break connection
          logError("SSE message handler error", {
            error:
              handlerErr instanceof Error
                ? handlerErr.message
                : String(handlerErr),
            stack: handlerErr instanceof Error ? handlerErr.stack : undefined,
          });
        }
      };

      // ============================================================================
      // MANDATE 3: SSE Error Handler
      // ============================================================================
      es.onerror = (): void => {
        // MANDATE 6: Clear timeout
        if (timeoutRef.current !== null) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }

        // MANDATE 5: Only handle if still the current connection
        if (eventSourceRef.current === es) {
          logWarn("SSE connection error, falling back to polling", {
            jobId: effectJobId,
          });
          setIsConnected(false);
          sseSupportedRef.current = false;
          startPolling();
        }

        // MANDATE 6: Always close the failed connection
        try {
          es.close();
        } catch (closeErr) {
          logWarn("Error closing failed EventSource", {
            error: String(closeErr),
          });
        }
      };
    };

    // ============================================================================
    // Polling Setup
    // ============================================================================
    const startPolling = (): void => {
      // MANDATE 5: Guard against duplicate polling
      if (pollIntervalRef.current !== null) return;

      logWarn("Starting polling fallback", { jobId: effectJobId });

      // MANDATE 3: Immediate first poll with error handling
      void pollJobStatus().catch((err: Error) => {
        logError("Initial poll failed", {
          jobId: effectJobId,
          error: err.message,
        });
      });

      // Set up interval polling
      pollIntervalRef.current = setInterval(() => {
        safeAsync(pollJobStatus(), "jobStream.poll");
      }, POLL_INTERVALS.jobStream);
    };

    // ============================================================================
    // Start Connection
    // ============================================================================
    try {
      trySseConnection();
    } catch (startErr) {
      logError("Failed to start SSE connection", {
        jobId: effectJobId,
        error: String(startErr),
      });
      startPolling();
    }

    // ============================================================================
    // MANDATE 6: Cleanup - Guaranteed cleanup on unmount or jobId change
    // ============================================================================
    return () => {
      isMountedRef.current = false;
      cleanup();
      // Reset SSE support flag for next job
      sseSupportedRef.current = null;
    };
    // MANDATE 5: pollJobStatus is stable (no deps), validatedJobId is the only changing dep
  }, [validatedJobId, pollJobStatus, cleanup]);

  // ============================================================================
  // MANDATE 2: TYPE SAFETY - Safe return with computed properties
  // ============================================================================
  const isStreaming =
    isConnected && (state.status === "queued" || state.status === "running" || state.status === "retrying" || state.status === "waiting_dependency");

  return {
    ...state,
    isConnected,
    error,
    isStreaming,
  };
}
