import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, apiDelete } from '@/api/typedClient';
import { QK } from './queryKeys';
import { withApiError, BaseApiError, STALE_TIME, RETRY_CONFIG } from './useApiShared';

// ── Error Class ─────────────────────────────────────────────────────────────

export class GovernanceApiError extends BaseApiError {
  constructor(message: string, statusCode?: number, responseData?: unknown) {
    super(message, statusCode, responseData);
    this.name = 'GovernanceApiError';
  }
}

// ── Types ───────────────────────────────────────────────────────────────────

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  status: 'active' | 'suspended' | 'deleted';
  plan?: string;
  created_at: string;
  updated_at?: string;
}

export interface User {
  id: string;
  email: string;
  display_name?: string;
  role: 'super_admin' | 'tenant_admin' | 'member' | 'viewer';
  status: 'active' | 'invited' | 'deactivated';
  tenant_id: string;
  created_at: string;
  last_login_at?: string;
}

export interface ApiKey {
  key_id: string;
  name: string;
  prefix: string;
  tenant_id: string;
  role: 'tenant_admin' | 'content_admin' | 'analyst' | 'read_only';
  enabled: boolean;
  revoked_at?: string;
  created_at: string;
  expires_at?: string;
  last_used_at?: string;
}

export interface ApiKeyCreateResponse {
  key_id: string;
  tenant_id: string;
  name: string;
  api_key: string;
  prefix: string;
  role: ApiKey['role'];
  permissions: string[];
  expires_at?: string;
  rate_limit_per_minute?: number;
  created_at: string;
}

// ── Query Keys ──────────────────────────────────────────────────────────────


// ── Fetch Functions ─────────────────────────────────────────────────────────

async function fetchTenants(): Promise<Tenant[]> {
  const response = await apiGet<Tenant[]>('l4', '/tenants');
  return response.data;
}

async function fetchUsers(): Promise<User[]> {
  const response = await apiGet<User[]>('l4', '/users');
  return response.data;
}

async function fetchApiKeys(): Promise<ApiKey[]> {
  const response = await apiGet<ApiKey[]>('l4', '/api-keys');
  return response.data;
}

// ── Hooks ───────────────────────────────────────────────────────────────────

export function useTenants() {
  return useQuery<Tenant[], GovernanceApiError>({
    queryKey: QK.governance.tenants,
    queryFn: () => withApiError(fetchTenants(), GovernanceApiError),
    staleTime: STALE_TIME.list,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

export function useUsers() {
  return useQuery<User[], GovernanceApiError>({
    queryKey: QK.governance.users(),
    queryFn: () => withApiError(fetchUsers(), GovernanceApiError),
    staleTime: STALE_TIME.list,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

export function useApiKeys() {
  return useQuery<ApiKey[], GovernanceApiError>({
    queryKey: QK.governance.apiKeys(),
    queryFn: () => withApiError(fetchApiKeys(), GovernanceApiError),
    staleTime: STALE_TIME.list,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

export function useInviteUser() {
  const queryClient = useQueryClient();

  return useMutation<User, GovernanceApiError, { email: string; role: string }>({
    mutationFn: async (payload) => {
      const response = await apiPost<User>('l4', '/users/invite', payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.governance.users() });
    },
  });
}

export interface AcceptInvitePayload {
  token: string;
  password: string;
  name: string;
}

export interface AcceptInviteResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export function useAcceptInvite() {
  return useMutation<AcceptInviteResponse, GovernanceApiError, AcceptInvitePayload>({
    mutationFn: async (payload) => {
      const response = await apiPost<AcceptInviteResponse>('api', '/auth/accept-invite', payload);
      return response.data;
    },
  });
}

export interface ApiKeyCreateRequest {
  name: string;
  role: ApiKey['role'];
  expires_at?: string;
  permissions?: string[];
  rate_limit_per_minute?: number;
  metadata?: Record<string, unknown>;
}

export function useCreateApiKey() {
  const queryClient = useQueryClient();

  return useMutation<ApiKeyCreateResponse, GovernanceApiError, ApiKeyCreateRequest>({
    mutationFn: async (payload) => {
      const response = await apiPost<ApiKeyCreateResponse>('l4', '/api-keys', payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.governance.apiKeys() });
    },
  });
}

export function useRevokeApiKey() {
  const queryClient = useQueryClient();

  return useMutation<void, GovernanceApiError, string>({
    mutationFn: async (keyId) => {
      await apiDelete<void>('l4', `/api-keys/${keyId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.governance.apiKeys() });
    },
  });
}
