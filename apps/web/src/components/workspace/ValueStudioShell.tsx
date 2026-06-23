import { Link, useLocation, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import WorkspacePagePattern, { type WorkspaceAccountContext } from "@/components/workspace/WorkspacePagePattern";
import { buildPath } from "@/navigation/navigationService";
import { Btn } from "@/components/ui/fabric";
import { getActiveStudioTabDefs, getStudioTabOrDefault } from "@/features/value-studio/studioTabRegistry";

interface ValueStudioShellProps {
  account: WorkspaceAccountContext;
  children: React.ReactNode;
  rightRail?: React.ReactNode;
}

export default function ValueStudioShell({ account, children, rightRail }: ValueStudioShellProps) {
  const { tenantSlug = "", accountId = "", tabId } = useParams<{
    tenantSlug: string;
    accountId: string;
    tabId?: string;
  }>();
  const segments = useLocation().pathname.split("/").filter(Boolean);
  const activeTab = getStudioTabOrDefault(tabId ?? segments[segments.length - 1]);
  const tabs = getActiveStudioTabDefs().map((tab) => ({
    key: tab.id,
    label: tab.label,
    to: buildPath("/t/:tenantSlug/accounts/:accountId/studio/:tab", {
      tenantSlug,
      accountId,
      tab: tab.id,
    }),
  }));
  const intelligenceHref = buildPath("/t/:tenantSlug/accounts/:accountId/intelligence/:tab", {
    tenantSlug,
    accountId,
    tab: "signals",
  });

  return (
    <WorkspacePagePattern
      account={account}
      activeTab={activeTab}
      tabs={tabs}
      rightRail={rightRail}
      headerAction={
        <Link to={intelligenceHref}>
          <Btn variant="outline" className="gap-1.5">
            <ArrowLeft size={13} />
            Back to Intelligence
          </Btn>
        </Link>
      }
    >
      {children}
    </WorkspacePagePattern>
  );
}
