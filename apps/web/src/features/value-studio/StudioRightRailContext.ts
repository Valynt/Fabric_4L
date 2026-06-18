/**
 * StudioRightRailContext — lets a Studio tab contribute page-specific
 * "Details" content to the single, shell-owned right rail.
 *
 * The Value Studio shell renders exactly one RightRail. Tabs stay pure content
 * and may optionally inject detail content via `useStudioDetailRail`.
 */
import { createContext, useContext, useEffect } from "react";
import type { ReactNode } from "react";

export interface StudioRightRailApi {
  setDetailContent: (node: ReactNode | null) => void;
}

export const StudioRightRailContext = createContext<StudioRightRailApi | null>(null);

/**
 * Inject page-specific detail content into the shell right rail.
 * Content is cleared automatically on unmount or when it changes.
 */
export function useStudioDetailRail(content: ReactNode | null): void {
  const ctx = useContext(StudioRightRailContext);
  useEffect(() => {
    if (!ctx) return;
    ctx.setDetailContent(content);
    return () => ctx.setDetailContent(null);
  }, [ctx, content]);
}
