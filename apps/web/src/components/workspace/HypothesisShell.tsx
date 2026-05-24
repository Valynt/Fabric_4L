import { useLocation, useParams } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { useNavigation } from "@/hooks/useNavigation";
import WorkspacePagePattern, { type WorkspaceAccountContext } from "@/components/workspace/WorkspacePagePattern";
import { buildPath } from "@/navigation/navigationService";
import { Btn } from "@/components/ui/fabric";

interface HypothesisShellProps { account: WorkspaceAccountContext; children: React.ReactNode; rightRail?: React.ReactNode; }
const TABS = [
  { key: "hypotheses", label: "Hypotheses" },
  { key: "discovery-questions", label: "Discovery Questions" },
  { key: "persona-fit", label: "Persona Fit" },
  { key: "assumptions", label: "Assumptions" },
] as const;

export default function HypothesisShell({ account, children, rightRail }: HypothesisShellProps) {
  const { tenantSlug = "", accountId = "" } = useParams<{ tenantSlug: string; accountId: string }>();
  const segments = useLocation().pathname.split("/").filter(Boolean);
  const activeTab = segments[segments.length - 1] || "hypotheses";
  const { navigateTo } = useNavigation();
  return <WorkspacePagePattern account={account} activeTab={activeTab} tabs={TABS.map((t) => ({ ...t, to: buildPath("/t/:tenantSlug/accounts/:accountId/intelligence/:tab", { tenantSlug, accountId, tab: t.key }) }))} rightRail={rightRail} headerAction={<Btn variant="primary" onClick={() => navigateTo("drivers", { accountId })} className="gap-1.5"><Sparkles size={13} />Generate Driver Tree</Btn>}>{children}</WorkspacePagePattern>;
}
