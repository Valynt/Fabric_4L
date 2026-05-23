import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import HypothesesTab from "./HypothesesTab";
import { createWrapperWithRouterPath } from "@/test-utils";

const navigateMock = vi.fn();
const persistMutateMock = vi.fn();
const validateMutateMock = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...(actual as object),
    useParams: () => ({ accountId: "acc-1" }),
    useNavigate: () => navigateMock,
  };
});

vi.mock("@/agui", () => ({
  useAgentEvents: () => ({ messages: [], sendMessage: vi.fn(), suggestedActions: [], steps: [], isStreaming: false, metadata: null }),
}));

vi.mock("@/hooks/useAccounts", () => ({
  useAccount: () => ({ data: { id: "acc-1", name: "Acme", industry: "Tech", annual_revenue: 1000 }, isLoading: false, error: null }),
}));

vi.mock("@/hooks/useWorkspaceCase", () => ({
  useCanonicalCaseId: () => ({ data: "case-1" }),
  usePersistWorkspaceTab: () => ({ mutate: persistMutateMock }),
}));

vi.mock("@/hooks/useHypotheses", () => ({
  useAccountHypotheses: () => ({ data: { hypotheses: [{ id: "hyp-1", account_id: "acc-1", product_id: "prod-1", signal_id: "sig-1", hypothesis_text: "Reduce onboarding time", confidence: 0.8, status: "draft", evidence_ids: [], created_at: "", updated_at: "" }] }, isLoading: false, error: null }),
  useGenerateHypotheses: () => ({ mutate: vi.fn(), isPending: false }),
  useValidateHypothesis: () => ({
    mutate: validateMutateMock,
    isPending: false,
  }),
  useConvertHypothesisToTree: () => ({ mutate: vi.fn(), isPending: false }),
}));

describe("hypothesis validation to driver flow", () => {
  it("validates a hypothesis, persists drivers, and deep-links to driver tree with provenance", async () => {
    validateMutateMock.mockImplementation((_vars: unknown, opts: { onSuccess?: (result: Record<string, unknown>) => void }) => {
      opts.onSuccess?.({
        status: "updated",
        hypothesis: { id: "hyp-1", account_id: "acc-1" },
        promoted_artifacts: {
          drivers: [{ id: "driver_hyp-1", name: "Onboarding efficiency" }],
          linkages: [{ hypothesis_id: "hyp-1", driver_id: "driver_hyp-1", linkage_id: "vh:hyp-1:driver:driver_hyp-1" }],
          created: true,
        },
      });
    });

    render(<HypothesesTab />, { wrapper: createWrapperWithRouterPath("/intelligence/acc-1/hypotheses") });

    fireEvent.click(screen.getByText(/cost_savings|value hypothesis/i));
    fireEvent.click(screen.getAllByRole("button", { name: "Validate" })[0]);

    await waitFor(() => {
      expect(persistMutateMock).toHaveBeenCalled();
      expect(navigateMock).toHaveBeenCalled();
    });

    expect(navigateMock.mock.calls[0][0].pathname).toBe("/drivers/acc-1/evidence");
    expect(String(navigateMock.mock.calls[0][0].search)).toContain("driver_id=driver_hyp-1");
    expect(String(navigateMock.mock.calls[0][0].search)).toContain("linkage_id=vh%3Ahyp-1%3Adriver%3Adriver_hyp-1");
  });
});
