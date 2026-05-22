import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/typedClient";
import { QK } from "./queryKeys";
import {
  withApiError,
  BaseApiError,
  STALE_TIME,
  RETRY_CONFIG,
} from "./useApiShared";

export interface OperationalAuditEntry {
  id: string;
  timestamp: string;
  source: "access_log";
  event_type: string;
  entity_id: string | null;
  entity_type: string | null;
  action: string;
  agent: string;
  details: Record<string, unknown>;
  event_hash?: string | null;
  event_reference?: string | null;
}

export interface OperationalAuditResponse {
  entries: OperationalAuditEntry[];
  total: number;
  page: number;
  per_page: number;
}

export interface OperationalAuditFilters {
  eventType?: string;
  entityType?: string;
  entityId?: string;
  action?: string;
  actor?: string;
  startDate?: string;
  endDate?: string;
  page?: number;
  perPage?: number;
}

export function buildOperationalAuditParams(filters: OperationalAuditFilters): URLSearchParams {
  const params = new URLSearchParams();
  params.set("source", "access");
  params.set("page", String(filters.page ?? 1));
  params.set("per_page", String(filters.perPage ?? 25));

  if (filters.eventType) params.set("event_type", filters.eventType);
  if (filters.entityType) params.set("entity_type", filters.entityType);
  if (filters.entityId) params.set("entity_id", filters.entityId);
  if (filters.action) params.set("action", filters.action);
  if (filters.actor) params.set("actor", filters.actor);
  if (filters.startDate) params.set("start_date", filters.startDate);
  if (filters.endDate) params.set("end_date", filters.endDate);

  return params;
}

export class OperationalAuditApiError extends BaseApiError {
  constructor(message: string, statusCode?: number, responseData?: unknown) {
    super(message, statusCode, responseData);
    this.name = "OperationalAuditApiError";
  }
}

async function fetchOperationalAudit(
  filters: OperationalAuditFilters
): Promise<OperationalAuditResponse> {
  const params = buildOperationalAuditParams(filters);

  const response = await apiGet<OperationalAuditResponse>(
    "l4",
    `/audit/logs?${params.toString()}`
  );
  return response.data;
}

export function useOperationalAudit(filters: OperationalAuditFilters = {}) {
  return useQuery<OperationalAuditResponse, OperationalAuditApiError>({
    queryKey: [...QK.governance.all, "operational-audit", filters] as const,
    queryFn: () =>
      withApiError(fetchOperationalAudit(filters), OperationalAuditApiError),
    staleTime: STALE_TIME.list,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}
