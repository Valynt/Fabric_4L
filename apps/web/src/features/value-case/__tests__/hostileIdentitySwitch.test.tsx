import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import React, { type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useValueCaseJourney } from "../queries/useValueCaseJourney";
import * as authProvider from "@/auth/AuthorizationProvider";
import * as apiModule from "../api/valueCaseApi";
import type { ApiBusinessCase } from "../api/valueCaseSchemas";

vi.mock("@/auth/AuthorizationProvider", () => ({
  useAuthorizationSnapshot: vi.fn(),
}));

vi.mock("../api/valueCaseApi", () => ({
  fetchAccountApi: vi.fn(),
  fetchValueCasesApi: vi.fn(),
  createValueCaseApi: vi.fn(),
  updateValueCaseApi: vi.fn(),
  publishValueCaseApi: vi.fn(),
}));

vi.mock("@/features/intelligence-workspace/tabs/_shared/useWorkspaceData", () => ({
  useStakeholdersData: () => ({ items: [], isLoading: false, isError: false }),
}));

vi.mock("@/hooks/useGroundTruthGovernance", () => ({
  useTruths: () => ({ data: { items: [] }, isLoading: false, isError: false }),
}));

vi.mock("@/hooks/useROICalculator", () => ({
  useROICalculations: () => ({ data: { calculations: [] }, isLoading: false, isError: false }),
}));

vi.mock("@/hooks/useWorkspaceCase", () => ({
  useCanonicalCaseId: () => ({ data: "case-123" }),
}));

vi.mock("@/hooks/useNarratives", () => ({
  useGenerateNarrative: () => ({
    mutateAsync: vi.fn().mockResolvedValue({
      id: "narrative-1",
      sections: [{ section_type: "executive_summary", title: "Exec Summary", summary: "Summary text" }],
    }),
  }),
}));

describe("Hostile Identity and Scope Switching", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });
  });

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it("fails closed and sets denied state when auth snapshot is unauthenticated / denied", async () => {
    vi.mocked(authProvider.useAuthorizationSnapshot).mockReturnValue({
      status: "denied",
      snapshot: null,
      reason: "unauthenticated",
      hasEveryPermission: () => false,
      hasAnyPermission: () => false,
      hasAnyRole: () => false,
      hasEveryEntitlement: () => false,
      hasAnyEntitlement: () => false,
      hasTenantMembership: () => false,
      hasAccountAccess: () => false,
    });

    const { result } = renderHook(() => useValueCaseJourney("acc-1"), {
      wrapper,
    });

    expect(result.current.lifecycleState).toBe("denied");
    expect(result.current.verifiedScope).toBeNull();
    expect(apiModule.fetchValueCasesApi).not.toHaveBeenCalled();
  });

  it("fails closed when auth snapshot belongs to a different account", async () => {
    vi.mocked(authProvider.useAuthorizationSnapshot).mockReturnValue({
      status: "verified",
      snapshot: {
        schemaVersion: "1",
        source: "backend",
        identity: {
          clerkUserId: "user-1",
          fabricUserId: "f-user-1",
          sessionDiscriminator: "sess-1",
        },
        tenant: {
          fabricTenantId: "tenant-A",
          clerkOrganizationId: "org-1",
          tenantSlug: "slug-a",
          membershipId: "mem-1",
          membershipStatus: "active",
        },
        accountScope: {
          scopeType: "account",
          accountId: "acc-OTHER",
        },
        roles: ["analyst"],
        permissions: ["read:data"],
        entitlements: [],
        issuedAt: new Date().toISOString(),
        expiresAt: new Date(Date.now() + 3600000).toISOString(),
      },
      hasEveryPermission: () => true,
      hasAnyPermission: () => true,
      hasAnyRole: () => true,
      hasEveryEntitlement: () => true,
      hasAnyEntitlement: () => true,
      hasTenantMembership: () => true,
      hasAccountAccess: id => id === "acc-OTHER",
    });

    const { result } = renderHook(() => useValueCaseJourney("acc-1"), {
      wrapper,
    });

    expect(result.current.lifecycleState).toBe("denied");
    expect(result.current.verifiedScope).toBeNull();
    expect(apiModule.fetchValueCasesApi).not.toHaveBeenCalled();
  });

  it("does not mutate active UI if account switches before mutation resolves", async () => {
    let authAccount = "acc-1";
    vi.mocked(authProvider.useAuthorizationSnapshot).mockImplementation(
      () => ({
        status: "verified",
        snapshot: {
          schemaVersion: "1",
          source: "backend",
          identity: {
            clerkUserId: "user-1",
            fabricUserId: "f-user-1",
            sessionDiscriminator: "sess-1",
          },
          tenant: {
            fabricTenantId: "tenant-A",
            clerkOrganizationId: "org-1",
            tenantSlug: "slug-a",
            membershipId: "mem-1",
            membershipStatus: "active",
          },
          accountScope: {
            scopeType: "account",
            accountId: authAccount,
          },
          roles: ["analyst"],
          permissions: ["read:data"],
          entitlements: [],
          issuedAt: new Date().toISOString(),
          expiresAt: new Date(Date.now() + 3600000).toISOString(),
        },
        hasEveryPermission: () => true,
        hasAnyPermission: () => true,
        hasAnyRole: () => true,
        hasEveryEntitlement: () => true,
        hasAnyEntitlement: () => true,
        hasTenantMembership: () => true,
        hasAccountAccess: id => id === authAccount,
      })
    );

    const apiCaseAcc1: ApiBusinessCase = {
      id: "v-acc-1",
      account_id: "acc-1",
      title: "Case Acc 1",
      version: 1,
      status: "draft",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      value_case: {
        inputs: {
          stakeholders: [],
          accepted_evidence: [],
          scenario_assumptions: [],
          roi_metrics: { three_year_value: "$1M", roi_percentage: "100%", payback_period: "12m" },
          risk_notes: [],
        },
        selected_scenario_id: null,
        sections: [],
        assumption_ids: [],
        evidence_ids: [],
        stakeholder_framing: [],
        claim_ids: [],
        roi_snapshot: null,
      },
    };

    let resolveGenerate: (val: ApiBusinessCase) => void;
    const generatePromise = new Promise<ApiBusinessCase>(resolve => {
      resolveGenerate = resolve;
    });

    vi.mocked(apiModule.fetchAccountApi).mockResolvedValue({ id: "acc-1", name: "Acme" });
    vi.mocked(apiModule.fetchValueCasesApi).mockResolvedValue([]);
    vi.mocked(apiModule.createValueCaseApi).mockImplementation(() => generatePromise);

    const { result, rerender } = renderHook(
      ({ accountId }) => useValueCaseJourney(accountId),
      {
        wrapper,
        initialProps: { accountId: "acc-1" },
      }
    );

    await waitFor(() => expect(result.current.lifecycleState).toBe("empty"));

    // Trigger generation for acc-1
    act(() => {
      result.current.generateArtifact.mutate({
        accountId: "acc-1",
        accountName: "Acme",
        stakeholders: ["CEO"],
        acceptedEvidence: [],
        scenarioAssumptions: [],
        roiMetrics: { threeYearValue: "$1M", roi: "100%", payback: "12m" },
        riskNotes: [],
      });
    });

    // Before mutation finishes, switch route to acc-2
    authAccount = "acc-2";
    rerender({ accountId: "acc-2" });

    // Resolve generation for acc-1
    await act(async () => {
      resolveGenerate(apiCaseAcc1);
    });

    // Active result for acc-2 should NOT have selected acc-1's version
    expect(result.current.selectedVersion?.id).not.toBe("v-acc-1");
  });
});
