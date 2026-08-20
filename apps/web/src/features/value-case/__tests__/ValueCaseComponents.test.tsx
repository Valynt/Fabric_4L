import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ValueCaseMetrics } from "../components/ValueCaseMetrics";
import { ValueCaseResult } from "../components/ValueCaseResult";
import { ValueCaseVersionHistory } from "../components/ValueCaseVersionHistory";
import { ValueCaseGenerationPanel } from "../components/ValueCaseGenerationPanel";
import type {
  ValueCaseMetricCardViewModel,
  ValueCaseResultViewModel,
  ValueCaseVersionSummaryViewModel,
  ValueCaseVersionDiffViewModel,
} from "../presentation/valueCaseViewModels";
import type {
  ValueCaseGenerationInputsDraft,
  ValueCaseInputProvenanceMap,
  ValueCaseInputAvailability,
} from "../domain/valueCaseModels";

describe("Value Case Presentational Components", () => {
  describe("ValueCaseMetrics", () => {
    it("renders metric cards with formatted values and labels", () => {
      const metrics: ValueCaseMetricCardViewModel[] = [
        {
          key: "three_year_value",
          label: "3-Year Value",
          formattedValue: "$2.5M",
          rawValue: "$2.5M",
          description: "Projected cumulative NPV",
          isAvailable: true,
        },
        {
          key: "roi",
          label: "ROI",
          formattedValue: "250%",
          rawValue: "250%",
          description: "Total Return on Investment",
          isAvailable: true,
        },
        {
          key: "payback",
          label: "Payback",
          formattedValue: "6 months",
          rawValue: "6 months",
          description: "Payback Period",
          isAvailable: true,
        },
      ];

      render(<ValueCaseMetrics metrics={metrics} />);

      expect(screen.getByText("3-Year Value")).toBeInTheDocument();
      expect(screen.getByText("$2.5M")).toBeInTheDocument();
      expect(screen.getByText("ROI")).toBeInTheDocument();
      expect(screen.getByText("250%")).toBeInTheDocument();
      expect(screen.getByText("Payback")).toBeInTheDocument();
      expect(screen.getByText("6 months")).toBeInTheDocument();
    });
  });

  describe("ValueCaseResult", () => {
    const resultVm: ValueCaseResultViewModel = {
      id: "v-1",
      version: 1,
      versionLabel: "v1",
      isPublished: false,
      statusBadgeVariant: "secondary",
      statusBadgeLabel: "Draft",
      createdAtFormatted: "Jan 1, 2026",
      narrativeTitle: "Acme Business Case",
      narrativeSections: [
        { heading: "Strategic Pillars", content: "Accelerating platform scale." },
      ],
      businessCaseSummary: "Executive summary for Acme.",
      metrics: [],
      stakeholderFraming: [
        { role: "CFO", priorities: ["OPEX"], valueMessage: "Low risk" },
      ],
      risks: ["Integration delay"],
    };

    it("renders narrative, summary, stakeholders, and risks", () => {
      render(<ValueCaseResult result={resultVm} onPublish={vi.fn()} />);

      expect(screen.getByText("Acme Business Case")).toBeInTheDocument();
      expect(screen.getByText("Draft")).toBeInTheDocument();
      expect(screen.getByText("Executive summary for Acme.")).toBeInTheDocument();
      expect(screen.getByText("Strategic Pillars")).toBeInTheDocument();
      expect(screen.getByText("Accelerating platform scale.")).toBeInTheDocument();
      expect(screen.getByText("CFO")).toBeInTheDocument();
      expect(screen.getByText("Integration delay")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /publish artifact/i })).toBeInTheDocument();
    });

    it("calls onPublish when publish button is clicked", () => {
      const onPublish = vi.fn();
      render(<ValueCaseResult result={resultVm} onPublish={onPublish} />);

      fireEvent.click(screen.getByRole("button", { name: /publish artifact/i }));
      expect(onPublish).toHaveBeenCalledWith("v-1");
    });
  });

  describe("ValueCaseVersionHistory", () => {
    const versions: ValueCaseVersionSummaryViewModel[] = [
      {
        id: "v-1",
        version: 1,
        label: "v1",
        isPublished: false,
        statusLabel: "Draft",
        createdAtFormatted: "Jan 1, 2026",
        title: "Initial Case",
        summary: "Summary v1",
      },
      {
        id: "v-2",
        version: 2,
        label: "v2",
        isPublished: true,
        statusLabel: "Published",
        createdAtFormatted: "Jan 2, 2026",
        title: "Updated Case",
        summary: "Summary v2",
      },
    ];

    const diff: ValueCaseVersionDiffViewModel = {
      priorVersion: 1,
      currentVersion: 2,
      roiDiff: "100% → 250%",
      paybackDiff: "12 mo → 6 mo",
      valueDiff: "$1M → $2.5M",
      risksCountDiff: "2 risks → 1 risks",
      hasChanges: true,
    };

    it("renders version buttons and diff overview", () => {
      const onSelect = vi.fn();
      render(
        <ValueCaseVersionHistory
          versions={versions}
          selectedVersionId="v-2"
          onSelectVersion={onSelect}
          diff={diff}
        />
      );

      expect(screen.getByRole("button", { name: /v1/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /v2/i })).toBeInTheDocument();
      expect(screen.getByText("100% → 250%")).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: /v1/i }));
      expect(onSelect).toHaveBeenCalledWith("v-1");
    });
  });

  describe("ValueCaseGenerationPanel", () => {
    const draft: ValueCaseGenerationInputsDraft = {
      stakeholders: ["CFO"],
      acceptedEvidence: ["Evidence A"],
      scenarioAssumptions: [],
      roiMetrics: {
        threeYearValue: "$2.0M",
        roi: "200%",
        payback: "8 months",
      },
      riskNotes: ["Risk A"],
    };

    const provenance: ValueCaseInputProvenanceMap = {
      stakeholders: [{ source: "workspace_stakeholder" }],
      acceptedEvidence: [{ source: "l5_truth" }],
      scenarioAssumptions: [],
      roiMetrics: [{ source: "roi_calculation" }],
      riskNotes: [{ source: "l5_truth" }],
    };

    const availability: ValueCaseInputAvailability = {
      hasPartialFailures: false,
      failedSources: [],
      statusMessage: "All sources loaded",
    };

    it("renders editable inputs and emits generation request", () => {
      const onGenerate = vi.fn();
      render(
        <ValueCaseGenerationPanel
          accountName="Acme Corp"
          isOpen={true}
          onClose={vi.fn()}
          onGenerate={onGenerate}
          isGenerating={false}
          draft={draft}
          provenance={provenance}
          availability={availability}
          isLoadingInputs={false}
          inputsError={null}
        />
      );

      expect(screen.getByRole("heading", { name: "Generate Value Case" })).toBeInTheDocument();
      expect(screen.getByText("CFO")).toBeInTheDocument();
      expect(screen.getByText("Evidence A")).toBeInTheDocument();
      expect(screen.getByDisplayValue("$2.0M")).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: /generate value case/i }));
      expect(onGenerate).toHaveBeenCalledWith(draft);
    });
  });
});
