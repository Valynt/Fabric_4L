import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/typedClient";
import { QK } from "./queryKeys";
import { RETRY_CONFIG, STALE_TIME, withApiError, BaseApiError } from "./useApiShared";

export type ComplianceStatus = "compliant" | "in_progress" | "non_compliant" | "expired" | "not_applicable";

export interface ComplianceEvidenceReference {
  id?: string;
  label: string;
  url?: string;
}

export interface ComplianceFrameworkStatus {
  framework: string;
  status: ComplianceStatus;
  control_coverage_percent: number;
  exceptions_count: number;
  effective_date?: string;
  next_review_date?: string;
  attestation_expires_at?: string;
  owner?: string;
  evidence_references: ComplianceEvidenceReference[];
}

export interface ComplianceStatusResponse {
  items: ComplianceFrameworkStatus[];
  updated_at?: string;
  updated_by?: string;
}

export class ComplianceStatusApiError extends BaseApiError {
  constructor(message: string, statusCode?: number, responseData?: unknown) {
    super(message, statusCode, responseData);
    this.name = "ComplianceStatusApiError";
  }
}

async function fetchComplianceStatus(): Promise<ComplianceStatusResponse> {
  const response = await apiGet<ComplianceStatusResponse>("l4", "/governance/compliance/status");
  return response.data;
}

export function useComplianceStatus() {
  return useQuery<ComplianceStatusResponse, ComplianceStatusApiError>({
    queryKey: QK.governance.complianceStatus(),
    queryFn: () => withApiError(fetchComplianceStatus(), ComplianceStatusApiError),
    staleTime: STALE_TIME.reference,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}
