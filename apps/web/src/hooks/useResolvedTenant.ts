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
import { useEffect, useRef } from "react";
import { useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { useAuth, useOrganization } from "@clerk/react";

import { apiGet } from "@/api/typedClient";
import { fabric } from "@/api/generated";
import {
  withApiError,
  BaseApiError,
  STALE_TIME,
  RETRY_CONFIG,
} from "./useApiShared";
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

type ClerkTenantResponse = fabric.components["schemas"]["ClerkTenantResponse"];

const TENANT_QUERY_KEY = (orgId: string | null | undefined): QueryKey => [
  "auth",
  "clerk",
  "tenant",
  orgId,
];

function normalizeTenant(response: ClerkTenantResponse): ResolvedTenant {
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

  const { isLoaded: authLoaded, isSignedIn } = useAuth();
  const { isLoaded: orgLoaded, organization } = useOrganization();

  const clerkEnabled = isClerkAuthEnabled();
  const canFetch =
    clerkEnabled &&
    authLoaded &&
    isSignedIn &&
    orgLoaded &&
    organization != null;
  const activeOrgId = organization?.id;

  const previousTenantId = useRef<string | null>(null);
  const previousOrgId = useRef<string | null | undefined>(undefined);

  const query = useQuery<ResolvedTenant, BaseApiError>({
    queryKey: TENANT_QUERY_KEY(activeOrgId),
    queryFn: async () => {
      const response = await withApiError(
        apiGet<ClerkTenantResponse>("api", "/auth/clerk/tenant"),
        BaseApiError
      );
      return normalizeTenant(response.data);
    },
    enabled: canFetch,
    staleTime: STALE_TIME.tenant,
    retry: RETRY_CONFIG.maxRetries,
    refetchOnWindowFocus: false,
  });

  // When the active Clerk org changes, clear the selected account and drop any
  // account-scoped cache immediately. Do the same when the resolved tenant
  // data changes, so stale data from one tenant/organization is never exposed
  // after a switch.
  useEffect(() => {
    if (!clerkEnabled || !authLoaded) return;
    if (!isSignedIn) {
      useAccountContextStore.getState().authorizationUnavailable();
      return;
    }
    if (!orgLoaded) return;
    if (!activeOrgId) {
      useAccountContextStore.getState().authorizationUnavailable();
      return;
    }
    
    if (previousOrgId.current === undefined) {
      previousOrgId.current = activeOrgId;
      return;
    }
    
    if (previousOrgId.current !== activeOrgId) {
      useAccountContextStore.getState().authorizationIdentityChanged();
      previousOrgId.current = activeOrgId;
    }
    queryClient.invalidateQueries({ queryKey: QK.accounts.all });
  }, [activeOrgId, authLoaded, clerkEnabled, isSignedIn, orgLoaded, queryClient]);

  // Only invalidate cache when the actual tenant ID changes, not on every data refresh
  useEffect(() => {
    if (!query.data) {
      if (!query.isLoading && (query.isError || canFetch)) {
        useAccountContextStore.getState().authorizationUnavailable();
      }
      return;
    }
    const currentTenantId = query.data.fabricTenantId;
    if (query.data.status !== "active") {
      useAccountContextStore.getState().authorizationUnavailable();
      return;
    }
    useAccountContextStore.getState().authorizationVerified(currentTenantId);
    if (previousTenantId.current !== currentTenantId) {
      queryClient.invalidateQueries({ queryKey: QK.accounts.all });
      previousTenantId.current = currentTenantId;
    }
  }, [canFetch, query.data, query.isError, query.isLoading, queryClient]);

  return {
    tenant: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error ?? null,
  };
}
