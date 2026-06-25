import type { C1Component, WhatIfResult } from "@/api/thesysClient";

/**
 * Apply a what-if formula result to the matching MetricCard components.
 *
 * Matching rules (label-based, case-insensitive):
 * - "roi" or "return"      → value = result.new_roi
 * - "payback" or "timeline" → value = result.new_payback_months
 * - "value" (but not "original") → value = result.adjusted_value
 */
export function applyWhatIfResult(
  components: C1Component[],
  result: WhatIfResult
): C1Component[] {
  return components.map((comp) => {
    if (comp.type !== "MetricCard") return comp;

    const label = ((comp.props.label as string) ?? "").toLowerCase();

    if (label.includes("roi") || label.includes("return")) {
      return { ...comp, props: { ...comp.props, value: result.new_roi } };
    }

    if (label.includes("payback") || label.includes("timeline")) {
      return {
        ...comp,
        props: { ...comp.props, value: result.new_payback_months },
      };
    }

    if (label.includes("value") && !label.includes("original")) {
      return { ...comp, props: { ...comp.props, value: result.adjusted_value } };
    }

    return comp;
  });
}
