import { describe, it, expect, vi, type Mock } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { createWrapper } from "@/test-utils";
import { ValueCaseGenerationPanel } from "./ValueCaseGenerationPanel";

vi.mock("@/hooks/useValueCaseGenerationInputs", () => ({
  useValueCaseGenerationInputs: vi.fn(),
}));

import { useValueCaseGenerationInputs } from "@/hooks/useValueCaseGenerationInputs";

function mockInputs(
  overrides: Partial<ReturnType<typeof useValueCaseGenerationInputs>> = {}
) {
  return {
    draft: {
      account_id: "acct-1",
      account_name: "Acme",
      stakeholders: ["CFO"],
      accepted_evidence: ["Efficiency gap"],
      scenario_assumptions: ["Ramp in Q1"],
      roi_metrics: {
        three_year_value: "$1.8M",
        roi: "214%",
        payback: "9 months",
      },
      risk_notes: ["Change management"],
    },
    provenance: {
      account_id: [{ source: "manual" as const }],
      account_name: [{ source: "manual" as const }],
      stakeholders: [{ source: "workspace_stakeholder" as const, id: "st-1" }],
      accepted_evidence: [{ source: "l5_truth" as const, id: "truth-1" }],
      scenario_assumptions: [{ source: "manual" as const }],
      roi_metrics: [{ source: "roi_calculation" as const, id: "roi-1" }],
      risk_notes: [{ source: "l5_truth" as const, id: "truth-2" }],
    },
    isLoading: false,
    isError: false,
    error: null,
    isReady: true,
    ...overrides,
  };
}

function renderPanel(
  props: Partial<React.ComponentProps<typeof ValueCaseGenerationPanel>> = {}
) {
  const wrapper = createWrapper();
  return render(
    <ValueCaseGenerationPanel
      accountId="acct-1"
      accountName="Acme"
      caseId="case-1"
      isOpen={true}
      onClose={vi.fn()}
      onGenerate={vi.fn()}
      isGenerating={false}
      {...props}
    />,
    { wrapper }
  );
}

