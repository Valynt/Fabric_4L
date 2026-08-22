import { describe, it, expect } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import { valueCaseKeys } from "../queries/valueCaseKeys";
import type { ValueCaseScope } from "../domain/valueCaseModels";

describe("valueCaseCacheReconciliation", () => {
  const scopeA: ValueCaseScope = {
    fabricTenantId: "tenant-A",
    tenantSlug: "slug-a",
    accountId: "account-1",
  };

  const scopeB: ValueCaseScope = {
    fabricTenantId: "tenant-B",
    tenantSlug: "slug-b",
    accountId: "account-2",
  };

  it("partitions query keys by tenantId and accountId", () => {
    const keyA = valueCaseKeys.versions(scopeA);
    const keyB = valueCaseKeys.versions(scopeB);

    expect(keyA).toEqual(["value-case", "scope", "tenant-A", "account-1", "versions"]);
    expect(keyB).toEqual(["value-case", "scope", "tenant-B", "account-2", "versions"]);
    expect(keyA).not.toEqual(keyB);
  });

  it("invalidates only target scoped cache without contaminating unrelated tenants", async () => {
    const queryClient = new QueryClient();

    queryClient.setQueryData(valueCaseKeys.versions(scopeA), [
      { id: "v-1", accountId: "account-1", version: 1 },
    ]);
    queryClient.setQueryData(valueCaseKeys.versions(scopeB), [
      { id: "v-2", accountId: "account-2", version: 1 },
    ]);

    expect(queryClient.getQueryData(valueCaseKeys.versions(scopeA))).toHaveLength(1);
    expect(queryClient.getQueryData(valueCaseKeys.versions(scopeB))).toHaveLength(1);

    // Invalidate scope A only
    await queryClient.invalidateQueries({
      queryKey: valueCaseKeys.scopeRoot(scopeA),
    });

    const queryStateA = queryClient.getQueryState(valueCaseKeys.versions(scopeA));
    const queryStateB = queryClient.getQueryState(valueCaseKeys.versions(scopeB));

    expect(queryStateA?.isInvalidated).toBe(true);
    expect(queryStateB?.isInvalidated).toBe(false);
  });
});
