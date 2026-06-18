import WorkspacePagePattern, { type WorkspaceAccountContext } from "@/components/workspace/WorkspacePagePattern";
interface RealizationShellProps { account: WorkspaceAccountContext; children: React.ReactNode; rightRail?: React.ReactNode; }
export default function RealizationShell({ account, children, rightRail }: RealizationShellProps) {
  return <WorkspacePagePattern account={account} rightRail={rightRail}>{children}</WorkspacePagePattern>;
}
