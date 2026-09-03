/**
 * Chart Primitive Tests
 *
 * Behavior tests for the shadcn/ui chart primitive:
 * - ChartContainer injects theme CSS variables from the chart config.
 * - ChartTooltipContent renders label, name, and value when active.
 * - ChartTooltipContent renders nothing when the tooltip is inactive,
 *   even when a (stale) payload is present.
 */
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import type * as React from "react";
import { readFileSync } from "node:fs";

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  Tooltip: () => null,
  Legend: () => null,
}));

import { ChartContainer, ChartTooltipContent } from "./chart";

const config = {
  revenue: { label: "Revenue", color: "#123456" },
};

const payload = [
  {
    name: "revenue",
    dataKey: "revenue",
    value: 1000,
    payload: { fill: "#123456" },
  },
];

describe("ChartContainer", () => {
  it("injects theme CSS variables derived from the chart config", () => {
    const { container } = render(
      <ChartContainer config={config}>
        <div />
      </ChartContainer>
    );

    const style = container.querySelector("style");
    expect(style?.innerHTML).toContain("--color-revenue: #123456;");
  });

  it("renders generated chart CSS without an HTML injection sink", () => {
    const chartSource = readFileSync("src/components/ui/chart.tsx", "utf8");

    expect(chartSource).not.toContain("dangerouslySetInnerHTML");
  });
});

describe("ChartTooltipContent", () => {
  it("renders the label, item name, and formatted value when active", () => {
    const { getByText } = render(
      <ChartContainer config={config}>
        <ChartTooltipContent active label="Q1 Revenue" payload={payload} />
      </ChartContainer>
    );

    expect(getByText("Q1 Revenue")).toBeTruthy();
    expect(getByText("Revenue")).toBeTruthy();
    expect(getByText("1,000")).toBeTruthy();
  });

  it("renders nothing when inactive even if a payload is present", () => {
    const { queryByText } = render(
      <ChartContainer config={config}>
        <ChartTooltipContent
          active={false}
          label="Q1 Revenue"
          payload={payload}
        />
      </ChartContainer>
    );

    expect(queryByText("Q1 Revenue")).toBeNull();
    expect(queryByText("Revenue")).toBeNull();
  });
});
