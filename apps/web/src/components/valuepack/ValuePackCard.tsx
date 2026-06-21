/**
 * ValuePack Card Component
 * 
 * Displays a compact summary of a ValuePack for browsing and selection.
 * Part of the ValuePack Framework v1.0 UI components.
 */
import { Building2, TrendingUp, Users, Clock, Database, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { ValuePackFrameworkData } from "@/api/valuePackFramework";

interface ValuePackCardProps {
  valuepack: ValuePackFrameworkData;
  onClick?: () => void;
  isSelected?: boolean;
  className?: string;
  showMatchScore?: number;
}

const tierConfig = {
  1: { label: "Tier 1", color: "bg-success/10 text-success", description: "Immediate Traction" },
  2: { label: "Tier 2", color: "bg-primary/10 text-primary", description: "High ROI, Underserved" },
  3: { label: "Tier 3", color: "bg-primary/10 text-primary", description: "Complex but Powerful" },
};

const switchingCostIcon = {
  low: <Zap className="w-3 h-3" />,
  medium: <Clock className="w-3 h-3" />,
  high: <Building2 className="w-3 h-3" />,
};

const dataRichnessIcon = {
  low: <Database className="w-3 h-3 opacity-50" />,
  medium: <Database className="w-3 h-3 opacity-75" />,
  high: <Database className="w-3 h-3" />,
};

export function ValuePackCard({
  valuepack,
  onClick,
  isSelected,
  className,
  showMatchScore,
}: ValuePackCardProps) {
  const tier = tierConfig[valuepack.tier];
  const driverCount = valuepack.primary_value_drivers.length;
  const useCaseCount = valuepack.core_use_cases.length;

  return (
    <div
      onClick={onClick}
      className={cn(
        "group cursor-pointer rounded-lg border p-4 transition-all hover:shadow-md",
        isSelected
          ? "border-primary bg-primary/5 shadow-sm"
          : "border-border bg-card hover:border-primary/50",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-foreground truncate">
            {valuepack.display_name}
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
            {valuepack.description}
          </p>
        </div>
        <Badge variant="secondary" className={cn("shrink-0 text-xs", tier.color)}>
          {tier.label}
        </Badge>
      </div>

      {/* Stats Row */}
      <div className="flex items-center gap-3 text-xs text-muted-foreground mb-3">
        <span className="flex items-center gap-1">
          <TrendingUp className="w-3 h-3" />
          {driverCount} drivers
        </span>
        <span className="flex items-center gap-1">
          <Users className="w-3 h-3" />
          {useCaseCount} use cases
        </span>
        {showMatchScore !== undefined && (
          <span className={cn(
            "flex items-center gap-1 font-medium",
            showMatchScore >= 0.8 ? "text-success" :
            showMatchScore >= 0.6 ? "text-warning" :
            "text-muted-foreground"
          )}>
            <Zap className="w-3 h-3" />
            {Math.round(showMatchScore * 100)}% match
          </span>
        )}
      </div>

      {/* Value Drivers Preview */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {valuepack.primary_value_drivers.slice(0, 3).map((driver) => (
          <span
            key={driver.id}
            className="inline-flex items-center px-2 py-0.5 rounded vf-text-micro bg-muted text-muted-foreground"
          >
            {driver.name}
          </span>
        ))}
        {driverCount > 3 && (
          <span className="inline-flex items-center px-2 py-0.5 rounded vf-text-micro text-muted-foreground">
            +{driverCount - 3} more
          </span>
        )}
      </div>

      {/* Metadata Indicators */}
      <div className="flex items-center justify-between pt-3 border-t border-border">
        <div className="flex items-center gap-3 vf-text-micro text-muted-foreground">
          <span className="flex items-center gap-1" title="Switching Cost">
            {switchingCostIcon[valuepack.metadata.switching_cost]}
            <span className="capitalize">{valuepack.metadata.switching_cost}</span>
          </span>
          <span className="flex items-center gap-1" title="Data Richness">
            {dataRichnessIcon[valuepack.metadata.data_richness]}
            <span className="capitalize">{valuepack.metadata.data_richness}</span>
          </span>
        </div>
        <span className="vf-text-micro text-muted-foreground">
          {valuepack.metadata.deal_size_range}
        </span>
      </div>

      {/* Match Score Progress Bar */}
      {showMatchScore !== undefined && (
        <div className="mt-3">
          <div className="h-1 bg-muted rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                showMatchScore >= 0.8 ? "bg-success/100" :
                showMatchScore >= 0.6 ? "bg-warning/100" :
                "bg-muted-foreground"
              )}
              style={{ width: `${showMatchScore * 100}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export function ValuePackCardSkeleton() {
  return (
    <div className="rounded-lg border border-border bg-card p-4 animate-pulse">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex-1">
          <div className="h-5 bg-muted rounded w-3/4 mb-2" />
          <div className="h-3 bg-muted rounded w-full" />
        </div>
        <div className="h-5 bg-muted rounded w-12" />
      </div>
      <div className="flex gap-2 mb-3">
        <div className="h-4 bg-muted rounded w-16" />
        <div className="h-4 bg-muted rounded w-16" />
      </div>
      <div className="flex flex-wrap gap-1.5 mb-3">
        <div className="h-5 bg-muted rounded w-20" />
        <div className="h-5 bg-muted rounded w-24" />
        <div className="h-5 bg-muted rounded w-16" />
      </div>
      <div className="h-6 bg-muted rounded w-full" />
    </div>
  );
}
