/**
 * StudioTabFrame — Renders the active studio tab's component
 */
import { Suspense } from "react";
import { useStudioContext } from "../hooks/useStudioContext";
import { getStudioTabDef, getStudioTabOrDefault } from "../studioTabRegistry";

export default function StudioTabFrame() {
  const { accountId, tabId } = useStudioContext();
  const resolvedTabId = getStudioTabOrDefault(tabId);
  const tabDef = getStudioTabDef(resolvedTabId);

  if (!tabDef || !tabDef.component) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        Tab "{resolvedTabId}" not found.
      </div>
    );
  }

  const TabComponent = tabDef.component;

  return (
    <Suspense
      fallback={
        <div className="flex h-full items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
        </div>
      }
    >
      <TabComponent accountId={accountId} />
    </Suspense>
  );
}
