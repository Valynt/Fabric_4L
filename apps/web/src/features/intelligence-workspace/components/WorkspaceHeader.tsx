/**
 * WorkspaceHeader — Account context bar at the top of the workspace
 */
import { Building2 } from "lucide-react";
import { useWorkspaceContext } from "../hooks/useWorkspaceContext";

export default function WorkspaceHeader() {
  const { accountName, industry, revenue } = useWorkspaceContext();

  return (
    <div className="h-11 bg-muted/50 border-b border-border flex items-center px-6 gap-3 vf-text-body-s shrink-0">
      <Building2 size={14} className="text-muted-foreground shrink-0" />
      <span className="font-semibold text-foreground">{accountName || "Select Account"}</span>
      {industry && (
        <>
          <span className="text-muted-foreground">·</span>
          <span className="text-muted-foreground">{industry}</span>
        </>
      )}
      {revenue && (
        <>
          <span className="text-muted-foreground">·</span>
          <span className="text-muted-foreground">{revenue}</span>
        </>
      )}
    </div>
  );
}
