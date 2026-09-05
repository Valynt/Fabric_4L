/**
 * useFeatureFlags — Check if required feature flags are enabled.
 *
 * Reads from environment variables or a remote flag service.
 * For now, uses Vite import.meta.env flags.
 */

import { useMemo } from "react";

const FEATURE_FLAG_ENV_VALUES: Record<string, string | boolean | undefined> = {
  VITE_ENABLE_C1_REPORTS: import.meta.env.VITE_ENABLE_C1_REPORTS,
  VITE_ENABLE_CRM_SYNC: import.meta.env.VITE_ENABLE_CRM_SYNC,
  VITE_ENABLE_DRIVER_TREE_EXPERIMENTAL_TABS: import.meta.env.VITE_ENABLE_DRIVER_TREE_EXPERIMENTAL_TABS,
  VITE_ENABLE_EXTRACTION_PAUSE_ALL: import.meta.env.VITE_ENABLE_EXTRACTION_PAUSE_ALL,
  VITE_ENABLE_IW_ALTERNATIVES_TAB: import.meta.env.VITE_ENABLE_IW_ALTERNATIVES_TAB,
  VITE_ENABLE_IW_ONTOLOGY_MATCH_TAB: import.meta.env.VITE_ENABLE_IW_ONTOLOGY_MATCH_TAB,
  VITE_ENABLE_IW_SOLUTION_COST_TAB: import.meta.env.VITE_ENABLE_IW_SOLUTION_COST_TAB,
  VITE_ENABLE_VS_MISSION_PROTOTYPE: import.meta.env.VITE_ENABLE_VS_MISSION_PROTOTYPE,
  VITE_ENABLE_VS_SOLUTION_COST_TAB: import.meta.env.VITE_ENABLE_VS_SOLUTION_COST_TAB,
  VITE_ENABLE_WEB_VITALS: import.meta.env.VITE_ENABLE_WEB_VITALS,
};

export function useFeatureFlags(requiredFlags: string[]) {
  const flagsEnabled = useMemo(() => {
    if (requiredFlags.length === 0) return true;
    return requiredFlags.every((flag) => {
      const value = FEATURE_FLAG_ENV_VALUES[flag];
      return value === "true" || value === true;
    });
  }, [requiredFlags]);

  return {
    flagsEnabled,
    isLoading: false,
  };
}
