export type ValueCalculationInput = {
  revenueBase: number;
  improvementRate: number;
  realizationRate: number;
  implementationCost: number;
  recurringCost: number;
  periodYears: number;
};

export type ValueCalculationResult = {
  grossValue: number;
  realizedValue: number;
  totalCost: number;
  netValue: number;
  roiPercent: number | null;
};

export function normalizeRate(value: number): number {
  if (!Number.isFinite(value)) {
    throw new Error("rate must be finite");
  }
  return Math.abs(value) > 1 ? value / 100 : value;
}

export function calculateValueOracle(input: ValueCalculationInput): ValueCalculationResult {
  const values = Object.entries(input);
  for (const [name, value] of values) {
    if (!Number.isFinite(value)) {
      throw new Error(`${name} must be finite`);
    }
  }

  if (input.revenueBase < 0) {
    throw new Error("revenueBase must be >= 0");
  }
  if (input.implementationCost < 0 || input.recurringCost < 0) {
    throw new Error("costs must be >= 0");
  }
  if (input.periodYears <= 0) {
    throw new Error("periodYears must be > 0");
  }

  const improvementRate = normalizeRate(input.improvementRate);
  const realizationRate = normalizeRate(input.realizationRate);
  if (improvementRate < 0 || realizationRate < 0) {
    throw new Error("rates must be >= 0");
  }

  const grossValue = input.revenueBase * improvementRate * input.periodYears;
  const realizedValue = grossValue * realizationRate;
  const totalCost = input.implementationCost + input.recurringCost * input.periodYears;
  const netValue = realizedValue - totalCost;
  const roiPercent = totalCost === 0 ? null : (netValue / totalCost) * 100;

  return {
    grossValue: roundCurrency(grossValue),
    realizedValue: roundCurrency(realizedValue),
    totalCost: roundCurrency(totalCost),
    netValue: roundCurrency(netValue),
    roiPercent: roiPercent === null ? null : roundPercent(roiPercent),
  };
}

function roundCurrency(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function roundPercent(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}
