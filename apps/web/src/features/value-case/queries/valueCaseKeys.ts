/**
 * Value Case Query Key Factory
 *
 * Scoped strictly by verified fabricTenantId and accountId to guarantee cache isolation.
 */

export interface ValueCaseKeyScope {
  fabricTenantId: string;
  accountId: string;
}

export interface ValueCaseDetailKeyScope extends ValueCaseKeyScope {
  caseId: string;
}

export interface ValueCaseInputsKeyScope extends ValueCaseKeyScope {
  canonicalCaseId?: string | null;
}

export const valueCaseKeys = {
  all: () => ["value-case"] as const,
  root: () => ["value-case"] as const,

  scopeRoot: ({ fabricTenantId, accountId }: ValueCaseKeyScope) =>
    ["value-case", "scope", fabricTenantId, accountId] as const,

  scope: ({ fabricTenantId, accountId }: ValueCaseKeyScope) =>
    ["value-case", "scope", fabricTenantId, accountId] as const,

  versions: ({ fabricTenantId, accountId }: ValueCaseKeyScope) =>
    ["value-case", "scope", fabricTenantId, accountId, "versions"] as const,

  account: ({ fabricTenantId, accountId }: ValueCaseKeyScope) =>
    ["value-case", "account", fabricTenantId, accountId] as const,

  detail: ({ fabricTenantId, accountId, caseId }: ValueCaseDetailKeyScope) =>
    ["value-case", "detail", fabricTenantId, accountId, caseId] as const,

  generationInputs: ({
    fabricTenantId,
    accountId,
    canonicalCaseId,
  }: ValueCaseInputsKeyScope) =>
    [
      "value-case",
      "generation-inputs",
      fabricTenantId,
      accountId,
      canonicalCaseId ?? "",
    ] as const,
};
