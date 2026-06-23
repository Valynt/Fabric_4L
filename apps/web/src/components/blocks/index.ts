/**
 * Design System — Block Components
 *
 * Extracted from _ui-prototype and adapted for the production frontend.
 * These are higher-level business components built from shadcn/ui and Fabric primitives.
 *
 * These components represent domain-specific UI patterns and should be preferred
 * over lower-level shadcn/Radix primitives in `components/ui/`.
 *
 * Usage:
 *   import { StatCard, StatusBadgeBlock, ProgressBar, SectionCard } from "@/components/blocks";
 */

// ── Metric & Status ──────────────────────────────────────────────────────
export { StatCard } from "./StatCard";
export type { StatCardProps } from "./StatCard";

export { StatusBadgeBlock } from "@/components/ui/fabric/StatusBadge";
export type {
  StatusBadgeBlockProps,
  BlockStatus as Status,
} from "@/components/ui/fabric/StatusBadge";

export { ProgressBar } from "./ProgressBar";
export type { ProgressBarProps } from "./ProgressBar";

// ── Layout ────────────────────────────────────────────────────────────────
export { SectionCard } from "./SectionCard";
export type { SectionCardProps } from "./SectionCard";

// ── Navigation ───────────────────────────────────────────────────────────
export { TabNav } from "./TabNav";
export type { TabItem, TabNavProps } from "./TabNav";

export { TopTabNav } from "./TopTabNav";
export type { TopTabItem, TopTabNavProps } from "./TopTabNav";

export { HorizontalTabWrapper } from "./HorizontalTabWrapper";
export type { TabConfig, HorizontalTabWrapperProps } from "./HorizontalTabWrapper";

// ── Evidence & Provenance ─────────────────────────────────────────────────
export { EvidenceCard } from "./EvidenceCard";
export type { EvidenceCardProps } from "./EvidenceCard";

// ── Value Model ──────────────────────────────────────────────────────────
export { ModelInputsTracker } from "./ModelInputsTracker";
export type { InputStatus, ModelInput, ModelInputsTrackerProps } from "./ModelInputsTracker";

export { ModelReadinessMeter } from "./ModelReadinessMeter";
export type { ReadinessOpportunity, ModelReadinessMeterProps } from "./ModelReadinessMeter";
