import React from "react";

/**
 * Entity Type Color System
 * Formalizes domain-specific colors for knowledge graph entity types.
 * These are SEMANTIC colors — they carry meaning and must NOT be replaced
 * with neutral Fabric tokens.
 */

/** Legacy entity type union used by graph/browser components. */
export type EntityType = "capability" | "usecase" | "persona" | "valuedriver";

export interface EntityColorScheme {
  bg: string;        // Background class (e.g., bg-violet-100)
  text: string;      // Text class (e.g., text-violet-800)
  border: string;    // Border class (e.g., border-violet-200)
  dot: string;       // Dot/indicator class
  fill: string;      // SVG fill color
  stroke: string;    // SVG stroke color
}

export const entityColors: Record<string, EntityColorScheme> = {
  capability: {
    bg: "bg-violet-100 dark:bg-violet-900/30",
    text: "text-violet-800 dark:text-violet-300",
    border: "border-violet-200 dark:border-violet-800",
    dot: "bg-violet-500",
    fill: "#ede9fe",
    stroke: "#c4b5fd",
  },
  usecase: {
    bg: "bg-cyan-100 dark:bg-cyan-900/30",
    text: "text-cyan-800 dark:text-cyan-300",
    border: "border-cyan-200 dark:border-cyan-800",
    dot: "bg-cyan-500",
    fill: "#cffafe",
    stroke: "#67e8f9",
  },
  persona: {
    bg: "bg-amber-100 dark:bg-amber-900/30",
    text: "text-amber-800 dark:text-amber-300",
    border: "border-amber-200 dark:border-amber-800",
    dot: "bg-amber-500",
    fill: "#fef3c7",
    stroke: "#fcd34d",
  },
  valuedriver: {
    bg: "bg-emerald-100 dark:bg-emerald-900/30",
    text: "text-emerald-800 dark:text-emerald-300",
    border: "border-emerald-200 dark:border-emerald-800",
    dot: "bg-emerald-500",
    fill: "#d1fae5",
    stroke: "#6ee7b7",
  },
  pack: {
    bg: "bg-blue-100 dark:bg-blue-900/30",
    text: "text-blue-800 dark:text-blue-300",
    border: "border-blue-200 dark:border-blue-800",
    dot: "bg-blue-500",
    fill: "#dbeafe",
    stroke: "#93c5fd",
  },
  account: {
    bg: "bg-slate-100 dark:bg-slate-800",
    text: "text-slate-800 dark:text-slate-300",
    border: "border-slate-200 dark:border-slate-700",
    dot: "bg-slate-500",
    fill: "#f1f5f9",
    stroke: "#94a3b8",
  },
  formula: {
    bg: "bg-indigo-100 dark:bg-indigo-900/30",
    text: "text-indigo-800 dark:text-indigo-300",
    border: "border-indigo-200 dark:border-indigo-800",
    dot: "bg-indigo-500",
    fill: "#e0e7ff",
    stroke: "#a5b4fc",
  },
  job: {
    bg: "bg-orange-100 dark:bg-orange-900/30",
    text: "text-orange-800 dark:text-orange-300",
    border: "border-orange-200 dark:border-orange-800",
    dot: "bg-orange-500",
    fill: "#ffedd5",
    stroke: "#fdba74",
  },
  workflow: {
    bg: "bg-rose-100 dark:bg-rose-900/30",
    text: "text-rose-800 dark:text-rose-300",
    border: "border-rose-200 dark:border-rose-800",
    dot: "bg-rose-500",
    fill: "#ffe4e6",
    stroke: "#fda4af",
  },
} as const;

/**
 * Get color scheme for an entity type.
 * Falls back to slate if type is unknown.
 */
export function getEntityColors(type: string): EntityColorScheme {
  return entityColors[type.toLowerCase()] ?? entityColors.account;
}

/**
 * Entity badge component using the color system.
 */
export function EntityBadge({ 
  type, 
  label,
  children,
  className,
}: { 
  type: string;
  /** Optional display label. Falls back to children, then to the type string. */
  label?: string;
  children?: React.ReactNode;
  className?: string;
}) {
  const colors = getEntityColors(type);
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium ${colors.bg} ${colors.text} ${className || ""}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${colors.dot}`} />
      {label ?? children ?? type}
    </span>
  );
}

/**
 * Status type color system for workflow/job states
 */
export type StatusType = "completed" | "processing" | "failed" | "running" | "paused" | "pending" | "cancelled";

export const statusColors: Record<StatusType, { bg: string; text: string; border: string; icon: string }> = {
  completed: {
    bg: "bg-emerald-100 dark:bg-emerald-900/30",
    text: "text-emerald-800 dark:text-emerald-300",
    border: "border-emerald-200 dark:border-emerald-800",
    icon: "✓",
  },
  running: {
    bg: "bg-amber-100 dark:bg-amber-900/30",
    text: "text-amber-800 dark:text-amber-300",
    border: "border-amber-200 dark:border-amber-800",
    icon: "↻",
  },
  processing: {
    bg: "bg-amber-100 dark:bg-amber-900/30",
    text: "text-amber-800 dark:text-amber-300",
    border: "border-amber-200 dark:border-amber-800",
    icon: "↻",
  },
  failed: {
    bg: "bg-red-100 dark:bg-red-900/30",
    text: "text-red-800 dark:text-red-300",
    border: "border-red-200 dark:border-red-800",
    icon: "✕",
  },
  paused: {
    bg: "bg-muted",
    text: "text-muted-foreground",
    border: "border-border",
    icon: "⏸",
  },
  pending: {
    bg: "bg-primary/10",
    text: "text-primary",
    border: "border-primary/20",
    icon: "…",
  },
  cancelled: {
    bg: "bg-muted/50",
    text: "text-muted-foreground",
    border: "border-border",
    icon: "⊘",
  },
};

/**
 * Status badge component using the color system.
 */
export function StatusBadgeEntity({ 
  status, 
  showIcon = true,
  className,
}: { 
  status: StatusType;
  showIcon?: boolean;
  className?: string;
}) {
  const colors = statusColors[status];
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${colors.bg} ${colors.text} ${colors.border} ${className || ""}`}>
      {showIcon && <span>{colors.icon}</span>}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
