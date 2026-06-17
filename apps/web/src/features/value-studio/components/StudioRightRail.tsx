/**
 * StudioRightRail — Shell-level right rail selected by active tab
 */
import { useState } from "react";
import RightRail, { type RightRailMode } from "@/components/workspace/RightRail";
import { useStudioContext } from "../hooks/useStudioContext";
import { useStudioRail } from "../context/StudioRailContext";
import { getStudioTabDef, getStudioTabOrDefault } from "../studioTabRegistry";

export default function StudioRightRail() {
  const { accountId, tabId } = useStudioContext();
  const { detailContent } = useStudioRail();
  const [detailMode, setDetailMode] = useState<RightRailMode>("detail");
  const resolvedTabId = getStudioTabOrDefault(tabId);
  const tabDef = getStudioTabDef(resolvedTabId);
  const RailComponent = tabDef?.rightRail;

  if (detailContent) {
    return (
      <div className="w-[320px] shrink-0 border-l border-border overflow-y-auto">
        <RightRail
          mode={detailMode}
          onModeChange={setDetailMode}
          detailContent={detailContent}
          activeTab={resolvedTabId}
          messages={[]}
          onSendMessage={() => {}}
        />
      </div>
    );
  }

  if (!RailComponent) {
    return (
      <div className="w-[320px] shrink-0 border-l border-border bg-background" />
    );
  }

  return (
    <div className="w-[320px] shrink-0 border-l border-border overflow-y-auto">
      <RailComponent accountId={accountId} />
    </div>
  );
}
