/**
 * StudioAgentRail — Reusable agent stream rail for Studio tabs
 */
import { useState } from "react";
import RightRail, { type RightRailMode } from "@/components/workspace/RightRail";
import { useAgentEvents } from "@/agui";
import { useAccount } from "@/hooks/useAccounts";
import type { StudioTabRailProps } from "../types";

interface StudioAgentRailProps extends StudioTabRailProps {
  activeTab: string;
}

export default function StudioAgentRail({ accountId, activeTab }: StudioAgentRailProps) {
  const [mode, setMode] = useState<RightRailMode>("agent");
  const { data: account } = useAccount(accountId ?? null);
  const accountName = account?.name ?? accountId ?? "Account";
  const { messages, sendMessage, suggestedActions, steps, isStreaming, metadata } =
    useAgentEvents({ activeTab, accountName });

  return (
    <RightRail
      mode={mode}
      onModeChange={setMode}
      activeTab={activeTab}
      messages={messages}
      onSendMessage={sendMessage}
      suggestedActions={suggestedActions}
      steps={steps}
      isStreaming={isStreaming}
      runMetadata={metadata}
    />
  );
}
