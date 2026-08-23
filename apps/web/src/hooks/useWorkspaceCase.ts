import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, apiPut, apiPatch } from '@/api/typedClient';
import { QK } from './queryKeys';

const CASE_STORAGE_PREFIX = 'vf.workspace.case';

interface CaseRecord {
  case_id?: string;
  id?: string;
}

function getStoredCaseId(accountId: string): string | null {
  return window.localStorage.getItem(`${CASE_STORAGE_PREFIX}.${accountId}`);
}

function setStoredCaseId(accountId: string, caseId: string) {
  window.localStorage.setItem(`${CASE_STORAGE_PREFIX}.${accountId}`, caseId);
}

/**
 * Detects the 501 soft-success sentinel returned when workspace tab
 * persistence is not implemented (H-01). In that case nothing was persisted,
 * so the tab query must not be invalidated — a refetch would return the
 * empty fallback and clobber local tab state.
 */
function isNotImplementedPersistResult(data: unknown): boolean {
  return (
    typeof data === 'object' &&
    data !== null &&
    'not_implemented' in data &&
    data.not_implemented === true
  );
}

export function useCanonicalCaseId(accountId: string | null) {
  return useQuery<string | null>({
    queryKey: ['workspace', 'case-id', accountId],
    enabled: Boolean(accountId),
    queryFn: async () => {
      if (!accountId) return null;

      const stored = getStoredCaseId(accountId);
      if (stored) return stored;

      const lookup = await apiGet<Record<string, unknown> | Array<Record<string, unknown>>>('l4', `/analysis/cases?account_id=${encodeURIComponent(accountId)}`);
      const lookupData = Array.isArray(lookup.data) ? {} : lookup.data;
      const items = (Array.isArray(lookup.data) ? lookup.data : (lookupData?.items ?? [])) as Array<Record<string, unknown>>;
      const existing = (items[0] ?? {}) as CaseRecord;
      const existingCaseId = existing.case_id || existing.id;
      if (existingCaseId) {
        setStoredCaseId(accountId, existingCaseId);
        return existingCaseId;
      }

      const created = await apiPost<Record<string, unknown>>('l4', '/analysis/cases', {
        account_id: accountId,
        title: `Account ${accountId} workspace`,
      });
      const createdData = created.data as Record<string, unknown>;
      const createdCaseId = String(createdData?.case_id ?? createdData?.id ?? '');
      if (!createdCaseId) throw new Error('Unable to create case for account workspace');
      setStoredCaseId(accountId, createdCaseId);
      return createdCaseId;
    },
  });
}

export function useWorkspaceTabQuery<TData>(caseId: string | null, tabKey: string) {
  return useQuery<TData>({
    queryKey: ['workspace', 'tab', caseId, tabKey],
    enabled: Boolean(caseId),
    queryFn: async () => {
      if (!caseId) throw new Error('Missing case_id');
      try {
        const response = await apiGet<TData>('l4', `/analysis/cases/${caseId}/workspace/${tabKey}`);
        return response.data;
      } catch (error: unknown) {
        // 501 = workspace tab persistence not yet implemented (H-01).
        // Return empty tab data so the UI renders empty states rather than errors.
        const apiError = error as { statusCode?: number };
        if (apiError.statusCode === 501) {
          return { [tabKey]: [] } as TData;
        }
        throw error;
      }
    },
  });
}

export function usePersistWorkspaceTab(tabKey: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: async ({ caseId, payload }: { caseId: string; payload: unknown }) => {
      try {
        const response = await apiPut<unknown>('l4', `/analysis/cases/${caseId}/workspace/${tabKey}`, payload);
        return response.data;
      } catch (error: unknown) {
        // 501 = workspace tab persistence not yet implemented (H-01).
        // Surface as a soft warning so the UI does not crash.
        const apiError = error as { statusCode?: number };
        if (apiError.statusCode === 501) {
          return { case_id: caseId, tab: tabKey, updated: false, not_implemented: true };
        }
        throw error;
      }
    },
    onSuccess: (data, { caseId }) => {
      if (isNotImplementedPersistResult(data)) return;
      queryClient.invalidateQueries({ queryKey: QK.workspace.tab(caseId, tabKey) });
    },
  });

  const persistState: 'idle' | 'saving' | 'saved' | 'failed' =
    mutation.isPending ? 'saving'
    : mutation.isSuccess ? 'saved'
    : mutation.isError ? 'failed'
    : 'idle';

  return { ...mutation, persistState };
}

