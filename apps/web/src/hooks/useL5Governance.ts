import { useQuery } from '@tanstack/react-query';
import { ApiError, buildApiFetchInit } from '@/api/client';
import { QK } from './queryKeys';
import { STALE_TIME } from './useApiShared';

export interface L5Truth {
  truth_id: string;
  claim?: string;
  claim_type?: string;
  status: string;
  maturity_level?: number;
  freshness?: string;
  is_stale?: boolean;
  updated_at?: string;
}

export interface L5TruthListResponse {
  items: L5Truth[];
  total: number;
}

export interface L5MaturityLevel {
  level: number;
  name: string;
  description?: string;
  advancement_criteria?: string[];
}

export interface L5TruthAuditEntry {
  id: string;
  timestamp: string;
  action: string;
  actor?: string;
  notes?: string;
}

export interface L5TruthQueryParams {
  status?: string;
  claim_type?: string;
  is_stale?: boolean;
  limit?: number;
  offset?: number;
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path, buildApiFetchInit());

  if (!response.ok) {
    throw new ApiError(`L5 request failed (${response.status})`, response.status);
  }

  return response.json() as Promise<T>;
}

function buildTruthsPath(params: L5TruthQueryParams = {}): string {
  const search = new URLSearchParams();
  if (params.status) search.set('status', params.status);
  if (params.claim_type) search.set('claim_type', params.claim_type);
  if (typeof params.is_stale === 'boolean') search.set('is_stale', String(params.is_stale));
  if (typeof params.limit === 'number') search.set('limit', String(params.limit));
  if (typeof params.offset === 'number') search.set('offset', String(params.offset));

  const qs = search.toString();
  return qs.length > 0 ? `/api/v1/truths?${qs}` : '/api/v1/truths';
}

export function useL5Truths(params: L5TruthQueryParams = {}) {
  return useQuery({
    queryKey: QK.groundTruth.list(params),
    queryFn: () => fetchJson<L5TruthListResponse>(buildTruthsPath(params)),
    staleTime: STALE_TIME.poll,
  });
}

export function useL5MaturityLadder() {
  return useQuery({
    queryKey: QK.groundTruth.maturityLadder(),
    queryFn: () => fetchJson<L5MaturityLevel[]>('/api/v1/maturity-ladder'),
    staleTime: STALE_TIME.reference,
  });
}

export function useL5TruthAudit(truthId: string | null) {
  return useQuery({
    queryKey: QK.groundTruth.audit(truthId ?? ''),
    queryFn: () => fetchJson<L5TruthAuditEntry[]>(`/api/v1/truths/${encodeURIComponent(truthId || '')}/audit`),
    enabled: Boolean(truthId),
    staleTime: STALE_TIME.activity,
  });
}
