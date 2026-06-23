import { describe, it, expect, vi } from "vitest";
import {
  isC1Enabled,
  saveScenario,
  getScenarios,
  compareScenarios,
  type SavedScenario,
} from "./thesysClient";

describe("thesysClient", () => {
  describe("isC1Enabled", () => {
    it("returns false by default", () => {
      expect(isC1Enabled()).toBe(false);
    });
  });

  describe("saveScenario / getScenarios", () => {
    beforeEach(() => {
      localStorage.clear();
    });

    it("saves and retrieves scenarios", () => {
      const id = saveScenario("case-1", "Scenario A", [{ name: "x", value: 10 }]);
      expect(id).toMatch(/^scenario_\d+_[a-z0-9]+$/);

      const scenarios = getScenarios("case-1");
      expect(scenarios).toHaveLength(1);
      expect(scenarios[0].name).toBe("Scenario A");
    });

    it("returns empty array when no scenarios exist", () => {
      expect(getScenarios("nonexistent")).toEqual([]);
    });

    it("handles corrupt localStorage gracefully", () => {
      localStorage.setItem("vf_scenarios_case-1", "not-json");
      expect(getScenarios("case-1")).toEqual([]);
      expect(localStorage.getItem("vf_scenarios_case-1")).toBeNull();
    });

    it("handles non-array parsed data", () => {
      localStorage.setItem("vf_scenarios_case-1", JSON.stringify({ foo: 1 }));
      expect(getScenarios("case-1")).toEqual([]);
    });
  });

  describe("compareScenarios", () => {
    beforeEach(() => {
      localStorage.clear();
    });

    it("filters scenarios by id list", () => {
      const id1 = saveScenario("case-1", "S1", []);
      const id2 = saveScenario("case-1", "S2", []);
      saveScenario("case-1", "S3", []);

      const result = compareScenarios("case-1", [id1, id2]);
      expect(result).toHaveLength(2);
      expect(result.map((s) => s.name)).toContain("S1");
      expect(result.map((s) => s.name)).toContain("S2");
    });

    it("returns empty array for unknown ids", () => {
      expect(compareScenarios("case-1", ["unknown"])).toEqual([]);
    });
  });
});
