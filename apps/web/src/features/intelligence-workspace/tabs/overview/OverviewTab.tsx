/**
 * OverviewTab — Landing view of the value-case workspace.
 *
 * Summarises the case across the four working views and frames the
 * Signal → Driver → Evidence → Stakeholder chain. Always renders (even with no
 * data yet) and links into each view.
 */
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Radio,
  GitBranch,
  ShieldCheck,
  Users,
  type LucideIcon,
} from "lucide-react";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { CenteredLoader } from "@/components/CenteredLoader";
import { cn } from "@/lib/utils";
import { SectionCard } from "@/components/blocks/SectionCard";
import type { IntelligenceTabId } from "../../types";
import { ScreenHeader } from "../_shared/primitives";
import { useTabLink } from "../_shared/useTabLink";
import {
  useWorkspaceCaseId,
  useSignalsData,
  useDriversData,
  useEvidenceData,
  useStakeholdersData,
} from "../_shared/useWorkspaceData";

interface ViewSummary {
  id: IntelligenceTabId;
  label: string;
  icon: LucideIcon;
  count: number;
  question: string;
  purpose: string;
}

export default function OverviewTab() {
  const tabLink = useTabLink();
  const { accountId, caseId, isLoading: caseLoading } = useWorkspaceCaseId();

  const signals = useSignalsData(caseId);
  const drivers = useDriversData(caseId);
  const evidence = useEvidenceData(caseId);
  const stakeholders = useStakeholdersData(caseId);

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }
  if (caseLoading) {
    return <CenteredLoader message="Loading value case…" />;
  }

  const views: ViewSummary[] = [
    {
      id: "signals",
      label: "Signals",
      icon: Radio,
      count: signals.items.length,
      question: "What did we detect?",
      purpose: "Observations extracted from notes, calls, CRM, files, and web sources.",
    },
    {
      id: "drivers",
      label: "Drivers",
      icon: GitBranch,
      count: drivers.items.length,
      question: "What value do they imply?",
      purpose: "Signals translated into economic or strategic value levers.",
    },
    {
      id: "evidence",
      label: "Evidence",
      icon: ShieldCheck,
      count: evidence.items.length,
      question: "What supports the case?",
      purpose: "Source-backed provenance that proves or weakens each claim.",
    },
    {
      id: "stakeholders",
      label: "Stakeholders",
      icon: Users,
      count: stakeholders.items.length,
      question: "Who matters in the deal?",
      purpose: "The buying committee — who must validate, approve, or act.",
    },
  ];

  const nextActions = buildNextActions(views);

  return (
    <div className="mx-auto max-w-5xl">
      <ScreenHeader
        title="Value Case Overview"
        description="This workspace is organised around four working views. Signals capture what we detected, Drivers translate them into value levers, Evidence proves or weakens each claim, and Stakeholders map who must act on the case."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {views.map((view) => {
          const Icon = view.icon;
          return (
            <Link
              key={view.id}
              to={tabLink(view.id)}
              className="group flex flex-col rounded-xl border border-border bg-card p-4 transition-colors hover:border-primary/40 hover:bg-accent/40"
            >
              <div className="flex items-center justify-between">
                <span className="flex h-8 w-8 items-center justify-center rounded-md bg-muted text-muted-foreground">
                  <Icon className="h-4 w-4" aria-hidden="true" />
                </span>
                <span className="vf-display-l font-bold text-foreground">{view.count}</span>
              </div>
              <p className="mt-3 vf-text-body-s font-semibold text-foreground">{view.label}</p>
              <p className="mt-0.5 vf-text-micro text-muted-foreground">{view.question}</p>
              <p className="mt-2 vf-text-caption text-muted-foreground">{view.purpose}</p>
              <span className="mt-3 inline-flex items-center gap-1 vf-text-micro font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
                Open {view.label} <ArrowRight className="h-3 w-3" />
              </span>
            </Link>
          );
        })}
      </div>

      <SectionCard title="The value-case chain" className="mt-6">
        <div className="flex flex-wrap items-center gap-2">
          {views.map((view, i) => (
            <div key={view.id} className="flex items-center gap-2">
              {i > 0 && <ArrowRight className="h-4 w-4 text-muted-foreground/50" aria-hidden="true" />}
              <Link
                to={tabLink(view.id)}
                className={cn(
                  "flex items-center gap-2 rounded-lg border border-border px-3 py-2 transition-colors hover:bg-accent",
                )}
              >
                <view.icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                <span className="vf-text-caption font-medium text-foreground">{view.label}</span>
                <span className="vf-text-micro text-muted-foreground">{view.count}</span>
              </Link>
            </div>
          ))}
        </div>
        <p className="mt-3 vf-text-caption text-muted-foreground">
          Each view is a different lens on the same case. A signal becomes a driver, the driver is
          supported by evidence, and a stakeholder must believe it.
        </p>
      </SectionCard>

      <SectionCard title="What to do next" className="mt-6">
        {nextActions.length === 0 ? (
          <p className="vf-text-caption text-muted-foreground">
            Every working view has content. Review each lens and refine the case.
          </p>
        ) : (
          <ul className="space-y-2">
            {nextActions.map((action) => (
              <li key={action.id}>
                <Link
                  to={tabLink(action.id)}
                  className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2.5 transition-colors hover:bg-accent"
                >
                  <span className="vf-text-caption text-foreground">{action.label}</span>
                  <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}

function buildNextActions(views: ViewSummary[]): { id: IntelligenceTabId; label: string }[] {
  const actions: { id: IntelligenceTabId; label: string }[] = [];
  const byId = Object.fromEntries(views.map((v) => [v.id, v]));

  if ((byId.signals?.count ?? 0) === 0) {
    actions.push({ id: "signals", label: "Capture the signals detected from your source material." });
  }
  if ((byId.drivers?.count ?? 0) === 0) {
    actions.push({ id: "drivers", label: "Translate signals into value drivers the case can prove." });
  }
  if ((byId.evidence?.count ?? 0) === 0) {
    actions.push({ id: "evidence", label: "Attach source-backed evidence for each claim." });
  }
  if ((byId.stakeholders?.count ?? 0) === 0) {
    actions.push({ id: "stakeholders", label: "Map the buying committee and what each person needs." });
  }
  return actions;
}