/**
 * Generate workspace intelligence data (signals, drivers, evidence, stakeholders)
 * for a case. Should be called when workspace is first loaded with empty data.
 */
export function useGenerateWorkspaceIntelligence() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (caseId: string) => {
      const response = await apiPost<{
        case_id: string;
        account_id: string;
        generated: boolean;
        stats: {
          signals: number;
          drivers: number;
          evidence: number;
          stakeholders: number;
        };
      }>('l4', `/analysis/cases/${caseId}/workspace/generate`, {});
      return response.data as {
        case_id: string;
        account_id: string;
        generated: boolean;
        stats: {
          signals: number;
          drivers: number;
          evidence: number;
          stakeholders: number;
        };
      };
    },
    onSuccess: () => {
      // Generation creates signals, drivers, evidence, and stakeholders
      // server-side; refresh every cached workspace tab for the case.
      queryClient.invalidateQueries({ queryKey: QK.workspace.all });
    },
  });
}

export function useSignalReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      signalId,
      accountId,
      reviewStatus,
      decisionNote,
    }: {
      signalId: string;
      accountId: string;
      reviewStatus: 'approved' | 'rejected';
      decisionNote?: string;
    }) => {
      const response = await apiPatch<unknown>('l4', `/v1/signals/${signalId}/review`, {
        account_id: accountId,
        review_status: reviewStatus,
        decision_note: decisionNote,
      });
      return response.data;
    },
    onSuccess: async (_result, vars) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: QK.workspace.all }),
        queryClient.invalidateQueries({ queryKey: QK.workspace.signalReview('unknown-case', vars.accountId) }),
        queryClient.invalidateQueries({ queryKey: QK.accounts.detail(vars.accountId) }),
        queryClient.invalidateQueries({ queryKey: QK.hypotheses.all }),
        queryClient.invalidateQueries({ queryKey: QK.evidence.all }),
      ]);
    },
  });
}


export function useEvidenceDecisionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      evidenceId,
      accountId,
      caseId,
      decision,
      decisionNote,
    }: {
      evidenceId: string;
      accountId: string;
      caseId: string;
      decision: "accepted" | "rejected";
      decisionNote?: string;
    }) => {
      const response = await apiPatch<unknown>('l4', `/v1/evidence/${evidenceId}/decision`, {
        account_id: accountId,
        case_id: caseId,
        decision,
        decision_note: decisionNote,
      });
      return response.data;
    },
    onSuccess: async (_result, vars) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: QK.workspace.evidenceDecision(vars.caseId, vars.accountId) }),
        queryClient.invalidateQueries({ queryKey: ['workspace', 'tab', vars.caseId, 'evidence'] }),
        queryClient.invalidateQueries({ queryKey: QK.calculators.all }),
      ]);
    },
  });
}

// ── Generic workspace page action dispatcher ──────────────────────────────────

export interface WorkspacePageActionContract {
  entityType: 'signal' | 'evidence' | 'hypothesis' | 'scenario';
  entityId: string;
  accountId: string;
  caseId: string;
  intendedOperation: 'signal_review' | 'evidence_attach' | 'hypothesis_convert' | 'scenario_update';
  payload: Record<string, unknown>;
  runMetadataIds?: Record<string, string>;
}

/**
 * Dispatches a workspace page action to the appropriate L4 endpoint and
 * invalidates the relevant workspace tab query on success.
 */
