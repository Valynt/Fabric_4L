import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { apiGet, apiPost, apiDelete } from "@/api/typedClient";
import type { l4 } from "@/api/generated";
import { QK } from "./queryKeys";
import { STALE_TIME } from "./useApiShared";
import { API_BASE, L4_PREFIX } from "@/lib/apiConfig";
import { POLL_INTERVALS } from "./usePolling";
import { createFeatureLogger } from "@/lib/telemetry";
import { parseJsonValue } from "@/agui/eventSchemas";
import { z } from "zod";
import type { WorkflowState } from "@/api/types";

const log = createFeatureLogger("useWorkflows");

// Constants for workflow SSE
// POLL_INTERVAL_MS removed — use POLL_INTERVALS.workflows from usePolling
const SSE_TIMEOUT_MS = 30 * 1000;
const CANCEL_DELAY_MS = 500;

export interface Workflow {
  id: string;
  name: string;
  status: WorkflowState;
  progress: number;
  createdAt?: string;
  updatedAt?: string;
  traceId?: string;
  correlationId?: string;
  lineageKey?: string;
}

function normalizeWorkflowStatus(status: unknown): WorkflowState {
  const value = typeof status === "string" ? status.toLowerCase() : "";
  const statusMap: Record<string, WorkflowState> = {
    created: "created",
    pending: "queued",
    queued: "queued",
    running: "running",
    waiting_dependency: "waiting_dependency",
    retrying: "retrying",
    paused: "paused",
    interrupted: "interrupted",
    completed: "succeeded",
    succeeded: "succeeded",
    failed: "failed_terminal",
    failed_terminal: "failed_terminal",
    cancelled: "cancelled",
  };
  return statusMap[value] ?? "created";
}

function normalizeWorkflowProgress(rawProgress: unknown): number {
  const numeric =
    typeof rawProgress === "number" ? rawProgress : Number(rawProgress);
  if (Number.isNaN(numeric)) {
    return 0;
  }
  return Math.min(100, Math.max(0, numeric));
}

const WorkflowSseMessageSchema = z.object({
  payload: z.unknown().optional(),
});

export function parseWorkflowSseMessageJson(
  eventJson: string
): RawWorkflow | null {
  try {
    const parsed = WorkflowSseMessageSchema.safeParse(
      parseJsonValue(eventJson)
    );
    if (!parsed.success) {
      log.warn("Failed to validate workflow SSE message", {
        errorCode: parsed.error.issues.map(issue => issue.message).join(", "),
      });
      return null;
    }
    return parsed.data.payload &&
      typeof parsed.data.payload === "object" &&
      !Array.isArray(parsed.data.payload)
      ? (parsed.data.payload as RawWorkflow)
      : null;
  } catch (err) {
    log.warn("Failed to parse SSE message", { errorCode: String(err) });
    return null;
  }
}

interface RawWorkflow {
  id?: string;
  workflow_id?: string;
  workflow_instance_id?: string;
  name?: string;
  workflow_type?: string;
  status?: unknown;
  progress?: unknown;
  progress_percentage?: unknown;
  createdAt?: string;
  created_at?: string;
  updatedAt?: string;
  updated_at?: string;
  started_at?: string;
  completed_at?: string;
  trace_id?: string;
  correlation_id?: string;
  lineage_key?: string;
}

const WorkflowTypeSchema = z.object({
  type: z.string().min(1),
  name: z.string().min(1),
  description: z.string().default(""),
});

const WorkflowTypesResponseSchema = z
  .object({
    workflows: z.array(WorkflowTypeSchema).default([]),
  })
  .passthrough();

function normalizeWorkflow(raw: RawWorkflow): Workflow | null {
  const normalizedIdText = String(raw.id || raw.workflow_id || raw.workflow_instance_id || "").trim();
  if (!normalizedIdText) {
    return null;
  }

  const normalizedName = raw.name || raw.workflow_type || "workflow";
  const normalizedProgress = normalizeWorkflowProgress(
    raw.progress ?? raw.progress_percentage ?? 0
  );

  return {
    id: normalizedIdText,
    name: String(normalizedName),
    status: normalizeWorkflowStatus(raw.status),
    progress: normalizedProgress,
    createdAt: raw.createdAt || raw.created_at,
    updatedAt: raw.updatedAt || raw.updated_at,
    traceId: raw.trace_id,
    correlationId: raw.correlation_id,
    lineageKey: raw.trace_id || raw.correlation_id || raw.lineage_key,
  };
}

