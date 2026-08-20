import { describe, it, expect } from "vitest";
import {
  aggregateGenerationInputs,
  createGenerationSubmissionSnapshot,
} from "../domain/generationInputs";
import type { ValueCaseScope } from "../domain/valueCaseModels";

describe("generationInputs", () => {
  const scope: ValueCaseScope = {
    fabricTenantId: "tenant-123",
    tenantSlug: "test-tenant",
    accountId: "acc-999",
  };

  it("stably sorts and truncates items to top 5", () => {
    const rawStakeholders = [
      { id: "s-5", name: "Zeta Officer" },
      { id: "s-1", name: "Alpha Leader" },
      { id: "s-3", name: "Beta Director" },
      { id: "s-2", name: "Gamma VP" },
      { id: "s-4", name: "Delta Head" },
      { id: "s-6", name: "Epsilon Manager" },
    ];

    const result = aggregateGenerationInputs({
      scope,
      accountName: "Acme",
      stakeholders: rawStakeholders,
      validatedTruths: [],
      disputedTruths: [],
      roiCalculations: [],
    });

    // Should be sorted alphabetically and capped at 5 items
    expect(result.draft.stakeholders).toEqual([
      "Alpha Leader",
      "Beta Director",
      "Delta Head",
      "Epsilon Manager",
      "Gamma VP",
    ]);
    expect(result.draft.stakeholders.length).toBe(5);
  });

  it("deduplicates identical names and trims whitespace", () => {
    const rawStakeholders = [
      { id: "s-1", name: "CFO " },
      { id: "s-2", name: "cfo" },
      { id: "s-3", name: "CTO" },
    ];

    const result = aggregateGenerationInputs({
      scope,
      accountName: "Acme",
      stakeholders: rawStakeholders,
      validatedTruths: [],
      disputedTruths: [],
      roiCalculations: [],
    });

    expect(result.draft.stakeholders).toEqual(["CFO", "CTO"]);
  });

  it("formats ROI metrics from latest calculation", () => {
    const roiCalculations = [
      {
        id: "roi-1",
        npv: 2500000,
        total_roi_pct: 250.4,
        payback_months: 6.2,
      },
    ];

    const result = aggregateGenerationInputs({
      scope,
      accountName: "Acme",
      stakeholders: [],
      validatedTruths: [],
      disputedTruths: [],
      roiCalculations,
    });

    expect(result.draft.roiMetrics.threeYearValue).toBe("$2.5M");
    expect(result.draft.roiMetrics.roi).toBe("250%");
    expect(result.draft.roiMetrics.payback).toBe("6.2 months");
    expect(result.provenance.roiMetrics[0]?.source).toBe("roi_calculation");
  });

  it("reports partial availability when some queries fail", () => {
    const result = aggregateGenerationInputs({
      scope,
      accountName: "Acme",
      stakeholders: [],
      validatedTruths: [],
      disputedTruths: [],
      roiCalculations: [],
      isStakeholdersError: true,
      isRoiError: false,
    });

    expect(result.availability.hasPartialFailures).toBe(true);
    expect(result.availability.failedSources).toContain("stakeholders");
    expect(result.availability.statusMessage).toContain("stakeholders");
  });

  it("creates immutable submission snapshot matching scope", () => {
    const aggregate = aggregateGenerationInputs({
      scope,
      accountName: "Acme",
      stakeholders: [{ id: "s-1", name: "CEO" }],
      validatedTruths: [],
      disputedTruths: [],
      roiCalculations: [],
    });

    const snapshot = createGenerationSubmissionSnapshot(aggregate.draft, scope, "Acme");

    expect(snapshot.submissionScope.fabricTenantId).toBe("tenant-123");
    expect(snapshot.submissionScope.accountId).toBe("acc-999");
    expect(snapshot.accountName).toBe("Acme");
    expect(snapshot.draft.stakeholders).toEqual(["CEO"]);
  });
});
