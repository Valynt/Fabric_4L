import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { createWrapper } from "../test-utils";
import { useValueCaseGenerationInputs } from "./useValueCaseGenerationInputs";

vi.mock(
  "@/features/intelligence-workspace/tabs/_shared/useWorkspaceData",
  () => ({
    useStakeholdersData: vi.fn(),
  })
);

vi.mock("@/hooks/useGroundTruthGovernance", () => ({
  useTruths: vi.fn(),
}));

vi.mock("@/hooks/useROICalculator", () => ({
  useROICalculations: vi.fn(),
}));

import { useStakeholdersData } from "../features/intelligence-workspace/tabs/_shared/useWorkspaceData";
import { useTruths } from "./useGroundTruthGovernance";
import { useROICalculations } from "./useROICalculator";

function mockQuery(
  overrides: Partial<ReturnType<typeof useStakeholdersData>> = {}
) {
  return {
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    isSuccess: true,
    items: [],
    ...overrides,
  };
}

describe("useValueCaseGenerationInputs", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useStakeholdersData as Mock).mockReturnValue(mockQuery({ items: [] }));
    (useTruths as Mock).mockReturnValue(mockQuery({ data: { items: [] } }));
    (useROICalculations as Mock).mockReturnValue(
      mockQuery({ data: { calculations: [] } })
    );
  });

  it("maps live sources into a ValueCaseArtifactsInput draft", async () => {
    (useStakeholdersData as Mock).mockReturnValue(
      mockQuery({
        items: [{ id: "st-1", name: "CFO", role: "Economic Buyer" }],
      })
    );
    (useTruths as Mock).mockReturnValue(
      mockQuery({
        data: { items: [{ id: "truth-1", claim: "Validated efficiency gap" }] },
      })
    );
    (useROICalculations as Mock).mockReturnValue(
      mockQuery({
        data: {
          calculations: [
            {
              id: "roi-1",
              npv: 2_500_000,
              total_roi_pct: 150,
              payback_months: 6,
            },
          ],
        },
      })
    );

    const wrapper = createWrapper();
    const { result } = renderHook(
      () => useValueCaseGenerationInputs("acct-1", "Acme", "case-1"),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isReady).toBe(true));

    expect(result.current.draft.account_id).toBe("acct-1");
    expect(result.current.draft.account_name).toBe("Acme");
    expect(result.current.draft.stakeholders).toEqual(["CFO"]);
    expect(result.current.draft.accepted_evidence).toEqual([
      "Validated efficiency gap",
    ]);
    expect(result.current.draft.scenario_assumptions).toEqual([]);
    expect(result.current.draft.roi_metrics).toEqual({
      three_year_value: "$2.5M",
      roi: "150%",
      payback: "6 months",
    });
    expect(result.current.provenance.stakeholders).toEqual([
      { source: "workspace_stakeholder", id: "st-1" },
    ]);
    expect(result.current.provenance.scenario_assumptions).toEqual([
      { source: "manual" },
    ]);
  });

  it("never returns the legacy hardcoded values", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(
      () => useValueCaseGenerationInputs("acct-1", "Acme", "case-1"),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isReady).toBe(true));

    const json = JSON.stringify(result.current.draft);
    expect(json).not.toContain("Economic buyer");
    expect(json).not.toContain("Business champion");
    expect(json).not.toContain("$1.8M");
    expect(json).not.toContain("214%");
    expect(json).not.toContain("9 months");
  });

  it("reports loading while any source is loading", async () => {
    (useStakeholdersData as Mock).mockReturnValue(
      mockQuery({ isLoading: true, items: [] })
    );

    const wrapper = createWrapper();
    const { result } = renderHook(
      () => useValueCaseGenerationInputs("acct-1", "Acme", "case-1"),
      { wrapper }
    );

    expect(result.current.isLoading).toBe(true);
    expect(result.current.isReady).toBe(false);
  });

  it("reports error when a source fails", async () => {
    const error = new Error("Truths query failed");
    (useTruths as Mock).mockReturnValue(mockQuery({ isError: true, error }));

    const wrapper = createWrapper();
    const { result } = renderHook(
      () => useValueCaseGenerationInputs("acct-1", "Acme", "case-1"),
      { wrapper }
    );

    expect(result.current.isError).toBe(true);
    expect(result.current.error).toBe(error);
    expect(result.current.isReady).toBe(false);
  });

  it("maps disputed truths into risk_notes with l5_truth provenance", async () => {
    (useStakeholdersData as Mock).mockReturnValue(mockQuery({ items: [] }));
    (useTruths as Mock).mockImplementation(
      (params: { status: string }) => {
        if (params.status === "disputed") {
          return mockQuery({
            data: {
              items: [{ id: "risk-1", claim: "Disputed integration risk" }],
            },
          });
        }
        return mockQuery({ data: { items: [] } });
      }
    );
    (useROICalculations as Mock).mockReturnValue(
      mockQuery({ data: { calculations: [] } })
    );

    const wrapper = createWrapper();
    const { result } = renderHook(
      () => useValueCaseGenerationInputs("acct-1", "Acme", "case-1"),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isReady).toBe(true));

    expect(result.current.draft.risk_notes).toEqual([
      "Disputed integration risk",
    ]);
    expect(result.current.provenance.risk_notes).toEqual([
      { source: "l5_truth", id: "risk-1" },
    ]);
  });

  it("falls back to empty inputs when no live sources are available", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(
      () => useValueCaseGenerationInputs("acct-1", "Acme", "case-1"),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isReady).toBe(true));

    expect(result.current.draft).toEqual({
      account_id: "acct-1",
      account_name: "Acme",
      stakeholders: [],
      accepted_evidence: [],
      scenario_assumptions: [],
      roi_metrics: { three_year_value: "", roi: "", payback: "" },
      risk_notes: [],
    });
    expect(result.current.provenance).toEqual({
      account_id: [{ source: "manual" }],
      account_name: [{ source: "manual" }],
      stakeholders: [],
      accepted_evidence: [],
      scenario_assumptions: [{ source: "manual" }],
      roi_metrics: [],
      risk_notes: [],
    });
  });
});
