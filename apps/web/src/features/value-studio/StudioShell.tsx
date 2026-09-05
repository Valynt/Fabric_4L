/**
 * StudioShell — Main Value Studio workspace shell
 *
 * Single source of workspace chrome:
 *   Header (account context) → Tabs (7 studio views) → Tab content + one right rail
 *
 * Tabs render pure content; the shell owns the account header, the tab bar, and
 * the single persistent AI right rail (agent stream + optional page details).
 *
 * Route: /t/:tenantSlug/accounts/:accountId/studio/:tabId
 */
import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import StudioHeader from "./components/StudioHeader";
import StudioTabs from "./StudioTabs";
import StudioTabFrame from "./components/StudioTabFrame";
import { StudioRightRailContext } from "./StudioRightRailContext";
import { useStudioContext } from "./hooks/useStudioContext";
import { getStudioTabOrDefault } from "./studioTabRegistry";
import RightRail, { type RightRailMode } from "@/components/workspace/RightRail";
import { useAgentEvents } from "@/agui";

export default function StudioShell() {
  const { accountId, tabId, accountName } = useStudioContext();
  const activeTab = getStudioTabOrDefault(tabId);

  const [railMode, setRailMode] = useState<RightRailMode>("agent");
  const [detailContent, setDetailContent] = useState<ReactNode | null>(null);

  // Detail-content lifecycle is owned by the tabs themselves:
  // useStudioDetailRail clears a tab's contribution on unmount and on change,
  // so a shell-side reset would race (and clobber) same-commit injections.

  // Surface tab-injected detail content: when a tab provides detail content
  // (e.g. the mission decision rail), the shell's single right rail switches
  // to Details so the content is visible; when the content is cleared, the
  // rail returns to the agent stream. Manual mode toggles are unaffected —
  // this effect only reacts to content presence transitions.
  useEffect(() => {
    setRailMode(detailContent ? "detail" : "agent");
  }, [detailContent]);

  const { messages, sendMessage, suggestedActions, steps, isStreaming, metadata } =
    useAgentEvents({
      activeTab,
      accountName: accountName || "Account",
      accountId: accountId || undefined,
    });

  const railApi = useMemo(() => ({ setDetailContent }), []);
  return (
    <StudioRightRailContext.Provider value={railApi}>
      <div className="flex flex-col h-full overflow-hidden">
        <StudioHeader />
        <StudioTabs />
        <div className="flex flex-1 min-h-0">
          <div className="flex-1 min-w-0 overflow-y-auto p-6">
            <StudioTabFrame />
          </div>
          <div className="w-[320px] shrink-0 border-l border-border overflow-y-auto">
            <RightRail
              mode={railMode}
              onModeChange={setRailMode}
              activeTab={activeTab}
              detailContent={detailContent}
              messages={messages}
              onSendMessage={sendMessage}
              suggestedActions={suggestedActions}
              steps={steps}
              isStreaming={isStreaming}
              runMetadata={metadata}
            />
          </div>
        </div>
      </div>
    </StudioRightRailContext.Provider>
  );
}