export function useApplyWorkspacePageAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (action: WorkspacePageActionContract) => {
      const { entityType: _entityType, entityId, accountId, caseId, intendedOperation, payload, runMetadataIds } = action;

      switch (intendedOperation) {
        case 'signal_review': {
          const response = await apiPatch<unknown>('l4', `/v1/signals/${entityId}/review`, {
            account_id: accountId,
            review_status: payload.reviewStatus,
            decision_note: payload.decisionNote,
            ...(runMetadataIds ? { run_metadata_ids: runMetadataIds } : {}),
          });
          return response.data;
        }
        case 'evidence_attach': {
          const hypothesisId = encodeURIComponent(String(payload.hypothesisId ?? ''));
          const response = await apiPost<unknown>('l4', `/v1/hypotheses/${hypothesisId}/attach-evidence`, {
            evidence_id: entityId,
            account_id: accountId,
            case_id: caseId,
          });
          return response.data;
        }
        case 'hypothesis_convert': {
          const response = await apiPost<unknown>('l4', `/v1/hypotheses/${entityId}/validate`, {
            new_status: 'converted',
            feedback: payload.feedback,
            account_id: accountId,
            case_id: caseId,
          });
          return response.data;
        }
        case 'scenario_update': {
          const response = await apiPatch<unknown>('l4', `/analysis/cases/${caseId}/workspace/value-model/scenarios/${entityId}`, {
            updates: payload,
            account_id: accountId,
            ...(runMetadataIds ? { run_metadata_ids: runMetadataIds } : {}),
          });
          return response.data;
        }
        default: {
          throw new Error(`Unknown workspace page action: ${intendedOperation}`);
        }
      }
    },
    onSuccess: async (_result, action) => {
      await queryClient.invalidateQueries({ queryKey: ['workspace', 'tab', action.caseId] });
    },
  });
}

/**
 * Get or create the canonical case ID for an account (imperative, non-hook).
 * Mirrors useCanonicalCaseId logic for use in async handlers.
 */
export async function getOrCreateCanonicalCaseId(accountId: string): Promise<string> {
  const stored = getStoredCaseId(accountId);
  if (stored) return stored;

  const lookup = await apiGet<Record<string, unknown> | Array<Record<string, unknown>>>('l4', `/analysis/cases?account_id=${encodeURIComponent(accountId)}`);
  const lookupData = Array.isArray(lookup.data) ? {} : lookup.data;
  const items = (Array.isArray(lookup.data) ? lookup.data : (lookupData?.items ?? [])) as Array<Record<string, unknown>>;
  const existing = (items[0] ?? {}) as CaseRecord;
  const existingCaseId = existing.case_id || existing.id;
  if (existingCaseId) {
    setStoredCaseId(accountId, existingCaseId);
    return existingCaseId;
  }

  const created = await apiPost<Record<string, unknown>>('l4', '/analysis/cases', {
    account_id: accountId,
    title: `Account ${accountId} workspace`,
  });
  const createdData = created.data;
  const createdCaseId = String(createdData?.case_id ?? createdData?.id ?? '');
  if (!createdCaseId) throw new Error('Unable to create case for account workspace');
  setStoredCaseId(accountId, createdCaseId);
  return createdCaseId;
}

/**
 * Persist workspace tab data for a case (imperative, non-hook).
 * Mirrors usePersistWorkspaceTab mutation logic for use in async handlers.
 */
export async function persistWorkspaceTab(caseId: string, tabKey: string, payload: unknown): Promise<unknown> {
  try {
    const response = await apiPut<unknown>('l4', `/analysis/cases/${caseId}/workspace/${tabKey}`, payload);
    return response.data;
  } catch (error: unknown) {
    const apiError = error as { statusCode?: number };
    if (apiError.statusCode === 501) {
      return { case_id: caseId, tab: tabKey, updated: false, not_implemented: true };
    }
    throw error;
  }
}
