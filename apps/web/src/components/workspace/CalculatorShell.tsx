import { useLocation, useParams } from "react-router-dom";
import WorkspacePagePattern, { type WorkspaceAccountContext } from "@/components/workspace/WorkspacePagePattern";
import { buildPath } from "@/navigation/navigationService";

interface CalculatorShellProps { account: WorkspaceAccountContext; children: React.ReactNode; rightRail?: React.ReactNode; }

const TABS = [
  { key: "roi", label: "ROI" },
  { key: "value-model", label: "Value Model" },
] as const;

export default function CalculatorShell({ account, children, rightRail }: CalculatorShellProps) {
  const { tenantSlug = "", accountId = "" } = useParams<{ tenantSlug: string; accountId: string }>();
  const segments = useLocation().pathname.split("/").filter(Boolean);
  const activeTab = segments[segments.length - 1] || "roi";
  return <WorkspacePagePattern account={account} activeTab={activeTab} tabs={TABS.map((t) => ({ ...t, to: buildPath("/t/:tenantSlug/accounts/:accountId/studio/:tab", { tenantSlug, accountId, tab: t.key }) }))} rightRail={rightRail}>{children}</WorkspacePagePattern>;
}
