import { Link } from "react-router-dom";
import { Building2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { PageShell } from "@/components/layout/PageShell";

export interface WorkspaceAccountContext {
  accountName: string;
  industry: string;
  revenue: string;
}

export interface WorkspaceTabItem {
  key: string;
  label: string;
  to: string;
}

interface WorkspacePagePatternProps {
  account: WorkspaceAccountContext;
  activeTab?: string;
  tabs?: WorkspaceTabItem[];
  headerAction?: React.ReactNode;
  rightRail?: React.ReactNode;
  children: React.ReactNode;
}

export default function WorkspacePagePattern({
  account,
  activeTab,
  tabs,
  headerAction,
  rightRail,
  children,
}: WorkspacePagePatternProps) {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="h-11 bg-muted/50 border-b border-border flex items-center px-6 gap-3 vf-text-body-s shrink-0">
        <Building2 size={14} className="text-muted-foreground shrink-0" />
        <span className="font-semibold text-foreground">{account.accountName}</span>
        <span className="text-muted-foreground">·</span>
        <span className="text-muted-foreground">{account.industry}</span>
        <span className="text-muted-foreground">·</span>
        <span className="text-muted-foreground">{account.revenue}</span>
        {headerAction && <><div className="flex-1" />{headerAction}</>}
      </div>

      {tabs && tabs.length > 0 && (
        <div className="flex border-b border-border px-6" role="tablist">
          {tabs.map((tab) => (
            <Link key={tab.key} to={tab.to}>
              <button type="button"
                role="tab"
                aria-selected={activeTab === tab.key}
                className={cn(
                  "px-4 py-2.5 vf-text-body-s font-semibold border-b-2 -mb-px transition-colors",
                  activeTab === tab.key
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                )}
              >
                {tab.label}
              </button>
            </Link>
          ))}
        </div>
      )}

      <div className="flex flex-1 min-h-[400px]">
        <div className="flex-1 min-w-0 overflow-y-auto">
          <PageShell fullWidth className="py-6">{children}</PageShell>
        </div>
        {rightRail && <div className="w-[320px] shrink-0 border-l border-border overflow-y-auto">{rightRail}</div>}
      </div>
    </div>
  );
}
