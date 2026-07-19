import { describe, expect, it } from "vitest";
import { calculateValueOracle, normalizeRate, type ValueCalculationInput } from "./valueCalculationOracle";

const canonicalCase: ValueCalculationInput = {
  revenueBase: 10_000_000,
  improvementRate: 0.04,
  realizationRate: 0.75,
  implementationCost: 120_000,
  recurringCost: 30_000,
  periodYears: 1,
};

describe("P0 calculation oracle", () => {
  it("matches the independently reviewed canonical one-year ROI case", () => {
    expect(calculateValueOracle(canonicalCase)).toEqual({
      grossValue: 400_000,
      realizedValue: 300_000,
      totalCost: 150_000,
      netValue: 150_000,
      roiPercent: 100,
    });
  });

  it("normalizes percentage and decimal rates to the same output", () => {
    const decimal = calculateValueOracle(canonicalCase);
    const percentage = calculateValueOracle({
      ...canonicalCase,
      improvementRate: 4,
      realizationRate: 75,
    });

    expect(percentage).toEqual(decimal);
    expect(normalizeRate(4)).toBe(0.04);
    expect(normalizeRate(0.04)).toBe(0.04);
  });

  it("treats an input of exactly 1 as a decimal (100%)", () => {
    expect(normalizeRate(1)).toBe(1);
  });

  it("returns an explicit null ROI for zero total cost instead of dividing by zero", () => {
    expect(
      calculateValueOracle({
        ...canonicalCase,
        implementationCost: 0,
        recurringCost: 0,
      })
    ).toEqual({
      grossValue: 400_000,
      realizedValue: 300_000,
      totalCost: 0,
      netValue: 300_000,
      roiPercent: null,
    });
  });

  it("rejects negative values and missing units represented by invalid horizons", () => {
    expect(() => calculateValueOracle({ ...canonicalCase, revenueBase: -1 })).toThrow("revenueBase must be >= 0");
    expect(() => calculateValueOracle({ ...canonicalCase, implementationCost: -1 })).toThrow("costs must be >= 0");
    expect(() => calculateValueOracle({ ...canonicalCase, recurringCost: -1 })).toThrow("costs must be >= 0");
    expect(() => calculateValueOracle({ ...canonicalCase, periodYears: 0 })).toThrow("periodYears must be > 0");
  });

  it("rounds currency and ROI at two decimals on boundary inputs", () => {
    expect(
      calculateValueOracle({
        revenueBase: 333_333.33,
        improvementRate: 0.033333,
        realizationRate: 0.666667,
        implementationCost: 7_777.77,
        recurringCost: 111.11,
        periodYears: 1,
      })
    ).toEqual({
      grossValue: 11_111,
      realizedValue: 7_407.34,
      totalCost: 7_888.88,
      netValue: -481.54,
      roiPercent: -6.1,
    });
  });

  it("handles very large values without losing the canonical cost invariant", () => {
    const result = calculateValueOracle({
      revenueBase: 9_000_000_000_000,
      improvementRate: 0.015,
      realizationRate: 0.8,
      implementationCost: 12_000_000,
      recurringCost: 4_000_000,
      periodYears: 3,
    });

    expect(result.grossValue).toBe(405_000_000_000);
    expect(result.realizedValue).toBe(324_000_000_000);
    expect(result.totalCost).toBe(24_000_000);
    expect(result.netValue).toBe(323_976_000_000);
    expect(result.roiPercent).toBe(1_349_900);
  });

  it("preserves the invariant that higher implementation cost cannot increase ROI", () => {
    const lowCost = calculateValueOracle(canonicalCase);
    const highCost = calculateValueOracle({
      ...canonicalCase,
      implementationCost: canonicalCase.implementationCost + 50_000,
    });

    expect(highCost.roiPercent).not.toBeNull();
    expect(lowCost.roiPercent).not.toBeNull();
    expect(highCost.roiPercent as number).toBeLessThan(lowCost.roiPercent as number);
    expect(highCost.netValue).toBeLessThan(lowCost.netValue);
  });
});
