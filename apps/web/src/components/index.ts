/**
 * Global Component Library
 * 
 * Single import source for all shared components across the application.
 * Organized by category for discoverability.
 * 
 * @example
 * ```tsx
 * import { 
 *   PageShell, 
 *   Button, 
 *   Card, 
 *   toast 
 * } from "@/components";
 * ```
 */

// ── Layout / Shell Components ───────────────────────────────────────────────

export { PageShell } from "./layout/PageShell";
export { RightRailPanel } from "./layout/RightRailPanel";

// ── Navigation ──────────────────────────────────────────────────────────────

export { TieredNav, type UserTier, NAV_SPINE } from "./navigation/TieredNav";
export { AccountPicker, type AccountPickerProps } from "./navigation/AccountPicker";
export { MobilePersistentSidebar, type MobilePersistentSidebarProps } from "./navigation/MobilePersistentSidebar";
// â”€â”€ Workspace Shells â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export { default as IntelligenceShell } from "./workspace/IntelligenceShell";
export { default as HypothesisShell } from "./workspace/HypothesisShell";

// â”€â”€ State Components (Loading, Empty, Error) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export {
  LoadingState,
  EmptyState,
  ErrorState,
  PageState,
} from "./states";

// â”€â”€ UI Primitives (shadcn/ui) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export * from "./ui/accordion";
export * from "./ui/alert";
export * from "./ui/alert-dialog";
export * from "./ui/aspect-ratio";
export * from "./ui/avatar";
export * from "./ui/badge";
export * from "./ui/breadcrumb";
export * from "./ui/button";
export * from "./ui/button-group";
export * from "./ui/calendar";
export * from "./ui/card";
export * from "./ui/carousel";
// NOTE: "./ui/chart" is intentionally NOT re-exported from this barrel. It
// imports recharts statically, and this barrel is loaded eagerly by the app
// shell, which would pull recharts into the main bundle. No consumer imports
// chart primitives today; when one does, it should import them directly from
// "@/components/ui/chart" inside a lazy-loaded route.
export * from "./ui/checkbox";
export * from "./ui/collapsible";
export * from "./ui/command";
export * from "./ui/context-menu";
export * from "./ui/dialog";
export * from "./ui/drawer";
export * from "./ui/dropdown-menu";
export * from "./ui/empty";
export * from "./ui/field";
export * from "./ui/form";
export * from "./ui/hover-card";
export * from "./ui/input";
export * from "./ui/input-group";
export * from "./ui/input-otp";
export * from "./ui/item";
export * from "./ui/kbd";
export * from "./ui/label";
export * from "./ui/menubar";
export * from "./ui/navigation-menu";
export * from "./ui/pagination";
export * from "./ui/popover";
export * from "./ui/progress";
export * from "./ui/radio-group";
export * from "./ui/resizable";
export * from "./ui/scroll-area";
export * from "./ui/select";
export * from "./ui/separator";
export * from "./ui/sheet";
export * from "./ui/sidebar";
export * from "./ui/skeleton";
export * from "./ui/slider";
export * from "./ui/sonner";
export * from "./ui/spinner";
export * from "./ui/switch";
export * from "./ui/table";
export * from "./ui/tabs";
export * from "./ui/textarea";
export * from "./ui/toggle";
export * from "./ui/toggle-group";
export * from "./ui/tooltip";

// â”€â”€ Block Components (Design System) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export {
  StatCard,
  StatusBadgeBlock,
  ProgressBar,
  TabNav,
  TopTabNav,
  ModelInputsTracker,
  ModelReadinessMeter,
} from "./blocks";
export type {
  StatCardProps,
  Status as BlockStatus,
  StatusBadgeBlockProps,
  ProgressBarProps,
  TabItem,
  TabNavProps,
  TopTabItem,
  TopTabNavProps,
  InputStatus,
  ModelInput,
  ModelInputsTrackerProps,
  ReadinessOpportunity,
  ModelReadinessMeterProps,
} from "./blocks";

// â”€â”€ Domain Components (Fabric-specific) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export {
  PageHeader,
  FabricCard,
  FilterBar,
  StatusBadge,
  MetricCard,
  DataTable,
  SidePanel,
  FabricDialog,
  TeamMemberList,
  EntityBadge,
} from "./ui/fabric";

// â”€â”€ Shared Contextual Components â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export { default as ErrorBoundary } from "./ErrorBoundary";
export { QueryState } from "./QueryState";
export { CenteredLoader } from "./CenteredLoader";
export { AccountRequiredGuard } from "./AccountRequiredGuard";

// â”€â”€ Graph Components â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export { GraphVisualization } from "./graph/GraphVisualization";
export { GraphInspectorPanel } from "./graph/GraphInspectorPanel";

// â”€â”€ Ontology Components â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export { PropertyEditor } from "./ontology/PropertyEditor";
export { RelationshipMap } from "./ontology/RelationshipMap";
export { TypeTree } from "./ontology/TypeTree";

// â”€â”€ Integration Components â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export { IntegrationConfigPanel } from "./integrations/IntegrationConfigPanel";
export { IntegrationGrid } from "./integrations/IntegrationGrid";
export { IntegrationList } from "./integrations/IntegrationList";

// â”€â”€ Auth Components â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export { SSOButtons } from "./auth/SSOButtons";

// â”€â”€ Error Handling & Loading States â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export { ErrorFallback, InlineError, SectionError } from "./ui/ErrorFallback";
export {
  SkeletonLine,
  SkeletonText,
  SkeletonCard,
  SkeletonTable,
  SkeletonTableRow,
  SkeletonPage,
  SkeletonStats,
  SkeletonForm,
} from "./ui/SkeletonViews";

// â”€â”€ ValuePack Framework Components â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export {
  ValuePackCard,
  ValuePackCardSkeleton,
  ValuePackDetail,
  type ValuePackFrameworkData,
  type OntologyMapData,
  type TemplateLibraryData,
  type ValuePackComparisonData,
  type ValuePackSuggestion,
  type ProspectProfile,
} from "./valuepack";

// â”€â”€ Re-export toast utilities for convenience â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export { toast } from "sonner";

