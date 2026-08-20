import { describe, it, expect } from "vitest";
import {
  buildMetricCardViewModels,
  buildVersionSummaryViewModels,
  buildVersionDiffViewModel,
  buildResultViewModel,
} from "../presentation/valueCaseViewModels";
import type { ValueCaseArtifactVersion } from "../domain/valueCaseModels";

describe("valueCaseViewModels", () => {
  const sampleVersion1: ValueCaseArtifactVersion = {
    id: "ver-1",
    accountId: "acc-1",
    version: 1,
    createdAt: "2026-01-01T10:00:00.000Z",
    updatedAt: "2026-01-01T10:00:00.000Z",
    title: "Initial Case",
    status: "draft",
    narrative: {
      id: "nar-1",
      title: "Initial Case Narrative",
      sections: [
        {
          id: "sec-1",
          type: "executive_summary",
          title: "Executive Summary",
          content: "Initial business impact.",
          order: 0,
        },
      ],
      createdAt: "2026-01-01T10:00:00.000Z",
      updatedAt: "2026-01-01T10:00:00.000Z",
    },
    businessCase: {
      summary: "Summary for v1",
      metrics: {
        threeYearValue: "$1.0M",
        roi: "100%",
        payback: "12 months",
      },
      risks: ["Risk A", "Risk B"],
    },
    stakeholderFraming: [],
    inputs: {
      stakeholders: ["CFO"],
      acceptedEvidence: ["Evidence 1"],
      scenarioAssumptions: [],
      roiMetrics: {
        threeYearValue: "$1.0M",
        roi: "100%",
        payback: "12 months",
      },
      riskNotes: ["Risk A", "Risk B"],
    },
  };

  const sampleVersion2: ValueCaseArtifactVersion = {
    ...sampleVersion1,
    id: "ver-2",
    version: 2,
    createdAt: "2026-02-01T10:00:00.000Z",
    title: "Revised Case",
    status: "published",
    businessCase: {
      summary: "Summary for v2",
      metrics: {
        threeYearValue: "$2.5M",
        roi: "250%",
        payback: "6 months",
      },
      risks: ["Risk A"],
    },
  };

  describe("buildMetricCardViewModels", () => {
    it("builds cards with formatted values and accessibility descriptions", () => {
      const cards = buildMetricCardViewModels(sampleVersion1.businessCase.metrics);
      expect(cards).toHaveLength(3);

      const valueCard = cards.find(c => c.key === "three_year_value");
      expect(valueCard?.formattedValue).toBe("$1.0M");
      expect(valueCard?.isAvailable).toBe(true);
      expect(valueCard?.description).toContain("Net Present Value");

      const roiCard = cards.find(c => c.key === "roi");
      expect(roiCard?.formattedValue).toBe("100%");

      const paybackCard = cards.find(c => c.key === "payback");
      expect(paybackCard?.formattedValue).toBe("12 months");
    });

    it("handles missing metrics with fallback em-dash", () => {
      const cards = buildMetricCardViewModels(null);
      expect(cards.every(c => c.formattedValue === "—")).toBe(true);
      expect(cards.every(c => !c.isAvailable)).toBe(true);
    });
  });

  describe("buildVersionSummaryViewModels", () => {
    it("maps list of versions to summaries with status badges", () => {
      const summaries = buildVersionSummaryViewModels([sampleVersion1, sampleVersion2]);
      expect(summaries).toHaveLength(2);
      expect(summaries[0]?.label).toBe("v1");
      expect(summaries[0]?.isPublished).toBe(false);
      expect(summaries[1]?.label).toBe("v2");
      expect(summaries[1]?.isPublished).toBe(true);
    });
  });

  describe("buildVersionDiffViewModel", () => {
    it("returns null when current or prior version is missing", () => {
      expect(buildVersionDiffViewModel(sampleVersion1, null)).toBeNull();
      expect(buildVersionDiffViewModel(null, sampleVersion1)).toBeNull();
    });

    it("calculates diff between prior and current versions", () => {
      const diff = buildVersionDiffViewModel(sampleVersion2, sampleVersion1);
      expect(diff).not.toBeNull();
      expect(diff?.priorVersion).toBe(1);
      expect(diff?.currentVersion).toBe(2);
      expect(diff?.roiDiff).toBe("100% → 250%");
      expect(diff?.paybackDiff).toBe("12 months → 6 months");
      expect(diff?.valueDiff).toBe("$1.0M → $2.5M");
      expect(diff?.risksCountDiff).toBe("2 risks → 1 risks");
      expect(diff?.hasChanges).toBe(true);
    });
  });

  describe("buildResultViewModel", () => {
    it("returns null when active version is null", () => {
      expect(buildResultViewModel(null)).toBeNull();
    });

    it("builds result view model with narrative and metrics", () => {
      const result = buildResultViewModel(sampleVersion2);
      expect(result).not.toBeNull();
      expect(result?.version).toBe(2);
      expect(result?.isPublished).toBe(true);
      expect(result?.statusBadgeLabel).toBe("Published");
      expect(result?.businessCaseSummary).toBe("Summary for v2");
      expect(result?.narrativeSections).toHaveLength(1);
      expect(result?.risks).toEqual(["Risk A"]);
    });
  });
});
