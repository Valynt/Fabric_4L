/**
 * useJobStream.utils.ts - Pure helpers for job stream event parsing and state reduction
 *
 * These functions have no React or browser-API dependencies and can be unit tested
 * without jsdom or an SSE mock.
 *
 * DEFENSIVE PROGRAMMING: All 7 mandates applied:
 * - M1: NULL/UNDEFINED SAFETY - Optional chaining and nullish coalescing throughout
 * - M2: TYPE SAFETY - Zod runtime validation replaces all `as` assertions
 * - M3: ERROR HANDLING - Every async operation has try/catch with context logging
 * - M4: INPUT VALIDATION - SSE data validated
 * - M5: RACE CONDITION ELIMINATION - Pure functions, no shared mutable state
 * - M6: RESOURCE LEAK PREVENTION - No resources held
 * - M7: BOUNDS SAFETY - All array operations have length checks
 */
import { z } from "zod";
import { parseJsonValue } from "@/agui/eventSchemas";
import { createFeatureLogger } from "@/lib/telemetry";
import type { WorkflowState } from "@/api/types";

// ============================================================================
// MANDATE 2: TYPE SAFETY - Zod Schemas for Runtime Validation
// ============================================================================

export const JobStreamEventTypeSchema = z.enum([
  "progress",
  "status",
  "log",
  "entity",
  "complete",
  "error",
]);

export const JobStreamEventSchema = z.object({
  type: JobStreamEventTypeSchema,
  timestamp: z.string().optional(),
  data: z.unknown(),
});

export const LogEntrySchema = z.object({
  timestamp: z.string().default(""),
  level: z.string().default("INFO"),
  message: z.string().default(""),
});

export const EntityEntrySchema = z.object({
  type: z.string().default("unknown"),
  name: z.string().default("Unknown"),
});

/** Validated job stream event type */
export type JobStreamEvent = z.infer<typeof JobStreamEventSchema>;

// ============================================================================
// MANDATE 3: ERROR HANDLING - Safe Logging Wrapper
// ============================================================================

const log = createFeatureLogger("use-job-stream");

export function logWarn(message: string, context?: Record<string, unknown>): void {
  log.warn(message, context);
}

export function logError(message: string, context?: Record<string, unknown>): void {
  log.error(message, context);
}

// ============================================================================
// Types
// ============================================================================

export interface JobStreamState {
  progress: number;
  status: WorkflowState;
  logs: Array<{
    timestamp: string;
    level: string;
    message: string;
  }>;
  entities: Array<{
    type: string;
    name: string;
  }>;
}

// ============================================================================
// MANDATE 2: TYPE SAFETY - Runtime Validation Functions
// ============================================================================

/**
 * Validates unknown payload against JobStreamEvent schema.
 * Returns validated event or null if invalid.
 */
export function parseJobStreamEvent(
  eventPayload: unknown
): JobStreamEvent | null {
  const result = JobStreamEventSchema.safeParse(eventPayload);
  if (!result.success) {
    logWarn("Failed to parse job stream event", {
      error: result.error.issues.map(i => i.message).join(", "),
      payload: eventPayload,
    });
    return null;
  }
  return result.data;
}

export function parseJobStreamEventJson(
  eventJson: string
): JobStreamEvent | null {
  try {
    return parseJobStreamEvent(parseJsonValue(eventJson));
  } catch (parseErr) {
    logWarn("Failed to parse SSE JSON", {
      data: eventJson,
      error: String(parseErr),
    });
    return null;
  }
}

/**
 * MANDATE 1: NULL/UNDEFINED SAFETY - Safe record check
 */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseLogEntry(data: unknown): JobStreamState["logs"][number] | null {
  if (!isRecord(data)) return null;
  const result = LogEntrySchema.safeParse({
    timestamp: data.timestamp,
    level: data.level,
    message: data.message,
  });
  return result.success
    ? result.data
    : {
        timestamp: "",
        level: "INFO",
        message: "",
      };
}

export function parseEntityEntry(data: unknown): JobStreamState["entities"][number] | null {
  if (!isRecord(data)) return null;
  const result = EntityEntrySchema.safeParse({
    type: data.type,
    name: data.name,
  });
  return result.success
    ? result.data
    : {
        type: "unknown",
        name: "Unknown",
      };
}

export function applyJobStreamEvent(
  previous: JobStreamState,
  event: JobStreamEvent,
): JobStreamState {
  switch (event.type) {
    case "progress":
      return {
        ...previous,
        progress: typeof event.data === "number" ? event.data : previous.progress,
      };

    case "status":
      return {
        ...previous,
        status: mapJobStatus(typeof event.data === "string" ? event.data : ""),
      };

    case "log": {
      const logEntry = parseLogEntry(event.data);
      return logEntry ? { ...previous, logs: [...previous.logs, logEntry] } : previous;
    }

    case "entity": {
      const entity = parseEntityEntry(event.data);
      return entity ? { ...previous, entities: [...previous.entities, entity] } : previous;
    }

    case "complete":
    case "error":
      return previous;
  }
}

// ============================================================================
// MANDATE 2: TYPE SAFETY - Exhaustive status mapping with fallback
// ============================================================================
export function mapJobStatus(status: string): JobStreamState["status"] {
  const statusMap: Record<string, JobStreamState["status"]> = {
    PENDING: "created",
    QUEUED: "queued",
    VALIDATING: "running",
    BROWSER_ACQUIRING: "running",
    NAVIGATING: "running",
    EXTRACTING: "running",
    TRANSFORMING: "running",
    STORING: "running",
    COMPLETED: "succeeded",
    FAILED: "failed_terminal",
    CANCELLED: "cancelled",
    PARTIAL_SUCCESS: "succeeded",
  };

  // MANDATE 1: NULL/UNDEFINED SAFETY - Return default if status not found
  return statusMap[status] ?? "created";
}