describe("ValueCaseGenerationPanel", () => {
  it("renders live inputs and calls onGenerate with the draft", async () => {
    const onGenerate = vi.fn();
    (useValueCaseGenerationInputs as Mock).mockReturnValue(mockInputs());

    renderPanel({ onGenerate });

    expect(
      screen.getByRole("heading", { name: "Generate Value Case" })
    ).toBeInTheDocument();
    expect(screen.getByText("CFO")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: /generate value case/i })
    );

    await waitFor(() => {
      expect(onGenerate).toHaveBeenCalledWith(
        expect.objectContaining({
          account_id: "acct-1",
          stakeholders: ["CFO"],
        })
      );
    });
  });

  it("does not render legacy hardcoded strings when the draft uses live data", () => {
    const legacyStrings = [
      "Economic buyer",
      "Business champion",
      "Technical evaluator",
      "Validated calculator assumptions",
      "Accepted business pains from discovery",
      "Conservative ramp in Q1",
      "Expected adoption by Q2",
      "$1.8M",
      "214%",
      "9 months",
      "Change management capacity",
      "Competing budget priorities",
    ];

    (useValueCaseGenerationInputs as Mock).mockReturnValue(
      mockInputs({
        draft: {
          account_id: "acct-1",
          account_name: "Acme",
          stakeholders: ["Live economic buyer"],
          accepted_evidence: ["Live evidence from discovery"],
          scenario_assumptions: ["Live adoption assumption"],
          roi_metrics: {
            three_year_value: "$2.1M",
            roi: "150%",
            payback: "6 months",
          },
          risk_notes: ["Live risk note"],
        },
      })
    );

    renderPanel();

    legacyStrings.forEach(text => {
      expect(screen.queryByText(text)).not.toBeInTheDocument();
    });
  });

  it("removes a stakeholder when the remove button is clicked", () => {
    (useValueCaseGenerationInputs as Mock).mockReturnValue(mockInputs());
    renderPanel();

    expect(screen.getByText("CFO")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Remove CFO" }));

    expect(screen.queryByText("CFO")).not.toBeInTheDocument();
  });

  it("adds a stakeholder from the input field", async () => {
    (useValueCaseGenerationInputs as Mock).mockReturnValue(mockInputs());
    renderPanel();

    const input = screen.getByPlaceholderText("Add stakeholder");
    fireEvent.change(input, { target: { value: "CEO" } });
    fireEvent.click(screen.getByRole("button", { name: "Add Stakeholders" }));

    await waitFor(() => {
      expect(screen.getByText("CEO")).toBeInTheDocument();
    });
  });

  it("edits ROI inputs and passes the updated values to onGenerate", async () => {
    const onGenerate = vi.fn();
    (useValueCaseGenerationInputs as Mock).mockReturnValue(mockInputs());
    renderPanel({ onGenerate });

    const valueInput = screen.getByLabelText("3-Year Value");
    fireEvent.change(valueInput, { target: { value: "$2.5M" } });

    fireEvent.click(
      screen.getByRole("button", { name: /generate value case/i })
    );

    await waitFor(() => {
      expect(onGenerate).toHaveBeenCalledWith(
        expect.objectContaining({
          roi_metrics: expect.objectContaining({ three_year_value: "$2.5M" }),
        })
      );
    });
  });

  it("disables Generate when there is no minimum data", () => {
    (useValueCaseGenerationInputs as Mock).mockReturnValue(
      mockInputs({
        draft: {
          account_id: "acct-1",
          account_name: "Acme",
          stakeholders: [],
          accepted_evidence: [],
          scenario_assumptions: [],
          roi_metrics: { three_year_value: "", roi: "", payback: "" },
          risk_notes: [],
        },
        isReady: true,
      })
    );
    renderPanel();

    expect(
      screen.getByRole("button", { name: /generate value case/i })
    ).toBeDisabled();
  });

  it("shows a loading alert while workspace data is loading", () => {
    (useValueCaseGenerationInputs as Mock).mockReturnValue(
      mockInputs({ isLoading: true })
    );
    renderPanel();

    expect(screen.getByText("Loading workspace data…")).toBeInTheDocument();
  });

  it("shows an error alert when workspace data fails to load", () => {
    const error = new Error("Stakeholders query failed");
    (useValueCaseGenerationInputs as Mock).mockReturnValue(
      mockInputs({ isError: true, error })
    );
    renderPanel();

    expect(screen.getByText("Stakeholders query failed")).toBeInTheDocument();
  });

  it("preserves user edits when the draft is refetched", async () => {
    const initialDraft = mockInputs().draft;
    const refetchedDraft = {
      ...initialDraft,
      roi_metrics: { ...initialDraft.roi_metrics, three_year_value: "$2.0M" },
    };

    (useValueCaseGenerationInputs as Mock).mockReturnValue(
      mockInputs({ draft: initialDraft })
    );
    const { rerender } = renderPanel();

    const valueInput = screen.getByLabelText("3-Year Value");
    fireEvent.change(valueInput, { target: { value: "$2.5M" } });

    (useValueCaseGenerationInputs as Mock).mockReturnValue(
      mockInputs({ draft: refetchedDraft })
    );
    rerender(
      <ValueCaseGenerationPanel
        accountId="acct-1"
        accountName="Acme"
        caseId="case-1"
        isOpen={true}
        onClose={vi.fn()}
        onGenerate={vi.fn()}
        isGenerating={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByLabelText("3-Year Value")).toHaveValue("$2.5M");
    });
    expect(screen.queryByDisplayValue("$2.0M")).not.toBeInTheDocument();
  });

  it("reloads from workspace when the reload button is clicked", async () => {
    const initialDraft = mockInputs().draft;
    const refetchedDraft = {
      ...initialDraft,
      roi_metrics: { ...initialDraft.roi_metrics, three_year_value: "$2.0M" },
    };

    (useValueCaseGenerationInputs as Mock).mockReturnValue(
      mockInputs({ draft: refetchedDraft })
    );
    renderPanel();

    const valueInput = screen.getByLabelText("3-Year Value");
    fireEvent.change(valueInput, { target: { value: "$2.5M" } });

    fireEvent.click(
      screen.getByRole("button", { name: "Reload from workspace" })
    );

    await waitFor(() => {
      expect(screen.getByLabelText("3-Year Value")).toHaveValue("$2.0M");
    });
  });

  it("shows a confirmation dialog when closing with unsaved edits", async () => {
    const onClose = vi.fn();
    (useValueCaseGenerationInputs as Mock).mockReturnValue(mockInputs());
    renderPanel({ onClose });

    const valueInput = screen.getByLabelText("3-Year Value");
    fireEvent.change(valueInput, { target: { value: "$2.5M" } });

    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    expect(
      screen.getByText("Discard unsaved changes?")
    ).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: /discard changes/i }));

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("keeps the panel open when the user chooses to keep editing", async () => {
    const onClose = vi.fn();
    (useValueCaseGenerationInputs as Mock).mockReturnValue(mockInputs());
    renderPanel({ onClose });

    const valueInput = screen.getByLabelText("3-Year Value");
    fireEvent.change(valueInput, { target: { value: "$2.5M" } });

    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    fireEvent.click(screen.getByRole("button", { name: /keep editing/i }));

    await waitFor(() => {
      expect(
        screen.queryByText("Discard unsaved changes?")
      ).not.toBeInTheDocument();
    });
    expect(onClose).not.toHaveBeenCalled();
  });

  it("closes immediately when there are no unsaved edits", async () => {
    const onClose = vi.fn();
    (useValueCaseGenerationInputs as Mock).mockReturnValue(mockInputs());
    renderPanel({ onClose });

    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled();
    });
    expect(
      screen.queryByText("Discard unsaved changes?")
    ).not.toBeInTheDocument();
  });

  it("renders source badges for live data sections", () => {
    (useValueCaseGenerationInputs as Mock).mockReturnValue(mockInputs());
    renderPanel();

    expect(screen.getAllByText("from Workspace").length).toBeGreaterThanOrEqual(
      1
    );
    expect(screen.getAllByText("from Ground Truth").length).toBe(2);
    expect(screen.getByText("from ROI Calculator")).toBeInTheDocument();
    expect(screen.getByText("from Manual")).toBeInTheDocument();
  });
});
