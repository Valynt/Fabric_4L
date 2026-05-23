/**
 * Platform Settings React Query Hooks
 * 
 * Server state management for tenant/platform configuration:
 * - usePlatformSettings: Fetch tenant settings
 * - useUpdatePlatformSettings: Update tenant configuration
 * 
 * All hooks handle loading, error, and caching automatically.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPatch } from '@/api/typedClient';
import { QK } from './queryKeys';
import { withApiError, PlatformSettingsApiError, STALE_TIME, RETRY_CONFIG } from './useApiShared';
import { createLogger } from '@/lib/telemetry';

const log = createLogger('usePlatformSettings');

// ── Types ───────────────────────────────────────────────────────────────────

export interface TenantSettings {
  tenant_id: string;
  tenant_name: string;
  tenant_slug?: string;
  tenant_status?: string;
  tenant_created_at?: string;
  features: {
    advanced_analytics: boolean;
    custom_integrations: boolean;
    ai_assistant: boolean;
    audit_trail: boolean;
  };
  limits: {
    max_users: number;
    max_api_calls_per_day: number;
    storage_gb: number;
  };
  notifications: {
    email_alerts: boolean;
    slack_webhook?: string;
    webhook_url?: string;
  };
  security: {
    require_2fa: boolean;
    session_timeout_minutes: number;
    ip_allowlist: string[];
  };
  branding?: {
    logo_url?: string;
    primary_color?: string;
    accent_color?: string;
    favicon_url?: string;
    custom_domain?: string;
  };
  compliance?: {
    data_residency_region?: string;
    data_residency_self_service?: boolean;
  };
  updated_at: string;
  updated_by?: string;
}

export interface UpdateSettingsPayload {
  tenant_name?: string;
  features?: Partial<TenantSettings['features']>;
  notifications?: Partial<TenantSettings['notifications']>;
  security?: Partial<TenantSettings['security']>;
  branding?: Partial<TenantSettings['branding']>;
  compliance?: Partial<TenantSettings['compliance']>;
}

interface RawTenantSettingsResponse {
  id: string;
  name: string;
  slug?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
  updated_by?: string;
  settings?: Record<string, unknown>;
}

function normalizeTenantSettings(raw: RawTenantSettingsResponse): TenantSettings {
  const settings = raw.settings ?? {};
  const branding = (settings.custom_branding ?? settings.branding ?? {}) as Record<string, unknown>;
  const notificationPreferences = (settings.notification_preferences ?? settings.notifications ?? {}) as Record<string, unknown>;
  const security = (settings.security ?? {}) as Record<string, unknown>;
  const features = (settings.feature_flags ?? settings.features ?? {}) as Record<string, unknown>;
  const limits = (settings.limits ?? {}) as Record<string, unknown>;
  const webhookSource = settings.webhook_url ?? notificationPreferences.webhook_url;

  return {
    tenant_id: raw.id,
    tenant_name: raw.name,
    tenant_slug: raw.slug,
    tenant_status: raw.status,
    tenant_created_at: raw.created_at,
    features: {
      advanced_analytics: Boolean(features.advanced_analytics),
      custom_integrations: Boolean(features.custom_integrations),
      ai_assistant: Boolean(features.ai_assistant),
      audit_trail: features.audit_trail !== false,
    },
    limits: {
      max_users: Number(limits.max_users ?? 25),
      max_api_calls_per_day: Number(limits.max_api_calls_per_day ?? 100000),
      storage_gb: Number(limits.storage_gb ?? 100),
    },
    notifications: {
      email_alerts: notificationPreferences.email_alerts !== false,
      slack_webhook: typeof notificationPreferences.slack_webhook === "string"
        ? notificationPreferences.slack_webhook
        : undefined,
      webhook_url: typeof webhookSource === "string" ? webhookSource : undefined,
    },
    security: {
      require_2fa: security.require_2fa === true || security.require_mfa === true,
      session_timeout_minutes: Number(security.session_timeout_minutes ?? 60),
      ip_allowlist: Array.isArray(security.ip_allowlist)
        ? security.ip_allowlist.filter((value): value is string => typeof value === "string")
        : [],
    },
    branding: {
      logo_url: typeof branding.logo_url === "string" ? branding.logo_url : undefined,
      primary_color: typeof branding.primary_color === "string" ? branding.primary_color : undefined,
      accent_color: typeof branding.accent_color === "string" ? branding.accent_color : undefined,
      favicon_url: typeof branding.favicon_url === "string" ? branding.favicon_url : undefined,
      custom_domain: typeof branding.custom_domain === "string" ? branding.custom_domain : undefined,
    },
    compliance: {
      data_residency_region: typeof settings.data_residency_region === "string"
        ? settings.data_residency_region
        : undefined,
      data_residency_self_service: settings.data_residency_self_service === true,
    },
    updated_at: raw.updated_at ?? raw.created_at ?? "",
    updated_by: raw.updated_by,
  };
}

function serializeTenantSettingsUpdate(payload: UpdateSettingsPayload): { settings: Record<string, unknown> } {
  const settings: Record<string, unknown> = {};

  if (payload.features) {
    settings.feature_flags = payload.features;
  }
  if (payload.notifications) {
    settings.notification_preferences = payload.notifications;
    if (payload.notifications.webhook_url) {
      settings.webhook_url = payload.notifications.webhook_url;
    }
  }
  if (payload.security) {
    settings.security = {
      ...payload.security,
      require_mfa: payload.security.require_2fa,
    };
  }
  if (payload.branding) {
    settings.custom_branding = payload.branding;
  }
  if (payload.compliance) {
    if (payload.compliance.data_residency_region) {
      settings.data_residency_region = payload.compliance.data_residency_region;
    }
    if (typeof payload.compliance.data_residency_self_service === "boolean") {
      settings.data_residency_self_service = payload.compliance.data_residency_self_service;
    }
  }

  return { settings };
}

// ── Fetch Functions ─────────────────────────────────────────────────────────

async function fetchPlatformSettings(): Promise<TenantSettings> {
  const response = await apiGet<RawTenantSettingsResponse>('l4', '/tenants/current/settings');
  return normalizeTenantSettings(response.data);
}

async function updatePlatformSettings(payload: UpdateSettingsPayload): Promise<TenantSettings> {
  const response = await apiPatch<RawTenantSettingsResponse>(
    'l4',
    '/tenants/current/settings',
    serializeTenantSettingsUpdate(payload)
  );
  return normalizeTenantSettings(response.data);
}

// ── Hooks ───────────────────────────────────────────────────────────────────

/**
 * Fetch tenant platform settings
 * 
 * @returns Query result with tenant settings and loading/error states
 * 
 * @example
 * ```tsx
 * const { data: settings, isLoading } = usePlatformSettings();
 * ```
 */
export function usePlatformSettings() {
  return useQuery<TenantSettings, PlatformSettingsApiError>({
    queryKey: QK.platform.settings,
    queryFn: () => withApiError(fetchPlatformSettings(), PlatformSettingsApiError),
    staleTime: STALE_TIME.reference,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

/**
 * Update tenant platform settings
 * 
 * @returns Mutation result with update function
 * 
 * @example
 * ```tsx
 * const updateSettings = useUpdatePlatformSettings();
 * updateSettings.mutate({ 
 *   features: { advanced_analytics: true } 
 * });
 * ```
 */
export function useUpdatePlatformSettings() {
  const queryClient = useQueryClient();

  return useMutation<TenantSettings, PlatformSettingsApiError, UpdateSettingsPayload>({
    mutationFn: (payload) => withApiError(updatePlatformSettings(payload), PlatformSettingsApiError),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.platform.settings });
    },
    onError: (error) => {
      log.error('UpdatePlatformSettings failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

// ── Query Key Extension ─────────────────────────────────────────────────────

// Add to QK in queryKeys.ts:
// platform: {
//   settings: ['platform', 'settings'] as const,
// },
