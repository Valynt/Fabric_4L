import { describe, expect, it } from "vitest";
import { NAV_SPINE } from "./TieredNav";

describe("TieredNav navigation spine", () => {
  it("uses the progressive-synthesis top-level domains", () => {
    expect(NAV_SPINE.map((item) => item.id)).toEqual([
      "accounts",
      "intelligence",
      "value-studio",
      "context-engine",
      "deliverables",
      "governance",
      "settings",
    ]);
  });

  it("keeps intelligence and value studio child tabs", () => {
    const intelligence = NAV_SPINE.find((item) => item.id === "intelligence");
    const valueStudio = NAV_SPINE.find((item) => item.id === "value-studio");

    expect(intelligence?.children?.map((child) => child.label)).toEqual([
      "Signals",
      "Drivers",
      "Evidence",
      "Stakeholders",
    ]);
    expect(valueStudio?.children?.map((child) => child.label)).toEqual([
      "Action Plan",
      "Value Model",
      "Narrative",
    ]);
  });
});
