/**
 * WfPrimitives — approved legacy compatibility surface for workflow pages.
 *
 * Re-exports the canonical fabric UI primitives under stable names so that
 * workflow pages can import from a single location without coupling to the
 * internal fabric directory structure.
 *
 * Do NOT add new exports here without updating the surface test in
 * WfPrimitives.test.tsx.
 */

export { Btn } from "@/components/ui/fabric";
export type { BtnProps } from "@/components/ui/fabric";

export { DataTable } from "@/components/ui/fabric";
export { EntityBadge } from "@/components/ui/fabric";
export type { EntityType } from "@/lib/entity-colors";

export { FilterBar } from "@/components/ui/fabric";
export { FabricDialog as Dialog } from "@/components/ui/fabric";
export { GraphLegend } from "@/components/ui/fabric";
export { MetricCard } from "@/components/ui/fabric";
export { PageHeader } from "@/components/ui/fabric";
export { SearchInput } from "@/components/ui/fabric";
export { SectionCard } from "@/components/blocks";
export type { SectionCardProps } from "@/components/blocks";
export { SidePanel } from "@/components/ui/fabric";
export { StatusBadge } from "@/components/ui/fabric";
// StatusType is the public alias for LegacyStatusType
export type { LegacyStatusType as StatusType } from "@/components/ui/fabric/StatusBadge";
export { Tabs } from "@/components/ui/fabric";
export { Toolbar } from "@/components/ui/fabric";

// Callout — lightweight inline notice component.
import React from "react";
import { cn } from "@/lib/utils";

interface CalloutProps {
  variant?: "info" | "warning" | "error" | "success";
  className?: string;
  children: React.ReactNode;
}

export function Callout({ variant = "info", className, children }: CalloutProps) {
  const variantClass = {
    info: "bg-primary/10 border-primary/20 text-primary",
    warning: "bg-warning/10 border-warning/20 text-warning",
    error: "bg-destructive/10 border-destructive/20 text-destructive",
    success: "bg-success/10 border-success/20 text-success",
  }[variant];

  return (
    <div
      role="note"
      className={cn(
        "rounded-md border px-4 py-3 text-sm",
        variantClass,
        className,
      )}
    >
      {children}
    </div>
  );
}

// StatusBadgeLegacy — alias kept for backward compatibility with older pages.
export { StatusBadge as StatusBadgeLegacy } from "@/components/ui/fabric";
