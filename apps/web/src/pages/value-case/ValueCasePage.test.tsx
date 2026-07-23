import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { createWrapper } from "@/test-utils";
import ValueCasePage from "./ValueCasePage";

vi.mock("@/hooks/useAccounts", () => ({
  useAccount: vi.fn(),
}));

vi.mock("@/hooks/useWorkspaceCase", () => ({
  useCanonicalCaseId: vi.fn(),
}));

vi.mock("@/hooks/useValueCaseArtifacts", () => ({
  useValueCaseArtifacts: vi.fn(),
}));

vi.mock("@/components/value-case/ValueCaseGenerationPanel", () => ({
  ValueCaseGenerationPanel: vi.fn(() => <div data-testid="generation-panel" />),
}));

import { useAccount } from "@/hooks/useAccounts";
import { useCanonicalCaseId } from "@/hooks/useWorkspaceCase";
import { useValueCaseArtifacts } from "@/hooks/useValueCaseArtifacts";
import { ValueCaseGenerationPanel } from "@/components/value-case/ValueCaseGenerationPanel";

const editedDraft = {
  account_id: "acct-1",
  account_name: "Acme",
  stakeholders: ["CFO", "CEO"],
  accepted_evidence: ["Live evidence"],
  scenario_assumptions: ["Assumption"],
  roi_metrics: { three_year_value: "$2.5M", roi: "250%", payback: "6 months" },
  risk_notes: ["Risk"],
};

describe("ValueCasePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useAccount as Mock).mockReturnValue({
      data: { id: "acct-1", name: "Acme" },
      isLoading: false,
    });
    (useCanonicalCaseId as Mock).mockReturnValue({
      data: "case-1",
      isLoading: false,
    });
    (useValueCaseArtifacts as Mock).mockReturnValue({
      versions: [],
      isLoadingVersions: false,
      versionsError: null,
      refetch: vi.fn(),
      selectedVersion: null,
      setSelectedVersionId: vi.fn(),
      generateArtifact: {
        mutate: vi.fn(),
        isPending: false,
        isError: false,
        error: null,
      },
      publishArtifact: {
        mutate: vi.fn(),
        isPending: false,
        isError: false,
        error: null,
      },
    });
    (ValueCaseGenerationPanel as Mock).mockReturnValue(
      <div data-testid="generation-panel" />
    );
  });

  it("opens the generation panel instead of using hardcoded inputs", async () => {
    const wrapper = createWrapper();
    render(<ValueCasePage accountId="acct-1" />, { wrapper });

    fireEvent.click(screen.getByRole("button", { name: /generate/i }));

    await waitFor(() => {
      expect(screen.getByTestId("generation-panel")).toBeInTheDocument();
    });
  });

  it("calls generateArtifact.mutate with the edited draft when generation is confirmed", async () => {
    const generateMutate = vi.fn();
    (useValueCaseArtifacts as Mock).mockReturnValue({
      versions: [],
      isLoadingVersions: false,
      versionsError: null,
      refetch: vi.fn(),
      selectedVersion: null,
      setSelectedVersionId: vi.fn(),
      generateArtifact: {
        mutate: generateMutate,
        isPending: false,
        isError: false,
        error: null,
      },
      publishArtifact: {
        mutate: vi.fn(),
        isPending: false,
        isError: false,
        error: null,
      },
    });
    (ValueCaseGenerationPanel as Mock).mockImplementation(({ onGenerate }) => (
      <button
        data-testid="generation-panel"
        onClick={() => onGenerate(editedDraft)}
      >
        Simulate Confirm
      </button>
    ));

    const wrapper = createWrapper();
    render(<ValueCasePage accountId="acct-1" />, { wrapper });

    fireEvent.click(screen.getByRole("button", { name: /generate/i }));
    await waitFor(() => {
      expect(screen.getByTestId("generation-panel")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /simulate confirm/i }));

    await waitFor(() => {
      expect(generateMutate).toHaveBeenCalledWith(editedDraft);
    });
  });
});
