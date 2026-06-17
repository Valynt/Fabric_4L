/**
 * Data hooks for the core value-case workspace views.
 *
 * Each view resolves the canonical case for the active account and reads its
 * tab payload. When persistence is not yet implemented the underlying query
 * returns empty arrays, so the screens render their (clickable) empty states
 * rather than errors.
 */
import { useParams } from "react-router-dom";
import {
  useCanonicalCaseId,
  useWorkspaceTabQuery,
} from "@/hooks/useWorkspaceCase";
import type {
  WorkspaceDriver,
  WorkspaceEvidenceItem,
  WorkspaceSignal,
  WorkspaceStakeholder,
} from "./types";

export function useWorkspaceCaseId() {
  const { accountId } = useParams<{ accountId: string }>();
  const resolvedAccountId = accountId ?? "";
  const query = useCanonicalCaseId(resolvedAccountId || null);
  return {
    accountId: resolvedAccountId,
    caseId: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error as Error | null,
  };
}

export function useSignalsData(caseId: string | null) {
  const query = useWorkspaceTabQuery<{ signals: WorkspaceSignal[] }>(caseId, "signals");
  return { ...query, items: query.data?.signals ?? [] };
}

export function useDriversData(caseId: string | null) {
  const query = useWorkspaceTabQuery<{ drivers: WorkspaceDriver[] }>(caseId, "drivers");
  return { ...query, items: query.data?.drivers ?? [] };
}

export function useEvidenceData(caseId: string | null) {
  const query = useWorkspaceTabQuery<{ evidence: WorkspaceEvidenceItem[] }>(caseId, "evidence");
  return { ...query, items: query.data?.evidence ?? [] };
}

export function useStakeholdersData(caseId: string | null) {
  const query = useWorkspaceTabQuery<{ stakeholders: WorkspaceStakeholder[] }>(caseId, "stakeholders");
  return { ...query, items: query.data?.stakeholders ?? [] };
}
