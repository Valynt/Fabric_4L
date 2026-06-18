import WorkspacePagePattern, { type WorkspaceAccountContext } from "@/components/workspace/WorkspacePagePattern";
interface ValueCaseShellProps { account: WorkspaceAccountContext; children: React.ReactNode; rightRail?: React.ReactNode; }
export default function ValueCaseShell({ account, children, rightRail }: ValueCaseShellProps) {
  return <WorkspacePagePattern account={account} rightRail={rightRail}>{children}</WorkspacePagePattern>;
}
