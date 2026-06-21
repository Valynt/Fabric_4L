/**
 * ValuePack Framework Components
 * 
 * UI components for the ValuePack Framework v1.0 system.
 */

export { ValuePackCard, ValuePackCardSkeleton } from "./ValuePackCard";
export { ValuePackDetail } from "./ValuePackDetail";

// Re-export framework DTO types from the canonical API module.
export type {
  ValuePackFrameworkData,
  OntologyMapData,
  TemplateLibraryData,
  ValuePackComparisonData,
} from "@/api/valuePackFramework";

// Suggestion helpers are still defined by the value-pack hook.
export type {
  ValuePackSuggestion,
  ProspectProfile,
} from "@/hooks/useValuePacks";
