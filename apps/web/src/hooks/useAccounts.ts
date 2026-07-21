import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { AxiosRequestConfig } from 'axios';
import { z } from 'zod';
import { apiGet, apiPost } from '@/api/typedClient';
import type { l4 } from '@/api/generated';
import { createLogger } from '@/lib/telemetry';
import { QK } from './queryKeys';
import { withApiError, BaseApiError, STALE_TIME, RETRY_CONFIG } from './useApiShared';

export type CRMProvider = 'salesforce' | 'hubspot' | 'manual';
export type SyncStatus = 'synced' | 'pending' | 'failed' | 'stale';

export interface Account {
  id: string;
  name: string;
  domain: string;
  industry?: string;
  stage?: string;
  region?: string;
  segment?: string;
  owner_id?: string;
  owner_name?: string;
  provider: CRMProvider;
  provider_record_id: string;
  sync_status: SyncStatus;
  last_synced_at?: string;
  employees?: number;
  annual_revenue?: number;
  headquarters?: string;
  website?: string;
  opportunities?: Opportunity[];
  created_at: string;
  updated_at: string;
}

export interface Opportunity {
  provider_opportunity_id: string;
  name: string;
  stage: string;
  value?: number;
  probability?: number;
  close_date?: string;
  pipeline?: string;
  last_synced_at?: string;
}

export interface AccountActivity {
  account_id: string;
  interactions: Interaction[];
  total_count: number;
  summary: string;
}

export interface Interaction {
  id: string;
  type: string;
  date: string;
  subject: string;
  duration_minutes?: number;
  notes?: string;
  outcome?: string;
  sender?: string;
}

export interface AccountSyncStatusInfo {
  provider: CRMProvider;
  status: 'idle' | 'running' | 'failed';
  last_sync_at?: string;
  last_successful_sync_at?: string;
  records_synced: number;
  records_updated: number;
  records_failed: number;
  error_message?: string;
}

export interface SyncResult {
  sync_id: string;
  status: 'completed' | 'partial';
  provider?: CRMProvider;
  message: string;
  stats: {
    provider: string;
    synced: number;
    updated: number;
    failed: number;
    errors: string[];
  }[];
}

// Domain-specific error class
export class AccountApiError extends BaseApiError {
  constructor(message: string, statusCode?: number, responseData?: unknown) {
    super(message, statusCode, responseData);
    this.name = 'AccountApiError';
  }
}


const log = createLogger('useAccounts');
const BACKEND_ACCOUNT_UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const SEMANTIC_ACCOUNT_ID_PATTERN = /^acct-[a-z0-9][a-z0-9-]*$/i;

