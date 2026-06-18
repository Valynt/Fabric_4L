import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { createWrapperWithRouterPath } from "@/test-utils";
import ValueModelTab from "@/pages/studio/ValueModelTab";

const mockUseParams = vi.fn(() => ({ accountId: "acc-1" }));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...(actual as object), useParams: () => mockUseParams() };
});

vi.mock("@/hooks/useAccounts", () => ({
  useAccount: () => ({ data: { id: "acc-1", name: "Acme", industry: "Tech", annual_revenue: 1000 }, isLoading: false }),
}));

vi.mock("@/hooks/useWorkspaceCase", () => ({
  useCanonicalCaseId: () => ({ data: "case-1" }),
  usePersistWorkspaceTab: () => ({ mutate: vi.fn() }),
  useGenerateWorkspaceIntelligence: () => ({ isPending: false, isError: false, mutate: vi.fn() }),
  useApplyWorkspacePageAction: () => ({ mutateAsync: vi.fn() }),
  useWorkspaceTabQuery: (_caseId: string | null, tab: string) => {
    if (tab === "evidence") return { data: { evidence: [{ id: "ev-1", title: "Validated headcount baseline", decision_status: "accepted", provenance_id: "prov-22" }] } };
    if (tab === "value-model") return { data: { valueLines: [{ id: "v1", driver: "Labor", category: "hard", conservative: 1, expected: 2, optimistic: 3, source: "ev-1" }] }, isLoading: false, error: null };
    return { data: undefined, isLoading: false, error: null };
  },
}));

vi.mock("@/hooks/useROICalculator", () => ({
  useCalculateROI: () => ({ mutate: vi.fn() }),
  useIndustryBenchmarks: () => ({ data: null }),
}));

describe("evidence acceptance downstream visibility", () => {
  it("shows accepted evidence and linkage IDs in value model", () => {
    render(<ValueModelTab accountId="acc-1" />, { wrapper: createWrapperWithRouterPath("/t/acme/accounts/acc-1/studio/value-model") });
    expect(screen.getByText(/accepted evidence inputs/i)).toBeInTheDocument();
    expect(screen.getByText(/Validated headcount baseline/i)).toBeInTheDocument();
    expect(screen.getByText(/Linkage ID: prov-22/i)).toBeInTheDocument();
  });
});
