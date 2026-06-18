/**
 * WorkspaceEmptyState — Shown when a tab is not release-enabled
 */
import { Construction } from "lucide-react";

interface Props {
  tabId: string;
}

export default function WorkspaceEmptyState({ tabId }: Props) {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[300px] gap-4 text-muted-foreground">
      <Construction size={40} className="opacity-50" aria-hidden="true" />
      <div className="text-center">
        <p className="text-sm font-medium">Workspace tab not enabled</p>
        <p className="text-xs mt-1">
          The <span className="font-mono text-foreground">{tabId}</span> tab is not part of this release.
        </p>
      </div>
    </div>
  );
}
