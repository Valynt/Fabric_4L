import { describe, expect, it } from "vitest";
import { studioTabs, getActiveStudioTabDefs, DEFAULT_STUDIO_TAB } from "./studioTabRegistry";

describe("studioTabRegistry", () => {
  it("contains the default tab", () => {
    const ids = getActiveStudioTabDefs().map((t) => t.id);
    expect(ids).toContain(DEFAULT_STUDIO_TAB);
  });

  it("every active tab has a component", () => {
    for (const tab of getActiveStudioTabDefs()) {
      expect(tab.component, `tab ${tab.id} should have a component`).toBeTruthy();
    }
  });

  it("no active tab id looks like an intelligence route", () => {
    for (const tab of getActiveStudioTabDefs()) {
      expect(tab.id).not.toMatch(/^intelligence-/);
    }
  });

  it("defines all expected core Studio tabs", () => {
    const ids = getActiveStudioTabDefs().map((t) => t.id);
    expect(ids).toEqual(
      expect.arrayContaining([
        "action-plan",
        "value-model",
        "driver-tree",
        "calculator",
        "narrative",
        "value-case",
        "value-realization",
      ])
    );
  });
});
