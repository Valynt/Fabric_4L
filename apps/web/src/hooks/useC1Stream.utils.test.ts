import { describe, it, expect } from "vitest";
import { applyWhatIfResult } from "./useC1Stream.utils";
import type { C1Component, WhatIfResult } from "@/api/thesysClient";

function metricCard(label: string, value: number): C1Component {
  return { type: "MetricCard", props: { label, value } };
}

const baseResult: WhatIfResult = {
  original_value: 100,
  adjusted_value: 150,
  delta_percentage: 50,
  new_roi: 25,
  new_payback_months: 18,
  formula_used: "test",
};

describe("applyWhatIfResult", () => {
  it("updates ROI metric cards", () => {
    const next = applyWhatIfResult(
      [metricCard("Projected ROI", 10)],
      baseResult
    );
    expect(next[0].props.value).toBe(baseResult.new_roi);
  });

  it("updates return metric cards", () => {
    const next = applyWhatIfResult(
      [metricCard("Annual Return", 5)],
      baseResult
    );
    expect(next[0].props.value).toBe(baseResult.new_roi);
  });

  it("updates payback metric cards", () => {
    const next = applyWhatIfResult(
      [metricCard("Payback Timeline", 24)],
      baseResult
    );
    expect(next[0].props.value).toBe(baseResult.new_payback_months);
  });

  it("updates value metric cards", () => {
    const next = applyWhatIfResult(
      [metricCard("Net Value", 100)],
      baseResult
    );
    expect(next[0].props.value).toBe(baseResult.adjusted_value);
  });

  it("does not update original value cards", () => {
    const next = applyWhatIfResult(
      [metricCard("Original Value", 100)],
      baseResult
    );
    expect(next[0].props.value).toBe(100);
  });

  it("leaves non-MetricCard components unchanged", () => {
    const slider: C1Component = {
      type: "Slider",
      props: { name: "cost", value: 10 },
    };
    const next = applyWhatIfResult([slider], baseResult);
    expect(next[0].props.value).toBe(10);
  });

  it("preserves other props on updated cards", () => {
    const next = applyWhatIfResult(
      [metricCard("Projected ROI", 10)],
      baseResult
    );
    expect(next[0].props.label).toBe("Projected ROI");
    expect(next[0].type).toBe("MetricCard");
  });
});
