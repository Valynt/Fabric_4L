import { memo } from "react";
import { MetricCard } from "@/components/ui/fabric";
import type { ValueCaseMetricCardViewModel } from "../presentation/valueCaseViewModels";

export interface ValueCaseMetricsProps {
  metrics: ValueCaseMetricCardViewModel[];
  className?: string;
}

export const ValueCaseMetrics = memo(function ValueCaseMetrics({
  metrics,
  className = "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4",
}: ValueCaseMetricsProps) {
  return (
    <div
      className={className}
      role="region"
      aria-label="Value Case Financial Metrics"
    >
      {metrics.map(metric => (
        <div key={metric.key} title={metric.description}>
          <MetricCard
            label={metric.label}
            value={metric.formattedValue}
          />
        </div>
      ))}
    </div>
  );
});
