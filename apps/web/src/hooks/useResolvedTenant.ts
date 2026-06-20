/**
 * useResolvedTenant — canonical Clerk org → Fabric tenant resolution.
 *
 * This hook is the single frontend source of truth for mapping the active
 * Clerk organization to a Fabric tenant. It calls the backend gateway
 * endpoint that verifies the Clerk token and resolves the tenant from the
 * directory. The backend remains the authority; localStorage or frontend
 * state is never trusted.
 *
 * Responsibilities:
 *   - Resolve the active Clerk org to a Fabric tenant via the gateway.
 *   - Expose loading, error, and resolved tenant states.
 *   - Clear the selected account and invalidate tenant/account-scoped cache
 *     when the resolved tenant changes.
 *   - Fail closed: 401/403/500 errors are exposed as error state so callers
 *     can redirect to sign-in, /forbidden, or onboarding as appropriate.
 */
import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth, useOrganization } from "@clerk/react";

import { apiGet } from "@/api/typedClient";
import { withApiError, BaseApiError, STALE_TIME, RETRY_CONFIG } from "./useApiShared";
import { QK } from "./queryKeys";
import { useAccountContextStore } from "@/stores/accountContextStore";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";

export interface ResolvedTenant {
  fabricTenantId: string;
  tenantSlug: string | null;
  clerkOrgId: string;
  status: string;
  roles: string[];
  permissions: string[];
}

export interface UseResolvedTenantResult {
  tenant: ResolvedTenant | null;
  isLoading: boolean;
  error: BaseApiError | null;
}

interface TenantMappingResponse {
  fabric_tenant_id: string;
  tenant_slug: string | null;
  clerk_org_id: string;
  status: string;
  roles: string[];
  permissions: string[];
}

const TENANT_QUERY_KEY = ["auth", "clerk", "tenant"];

function normalizeTenant(response: TenantMappingResponse): ResolvedTenant {
  return {
    fabricTenantId: response.fabric_tenant_id,
    tenantSlug: response.tenant_slug ?? null,
    clerkOrgId: response.clerk_org_id,
    status: response.status,
    roles: response.roles ?? [],
    permissions: response.permissions ?? [],
  };
}

/**
 * Resolve the active Clerk organization to a Fabric tenant.
 *
 * In legacy mode the hook is a no-op (tenant is null, not loading) so existing
 * routes keep working. In Clerk mode it waits for Clerk auth/org to load and
 * then fetches the canonical mapping from the gateway.
 */
export function useResolvedTenant(): UseResolvedTenantResult {
  const queryClient = useQueryClient();
  const clearSelectedAccountId = useAccountContextStore((s) => s.clearSelectedAccountId);
  const syncTenant = useAccountContextStore((s) => s.syncTenant);

  const { isLoaded: authLoaded, isSignedIn, getToken } = useAuth();
  const { isLoaded: orgLoaded, organization } = useOrganization();

  const clerkEnabled = isClerkAuthEnabled();
  const canFetch = clerkEnabled && authLoaded && isSignedIn && orgLoaded && organization != null;

  const query = useQuery<ResolvedTenant, BaseApiError>({
    queryKey: TENANT_QUERY_KEY,
    queryFn: async () => {
      const token = await getToken();
      if (!token) {
        throw new BaseApiError("Authentication required", 401);
      }
      const response = await withApiError(
        apiGet<TenantMappingResponse>("api", "/auth/clerk/tenant", {
          headers: { Authorization: `Bearer ${token}` },
        }),
        BaseApiError
      );
      return normalizeTenant(response.data);
    },
    enabled: canFetch,
    staleTime: STALE_TIME.tenant,
    retry: RETRY_CONFIG.maxRetries,
    refetchOnWindowFocus: false,
  });

  // When the resolved tenant changes, clear the selected account and drop any
  // tenant/account-scoped cache. This prevents stale data from one tenant
  // being shown after an org switch.
  useEffect(() => {
    if (!query.data) {
      return;
    }
    syncTenant();
    clearSelectedAccountId();
    queryClient.invalidateQueries({ queryKey: QK.accounts.all });
  }, [query.data?.fabricTenantId, syncTenant, clearSelectedAccountId, queryClient]);

  return {
    tenant: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ?? null,
  };
}
