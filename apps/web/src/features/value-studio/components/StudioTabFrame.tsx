/**
 * StudioTabFrame — Renders the active studio tab's component
 */
import { Suspense } from "react";
import { EyeOff } from "lucide-react";
import { EmptyState } from "@/components/states/EmptyState";
import { useStudioContext } from "../hooks/useStudioContext";
import { getStudioTabDef, getStudioTabOrDefault } from "../studioTabRegistry";
import { isValueStudioMissionPrototypeEnabled } from "../mission/prototype";

export default function StudioTabFrame() {
  const { accountId, tabId } = useStudioContext();
  const resolvedTabId = getStudioTabOrDefault(tabId);
  const tabDef = getStudioTabDef(resolvedTabId);

  // Mission is prototype-gated: when disabled, an explicit /studio/mission URL
  // gets an honest "not available" state instead of silently falling back to
  // the default tab.
  if (tabId === "mission" && !isValueStudioMissionPrototypeEnabled) {
    return (
      <EmptyState
        title="Value Studio Mission is not available"
        description="The Mission workspace is a prototype preview and is not enabled in this environment."
        icon={EyeOff}
        className="h-full"
      />
    );
  }

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
