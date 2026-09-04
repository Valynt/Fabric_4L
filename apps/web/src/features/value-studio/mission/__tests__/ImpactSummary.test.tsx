/**
 * Component tests for the impact summary (§9.6, FE-IMP-*). Economics render
 * exactly as projected: null program cost → "Pending", null ROI → "Not yet
 * calculable", never zero; no browser recalculation.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { makeCaseProjection } from "../fixtures";
import { ImpactSummary } from "../components/ImpactSummary";

const economics = makeCaseProjection().economics;

describe("ImpactSummary", () => {
  it("renders the value impact region with the projected annual benefit", () => {
    render(<ImpactSummary economics={economics} />);
    expect(screen.getByRole("region", { name: "Value impact summary" })).toBeInTheDocument();
    expect(screen.getByText("720,000 USD/year")).toBeInTheDocument();
  });

  it("shows the backend governance label next to the benefit (FE-HDR-003)", () => {
    render(<ImpactSummary economics={economics} />);
    expect(screen.getByText("Provisional")).toBeInTheDocument();
  });

  it("renders null program cost as Pending, never zero (FE-IMP-002)", () => {
    render(<ImpactSummary economics={economics} />);
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });

  it("renders null ROI as Not yet calculable, never zero (FE-IMP-003)", () => {
    render(<ImpactSummary economics={economics} />);
    expect(screen.getByText("Not yet calculable")).toBeInTheDocument();
  });

  it("renders the server-provided formula display and id verbatim", () => {
    render(<ImpactSummary economics={economics} />);
    expect(
      screen.getByText("(400 − 340) × 12,000 USD = 720,000 USD/year"),
    ).toBeInTheDocument();
    expect(screen.getByText("Formula formula_downtime_benefit_v3")).toBeInTheDocument();
  });

  it("formats present cost and ROI values when the server provides them", () => {
    render(
      <ImpactSummary
        economics={{
          ...economics,
          programCost: { amount: 96_000, currency: "USD", governanceLabel: "VALIDATED" },
          roi: { ratio: 7.5, governanceLabel: "VALIDATED" },
        }}
      />,
    );
    expect(screen.getByText("96,000 USD/year")).toBeInTheDocument();
    expect(screen.getByText("7.50×")).toBeInTheDocument();
  });
});