function normalizeWorkflowList(data: unknown): Workflow[] {
  const normalized: Workflow[] = [];
  const seen = new Set<string>();

  for (const raw of extractWorkflowList(data)) {
    const workflow = normalizeWorkflow(raw);
    if (!workflow || seen.has(workflow.id)) {
      continue;
    }
    seen.add(workflow.id);
    normalized.push(workflow);
  }

  return normalized;
}

function extractWorkflowList(data: unknown): RawWorkflow[] {
  if (
    data &&
    typeof data === "object" &&
    Array.isArray((data as { items?: unknown[] }).items)
  ) {
    return (data as { items: RawWorkflow[] }).items;
  }

  return [];
}

// Pagination types for new API
export interface PaginatedWorkflows {
  items: Workflow[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

/**
 * Parse API response into PaginatedWorkflows structure.
 * Requires canonical paginated format.
 */
function parsePaginatedResponse(
  data: unknown,
  items: Workflow[]
): PaginatedWorkflows {
  if (data && typeof data === "object" && "items" in data && "total" in data) {
    const paginated = data as PaginatedWorkflows;
    return {
      items,
      total: paginated.total,
      limit: paginated.limit,
      offset: paginated.offset,
      has_more: paginated.has_more,
    };
  }
  throw new Error("Workflow list response is not canonical paginated format");
}

/**
 * Fetch and poll active workflows from Layer 4 with pagination support.
 * Polls every 5 seconds, stops on window focus (already polling).
 *
 * @param limit - Maximum number of workflows to fetch (default: 50, max: 100)
 * @param offset - Number of workflows to skip for pagination (default: 0)
 * @param status - Optional status filter ('created' | 'queued' | 'running' | 'waiting_dependency' | 'retrying' | 'paused' | 'succeeded' | 'failed_terminal' | 'cancelled')
 */
export function useActiveWorkflows(
  options: { limit?: number; offset?: number; status?: string } = {}
) {
  const { limit = 50, offset = 0, status } = options;

  return useQuery<PaginatedWorkflows, Error>({
    queryKey: [...QK.workflows.active(), { limit, offset, status }],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("limit", String(limit));
      params.set("offset", String(offset));
      if (status) params.set("status", status);

      const response = await apiGet<unknown>(
        "l4",
        `/workflows/active?${params.toString()}`
      );
      const items = normalizeWorkflowList(response.data);
      return parsePaginatedResponse(response.data, items);
    },
    staleTime: STALE_TIME.poll,
    refetchInterval: POLL_INTERVALS.workflows,
    refetchOnWindowFocus: false, // Already polling, avoid duplicate fetches
  });
}

export function useWorkflowHistory(
  options: { limit?: number; offset?: number } = {}
) {
  const { limit = 50, offset = 0 } = options;

  return useQuery<PaginatedWorkflows, Error>({
    queryKey: [...QK.workflows.history(), { limit, offset }],
    queryFn: async () => {
      // NOTE: Using /workflows/active with pagination params.
      // Backend now supports limit/offset for paginated workflow lists.
      const params = new URLSearchParams();
      params.set("limit", String(limit));
      params.set("offset", String(offset));

      const response = await apiGet<unknown>(
        "l4",
        `/workflows/active?${params.toString()}`
      );
      const items = normalizeWorkflowList(response.data);
      return parsePaginatedResponse(response.data, items);
    },
    staleTime: STALE_TIME.stats,
  });
}

export function useCreateWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: {
      type: string;
      inputs?: Record<string, unknown>;
      priority?: "CRITICAL" | "HIGH" | "NORMAL" | "LOW" | "BACKGROUND";
    }) => {
      const response = await apiPost<l4.components["schemas"]["WorkflowCreateResponse"] & { workflow_id?: string }>("l4", "/workflows", {
        workflow_type: params.type,
        inputs: {
          custom_data: params.inputs || {},
        },
        priority: params.priority || "NORMAL",
      });
      const workflowId =
        response.data.workflow_instance_id || response.data.workflow_id;
      if (!workflowId) {
        throw new Error("Workflow creation response missing workflow id");
      }
      return String(workflowId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.workflows.active() }).catch((err) =>
        log.error('Invalidate active workflows failed', { error: err instanceof Error ? err.message : String(err) })
      );
      queryClient.invalidateQueries({ queryKey: QK.workflows.history() }).catch((err) =>
        log.error('Invalidate history workflows failed', { error: err instanceof Error ? err.message : String(err) })
      );
    },
    onError: (error) => {
      log.error('CreateWorkflow failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

/**
 * Cancel a running workflow and refresh the workflow lists.
 * Includes a brief delay to allow backend state propagation.
 */
export function useCancelWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await apiDelete<unknown>("l4", `/workflows/${id}`);
    },
    onSuccess: async () => {
      // Brief delay to allow backend to process cancellation
      // before refetching to avoid stale "running" state
      await new Promise(resolve => setTimeout(resolve, CANCEL_DELAY_MS));
      await queryClient.invalidateQueries({ queryKey: QK.workflows.active() }).catch((err) =>
        log.error('Invalidate active workflows failed', { error: err instanceof Error ? err.message : String(err) })
      );
      await queryClient.invalidateQueries({ queryKey: QK.workflows.history() }).catch((err) =>
        log.error('Invalidate history workflows failed', { error: err instanceof Error ? err.message : String(err) })
      );
    },
    onError: (error) => {
      log.error('CancelWorkflow failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

/**
 * Subscribe to workflow updates via Server-Sent Events.
 * Uses useEffect for proper cleanup guarantee when component unmounts.
 */
export function useWorkflowSSE(workflowId: string | null) {
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!workflowId) {
      setWorkflow(null);
      setError(null);
      setIsConnected(false);
      return;
    }

    const url = `${API_BASE}${L4_PREFIX}/workflows/${workflowId}/events`;

    // Close any existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource(url);
    eventSourceRef.current = es;
    setIsConnected(true);
    setError(null);

    // Set up timeout
    timeoutRef.current = setTimeout(() => {
      if (eventSourceRef.current === es) {
        es.close();
        eventSourceRef.current = null;
        setIsConnected(false);
        setError(
          new Error(`SSE connection timeout after ${SSE_TIMEOUT_MS / 1000}s`)
        );
      }
    }, SSE_TIMEOUT_MS);

    es.onmessage = event => {
      const payload = parseWorkflowSseMessageJson(event.data);
      if (!payload) {
        return;
      }

      const normalized = normalizeWorkflow(payload);
      if (normalized) {
        setWorkflow(normalized);
        // Keep connection open for ongoing updates, don't close
      }
    };

    es.onerror = () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (eventSourceRef.current === es) {
        setIsConnected(false);
        setError(new Error("SSE connection failed"));
      }
      es.close();
    };

    // Cleanup function - guaranteed to run on unmount
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      es.close();
      if (eventSourceRef.current === es) {
        eventSourceRef.current = null;
        setIsConnected(false);
      }
    };
  }, [workflowId]);

  return { workflow, error, isConnected };
}

