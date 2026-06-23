/**
 * StudioRailContext — Lets the active Studio tab share state with the shell-level right rail.
 *
 * This keeps the right rail rendered by StudioShell while allowing tabs such as
 * Narrative to push tab-specific detail content into the rail panel.
 */
import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

interface StudioRailContextValue {
  /** Tab-provided detail panel content rendered in the right rail */
  detailContent: ReactNode;
  /** Replace the detail panel content */
  setDetailContent: (content: ReactNode) => void;
  /** Clear the detail panel content */
  clearDetailContent: () => void;
}

const StudioRailContext = createContext<StudioRailContextValue | null>(null);

export function StudioRailProvider({ children }: { children: ReactNode }) {
  const [detailContent, setDetailContentState] = useState<ReactNode>(null);

  const setDetailContent = useCallback((content: ReactNode) => {
    setDetailContentState(content);
  }, []);

  const clearDetailContent = useCallback(() => {
    setDetailContentState(null);
  }, []);

  return (
    <StudioRailContext.Provider
      value={{ detailContent, setDetailContent, clearDetailContent }}
    >
      {children}
    </StudioRailContext.Provider>
  );
}

export function useStudioRail(): StudioRailContextValue {
  const ctx = useContext(StudioRailContext);
  if (!ctx) {
    throw new Error("useStudioRail must be used within StudioRailProvider");
  }
  return ctx;
}
