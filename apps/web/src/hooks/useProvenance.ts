import { useQuery, useMutation } from "@tanstack/react-query";
import { apiGet } from "@/api/typedClient";
import type { l3 } from "@/api/generated";
import { QK } from "./queryKeys";
import { RETRY_CONFIG, STALE_TIME } from "./useApiShared";
import { createLogger } from "@/lib/telemetry";

const log = createLogger("useProvenance");
import {
  parseAuditLogResponse,
  parseProvenanceTrail,
  type AuditLogEntry,
  type AuditLogResponse,
  type ProvenanceStep,
  type ProvenanceTrail,
} from "@/lib/schemas/provenance";

export type {
  AuditLogEntry,
  AuditLogResponse,
  ProvenanceStep,
  ProvenanceTrail,
};

export interface AuditLogFilter {
  source?: "provenance" | "access" | "all";
  from_date?: string;
  to_date?: string;
  entity_type?: string;
  event_type?: string;
  agent?: string;
}

export function useProvenanceTrail(
  entityId: string | null,
  options: { enabled?: boolean; retry?: typeof RETRY_CONFIG.maxRetries | false } = {}
) {
  return useQuery({
    queryKey: QK.provenance.trail(entityId || ""),
    queryFn: async () => {
      if (!entityId) throw new Error("No entity ID provided");
      const response = await apiGet<l3.components['schemas']['ProvenanceTrailResponse']>(
        "l3",
        `/provenance/${encodeURIComponent(entityId)}`
      );
      return parseProvenanceTrail(response.data);
    },
    enabled: Boolean(entityId) && (options.enabled ?? true),
    staleTime: STALE_TIME.activity,
    retry: options.retry ?? RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

export function useAuditLogs(
  filters: AuditLogFilter = {},
  options: { enabled?: boolean; retry?: typeof RETRY_CONFIG.maxRetries | false } = {}
) {
  return useQuery({
    queryKey: QK.provenance.audit(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.source) params.set("source", filters.source);
      if (filters.from_date) params.set("from_date", filters.from_date);
      if (filters.to_date) params.set("to_date", filters.to_date);
      if (filters.entity_type) params.set("entity_type", filters.entity_type);
      if (filters.event_type) params.set("event_type", filters.event_type);
      if (filters.agent) params.set("agent", filters.agent);

      const response = await apiGet<l3.components['schemas']['AuditLogResponse']>(
        "l3",
        `/audit/logs?${params.toString()}`
      );
      return parseAuditLogResponse(response.data);
    },
    staleTime: STALE_TIME.poll,
    enabled: options.enabled ?? true,
    retry: options.retry ?? RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

export function useExportProvenance() {
  return useMutation({
    mutationFn: async ({
      entityId,
      format = "json",
    }: {
      entityId: string;
      format?: "json" | "prov-o";
    }) => {
      const response = await apiGet<l3.components['schemas']['ProvenanceTrailResponse']>(
        "l3",
        `/provenance/${encodeURIComponent(entityId)}?format=${format}`
      );
      return response.data;
    },
    onError: (error) => {
      log.error('ExportProvenance failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}