export interface AccountFilters {
  provider?: CRMProvider | 'all';
  stage?: string;
  industry?: string;
  region?: string;
  segment?: string;
  owner_id?: string;
  sync_status?: SyncStatus | 'all';
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface AccountListResponse {
  items: Account[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface FilterOptions {
  industries: string[];
  stages: string[];
  providers: CRMProvider[];
  owners: { id: string; name: string }[];
}

export interface UseAccountsOptions {
  enabled?: boolean;
  suppressAuthRedirect?: boolean;
}

async function fetchAccounts(
  filters: AccountFilters,
  config?: AxiosRequestConfig
): Promise<AccountListResponse> {
  const params = new URLSearchParams();
  if (filters.provider && filters.provider !== 'all') params.set('provider', filters.provider);
  if (filters.stage) params.set('stage', filters.stage);
  if (filters.industry) params.set('industry', filters.industry);
  if (filters.region) params.set('region', filters.region);
  if (filters.segment) params.set('segment', filters.segment);
  if (filters.owner_id) params.set('owner_id', filters.owner_id);
  if (filters.sync_status && filters.sync_status !== 'all') params.set('sync_status', filters.sync_status);
  if (filters.search) params.set('q', filters.search);
  if (filters.page) params.set('page', filters.page.toString());
  if (filters.page_size) params.set('page_size', filters.page_size.toString());
  if (filters.sort_by) params.set('sort_by', filters.sort_by);
  if (filters.sort_order) params.set('sort_order', filters.sort_order);

  const response = await apiGet<AccountListResponse>('l4', `/accounts?${params.toString()}`, config);
  const data = response.data;
  return {
    items: data.items ?? [],
    total: data.total,
    page: data.page,
    page_size: data.page_size,
    has_more: data.has_more ?? false,
  };
}

export function isBackendAccountUuid(accountId: string): boolean {
  return BACKEND_ACCOUNT_UUID_PATTERN.test(accountId);
}

export function isSemanticAccountId(accountId: string): boolean {
  return SEMANTIC_ACCOUNT_ID_PATTERN.test(accountId);
}

function findAccountByRouteId(accounts: Account[], accountId: string): Account | undefined {
  const semanticTokens = accountId
    .replace(/^acct-/i, '')
    .split('-')
    .filter((token) => token && !/^\d+$/.test(token));

  return accounts.find((account) =>
    account.id === accountId ||
    account.provider_record_id === accountId ||
    account.name.toLowerCase() === accountId.toLowerCase() ||
    (semanticTokens.length > 0 && semanticTokens.every((token) => account.name.toLowerCase().includes(token.toLowerCase())))
  );
}

export async function resolveBackendAccountId(accountId: string): Promise<string> {
  if (isBackendAccountUuid(accountId) || !isSemanticAccountId(accountId)) {
    return accountId;
  }

  try {
    const searched = await fetchAccounts({ search: accountId, page_size: 100 });
    const searchMatch = findAccountByRouteId(searched.items, accountId);
    if (searchMatch) return searchMatch.id;
  } catch (error) {
    log.warn('Account route ID search failed; falling back to tenant-scoped account list', {
      accountId,
      error,
    });
  }

  const listed = await fetchAccounts({ page_size: 100 });
  const listMatch = findAccountByRouteId(listed.items, accountId);
  if (listMatch) return listMatch.id;

  throw new AccountApiError(`Account not found for route identifier ${accountId}`, 404);
}

export function useAccounts(filters: AccountFilters = {}, options: UseAccountsOptions = {}) {
  const requestConfig = options.suppressAuthRedirect
    ? { headers: { 'X-Fabric-Skip-Auth-Redirect': '1' } }
    : undefined;

  return useQuery<AccountListResponse, AccountApiError>({
    queryKey: QK.accounts.list(filters),
    queryFn: () => withApiError(fetchAccounts(filters, requestConfig), AccountApiError),
    enabled: options.enabled ?? true,
    staleTime: STALE_TIME.list,
    retry: (failureCount, error) => {
      if (error?.statusCode === 401 || error?.statusCode === 403) {
        return false;
      }

      if (typeof RETRY_CONFIG.maxRetries === 'number') {
        return failureCount < RETRY_CONFIG.maxRetries;
      }

      return RETRY_CONFIG.maxRetries;
    },
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

async function fetchAccount(accountId: string): Promise<Account> {
  const backendAccountId = await resolveBackendAccountId(accountId);
  const response = await apiGet<Account>('l4', `/accounts/${backendAccountId}`);
  return response.data;
}

export function useAccount(accountId: string | null) {
  return useQuery<Account, AccountApiError>({
    queryKey: QK.accounts.detail(accountId || ''),
    queryFn: async () => {
      if (!accountId) throw new AccountApiError('No account ID provided');
      return withApiError(fetchAccount(accountId), AccountApiError);
    },
    enabled: !!accountId,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

async function fetchAccountActivity(accountId: string, sinceDays: number = 90): Promise<AccountActivity> {
  const response = await apiGet<l4.components['schemas']['AccountActivityResponse']>('l4', `/accounts/${accountId}/activity?since_days=${sinceDays}`);
  const data = response.data;
  return {
    account_id: data.account_id,
    total_count: data.total_count,
    summary: data.summary ?? '',
    interactions: data.interactions.map((i: {id: string; type: string; date: string; subject?: string | null; duration_minutes?: number | null; notes?: string | null; outcome?: string | null}) => ({
      id: i.id,
      type: i.type,
      date: i.date,
      subject: i.subject ?? '',
      duration_minutes: i.duration_minutes ?? undefined,
      notes: i.notes ?? undefined,
      outcome: i.outcome ?? undefined,
      sender: undefined,
    })),
  };
}

export function useAccountActivity(accountId: string | null, sinceDays?: number) {
  return useQuery<AccountActivity, AccountApiError>({
    queryKey: QK.accounts.activity(accountId || ''),
    queryFn: async () => {
      if (!accountId) throw new AccountApiError('No account ID provided');
      return withApiError(fetchAccountActivity(accountId, sinceDays), AccountApiError);
    },
    enabled: !!accountId,
    staleTime: STALE_TIME.activity,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

async function fetchSyncStatus(): Promise<AccountSyncStatusInfo[]> {
  const response = await apiGet<AccountSyncStatusInfo[]>('l4', '/accounts/sync-status');
  return response.data;
}

export function useAccountSyncStatus() {
  return useQuery<AccountSyncStatusInfo[], AccountApiError>({
    queryKey: QK.accounts.syncStatus,
    queryFn: () => withApiError(fetchSyncStatus(), AccountApiError),
    staleTime: STALE_TIME.poll,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

async function fetchFilterOptions(): Promise<FilterOptions> {
  const response = await apiGet<FilterOptions>('l4', '/accounts/filters');
  return response.data;
}

export function useAccountFilterOptions() {
  return useQuery<FilterOptions, AccountApiError>({
    queryKey: QK.accounts.filters,
    queryFn: () => withApiError(fetchFilterOptions(), AccountApiError),
    staleTime: STALE_TIME.activity,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

export interface CreateAccountParams {
  id?: string;
  provider: CRMProvider;
  provider_record_id: string;
  name: string;
  domain?: string;
  industry?: string;
  stage?: string;
  region?: string;
  segment?: string;
  company_size?: number;
  annual_revenue?: number;
  headquarters?: string;
  website?: string;
  owner_id?: string;
  owner_name?: string;
  owner_email?: string;
}

export const createAccountPayloadSchema = z.object({
  id: z.uuid().optional(),
  provider: z.enum(['salesforce', 'hubspot', 'manual']),
  provider_record_id: z.string().min(1).max(100),
  name: z.string().min(1).max(255),
  domain: z.string().max(255).optional(),
  industry: z.string().max(100).optional(),
  region: z.string().max(100).optional(),
  company_size: z.number().int().min(0).optional(),
  annual_revenue: z.number().min(0).optional(),
  headquarters: z.string().max(255).optional(),
  website: z.string().max(255).optional(),
  owner_id: z.string().max(100).optional(),
  owner_name: z.string().max(255).optional(),
  owner_email: z.string().max(255).optional(),
  stage: z.string().max(50).optional(),
  segment: z.string().max(100).optional(),
});

export type CreateAccountPayload = z.infer<typeof createAccountPayloadSchema>;

export function buildCreateAccountPayload(params: CreateAccountParams): CreateAccountPayload {
  return createAccountPayloadSchema.parse({
    ...(params.id ? { id: params.id } : {}),
    provider: params.provider,
    provider_record_id: params.provider_record_id,
    name: params.name,
    domain: params.domain,
    industry: params.industry,
    stage: params.stage || 'prospect',
    region: params.region,
    segment: params.segment,
    company_size: params.company_size,
    annual_revenue: params.annual_revenue,
    headquarters: params.headquarters,
    website: params.website,
    owner_id: params.owner_id,
    owner_name: params.owner_name,
    owner_email: params.owner_email,
  });
}

export interface CreateAccountResponse {
  account: Account;
  workflow_id?: string;
}

type CreateAccountApiResponse = CreateAccountResponse | Account;

export interface SyncAccountsParams {
  provider?: CRMProvider;
  account_ids?: string[];
  force_refresh?: boolean;
}

export function useCreateAccount() {
  const queryClient = useQueryClient();

  return useMutation<CreateAccountResponse, AccountApiError, CreateAccountParams>({
    mutationFn: async (params) => {
      const response = await apiPost<CreateAccountApiResponse>('l4', '/accounts', buildCreateAccountPayload(params));
      const data = response.data;
      return 'account' in data ? data : { account: data };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.accounts.list({}) });
    },
    onError: (error) => {
      log.error('CreateAccount failed', { error: error.message });
    },
  });
}

export function useSyncAccounts() {
  const queryClient = useQueryClient();

  return useMutation<SyncResult, AccountApiError, SyncAccountsParams>({
    mutationFn: async (params = {}) => {
      const response = await apiPost<SyncResult>('l4', '/accounts/sync', {
        provider: params.provider,
        account_ids: params.account_ids,
        force_refresh: params.force_refresh || false,
      });
      return response.data;
    },
    onSuccess: () => {
      // Invalidate all account queries to refresh data
      queryClient.invalidateQueries({ queryKey: QK.accounts.list({}) });
    },
    onError: (error) => {
      log.error('SyncAccounts failed', { error: error.message });
    },
  });
}

export function useRefreshAccount() {
  const queryClient = useQueryClient();

  return useMutation<Account, AccountApiError, string>({
    mutationFn: async (accountId: string) => {
      if (!accountId || accountId.trim() === '') {
        throw new AccountApiError('Account ID is required');
      }
      const response = await apiPost<Account>('l4', `/accounts/${accountId}/refresh`, {});
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate to get fresh data from server
      queryClient.invalidateQueries({ queryKey: QK.accounts.detail(data.id) });
      queryClient.invalidateQueries({ queryKey: QK.accounts.list({}) });
    },
    onError: (error, accountId) => {
      log.error('RefreshAccount failed', { accountId, error: error.message });
    },
  });
}
