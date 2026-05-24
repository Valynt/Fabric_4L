/**
 * useFeatureFlags — Check if required feature flags are enabled.
 *
 * Reads from environment variables or a remote flag service.
 * For now, uses Vite import.meta.env flags.
 */

import { useMemo } from "react";

export function useFeatureFlags(requiredFlags: string[]) {
  const flagsEnabled = useMemo(() => {
    if (requiredFlags.length === 0) return true;
    return requiredFlags.every((flag) => {
      const value = import.meta.env[flag];
      return value === "true" || value === true;
    });
  }, [requiredFlags]);

  return {
    flagsEnabled,
    isLoading: false,
  };
}
