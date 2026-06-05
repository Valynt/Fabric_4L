/**
 * GraphLegend — Color legend for knowledge graph entity types.
 * Migrated from WfPrimitives shim.
 */
import { cn } from "@/lib/utils";

const LEGEND_ITEMS = [
  { color: "bg-violet-400", label: "Capability" },
  { color: "bg-cyan-400", label: "Use Case" },
  { color: "bg-amber-400", label: "Persona" },
  { color: "bg-emerald-400", label: "Value Driver" },
] as const;

export function GraphLegend() {
  return (
    <div className="flex gap-4 flex-wrap">
      {LEGEND_ITEMS.map(({ color, label }) => (
        <div key={label} className="flex items-center gap-1.5 vf-text-caption text-muted-foreground">
          <div className={cn("w-2.5 h-2.5 rounded-full", color)} />
          {label}
        </div>
      ))}
    </div>
  );
}
