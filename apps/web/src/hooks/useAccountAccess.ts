import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/typedClient";
import { createFeatureLogger } from "@/lib/telemetry";

const log = createFeatureLogger("use-account-access");

type AccountAccessResponse = {
  account_exists: boolean;
  tenant_bound: boolean;
  principal_allowed: boolean;
  reason: string;
};

export function useAccountAccess(accountId: string | undefined, tenantSlug: string | undefined) {
  const query = useQuery({
    queryKey: ["authz", "account-access", tenantSlug ?? null, accountId ?? null],
    queryFn: async () => {
      const response = await apiGet<AccountAccessResponse>(
        "l4",
        `/v1/authz/accounts/${encodeURIComponent(accountId ?? "")}/access?tenant_slug=${encodeURIComponent(tenantSlug ?? "")}`
      );
      return response.data;
    },
    enabled: Boolean(accountId && tenantSlug),
    retry: false,
  });

  const hasAccountAccess =
    Boolean(accountId && tenantSlug) &&
    !query.isLoading &&
    !query.isError &&
    query.data?.account_exists === true &&
    query.data?.tenant_bound === true &&
    query.data?.principal_allowed === true;

  if (query.isError) {
    log.warn("Account ACL verification failed; denying by default", {
      accountId,
      tenantSlug,
    });
  }

  return {
    hasAccountAccess,
    denyReason: query.data?.reason ?? (query.isError ? "authorization_service_error" : undefined),
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