/**
 * Pause a running workflow.
 * POST /workflows/{id}/pause
 */
export function usePauseWorkflow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiPost<l4.components["schemas"]["WorkflowPauseResponse"]>("l4", `/workflows/${id}/pause`, {});
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: QK.workflows.active() }).catch((err) =>
        log.error('Invalidate active workflows failed', { error: err instanceof Error ? err.message : String(err) })
      );
    },
    onError: (error) => {
      log.error('PauseWorkflow failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

/**
 * Resume a paused workflow.
 * POST /workflows/{id}/resume
 */
export function useResumeWorkflow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiPost<l4.components["schemas"]["WorkflowResumeResponse"]>("l4", `/workflows/${id}/resume`, {});
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: QK.workflows.active() }).catch((err) =>
        log.error('Invalidate active workflows failed', { error: err instanceof Error ? err.message : String(err) })
      );
    },
    onError: (error) => {
      log.error('ResumeWorkflow failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

/**
 * Get available workflow types.
 * GET /workflows/types
 */
export function useWorkflowTypes() {
  return useQuery({
    queryKey: [...QK.workflows.all, "types"],
    queryFn: async () => {
      const response = await apiGet<unknown>("l4", "/workflows/types");
      const data = WorkflowTypesResponseSchema.parse(response.data);
      // Normalize backend shape { workflows: [{ type, name, description }] }
      // to frontend shape { types: [{ id, name, description }] }
      return {
        types: data.workflows.map(w => ({
          id: w.type,
          name: w.name,
          description: w.description,
        })),
      };
    },
    staleTime: 60_000,
  });
}
