import { describe, expect, it } from "vitest";
import { parsePromptText } from "./promptParser";

describe("parsePromptText", () => {
  it("parses an empty prompt into an empty draft", () => {
    const result = parsePromptText("");
    expect(result.draft.companyName).toBe("");
    expect(result.draft.businessPain).toEqual([]);
    expect(result.draft.stakeholders.economicBuyer).toBe("");
    expect(result.visibleSections.company).toBe(false);
  });

  it("extracts company fields from key-value lines", () => {
    const result = parsePromptText(`
Company: Acme Corp
Website: acme.example.com
Industry: Manufacturing
`);
    expect(result.draft.companyName).toBe("Acme Corp");
    expect(result.draft.companyDomain).toBe("acme.example.com");
    expect(result.draft.industry).toBe("Manufacturing");
    expect(result.visibleSections.company).toBe(true);
  });

  it("extracts buying context fields", () => {
    const result = parsePromptText(`
Buying Context: Looking to expand analytics
Why This Account Now: Budget cycle
Known Initiative: Cloud migration
`);
    expect(result.draft.buyingContext).toBe("Looking to expand analytics");
    expect(result.draft.whyNow).toBe("Budget cycle");
    expect(result.draft.knownInitiative).toBe("Cloud migration");
    expect(result.visibleSections.buyingContext).toBe(true);
  });

  it("extracts stakeholders from bullet list", () => {
    const result = parsePromptText(`
Stakeholders:
- Economic Buyer: Alice
- Champion: Bob
- Evaluator: Carol
- Compliance: Dave
`);
    expect(result.draft.stakeholders.economicBuyer).toBe("Alice");
    expect(result.draft.stakeholders.champion).toBe("Bob");
    expect(result.draft.stakeholders.evaluator).toBe("Carol");
    expect(result.draft.stakeholders.compliance).toBe("Dave");
    expect(result.visibleSections.stakeholders).toBe(true);
  });

  it("extracts business pain bullets", () => {
    const result = parsePromptText(`
Business Pains:
- Data silos
- Slow reporting
- Manual reconciliations
`);
    expect(result.draft.businessPain).toEqual([
      "Data silos",
      "Slow reporting",
      "Manual reconciliations",
    ]);
    expect(result.visibleSections.businessPain).toBe(true);
  });

  it("extracts current friction and desired outcomes", () => {
    const result = parsePromptText(`
Current Friction:
- Legacy tools

Desired Outcomes:
- Faster close
- Real-time dashboards
`);
    expect(result.draft.currentFriction).toEqual(["Legacy tools"]);
    expect(result.draft.desiredOutcomes).toEqual([
      "Faster close",
      "Real-time dashboards",
    ]);
    expect(result.visibleSections.businessPain).toBe(true);
  });

  it("maps deliverable labels to typed values", () => {
    const result = parsePromptText(`
Deliverables:
- Account Brief
- Value Hypotheses
- Executive Summary
`);
    expect(result.draft.desiredOutputs).toEqual([
      "account_brief",
      "value_hypotheses",
      "executive_summary",
    ]);
    expect(result.visibleSections.deliverable).toBe(true);
  });

  it("extracts compliance details", () => {
    const result = parsePromptText(`
Compliance:
- Regulated Industry: Healthcare
- Known Requirements: HIPAA, SOC 2
- Security Review Expected: Yes
`);
    expect(result.draft.compliance.regulatedIndustry).toBe("Healthcare");
    expect(result.draft.compliance.knownRequirements).toEqual(["HIPAA", "SOC 2"]);
    expect(result.draft.compliance.securityReviewExpected).toBe("Yes");
    expect(result.visibleSections.compliance).toBe(true);
  });

  it("extracts research focus bullets", () => {
    const result = parsePromptText(`
Research Focus:
- Competitive landscape
- Pricing strategy
`);
    expect(result.draft.researchFocus).toEqual([
      "Competitive landscape",
      "Pricing strategy",
    ]);
    expect(result.visibleSections.researchFocus).toBe(true);
  });

  it("collects leftover text as notes", () => {
    const result = parsePromptText(`
Some additional context that does not match any section.
Another free-form note.
`);
    expect(result.draft.notes).toContain("Some additional context");
    expect(result.visibleSections.notes).toBe(true);
  });

  it("extracts explicit notes section", () => {
    const result = parsePromptText(`
Notes:
Remember to verify the renewal date.
`);
    expect(result.draft.notes).toContain("Remember to verify the renewal date");
    expect(result.visibleSections.notes).toBe(true);
  });
});
