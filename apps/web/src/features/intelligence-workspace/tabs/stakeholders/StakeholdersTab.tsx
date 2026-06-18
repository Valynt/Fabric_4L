/**
 * StakeholdersTab — "Who matters in the deal?"
 *
 * Maps the buying committee: roles, influence, priorities, objections, and the
 * next action for each person. Value cases are buying-committee artifacts, not
 * just financial models.
 */
import { Link } from "react-router-dom";
import { Users, GitBranch, Quote } from "lucide-react";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { CenteredLoader } from "@/components/CenteredLoader";
import { ErrorState } from "@/components/states/ErrorState";
import { SectionCard } from "@/components/blocks/SectionCard";
import { cn } from "@/lib/utils";
import { ScreenHeader, Tag, WorkspaceEmpty } from "../_shared/primitives";
import { InfluenceBadge, RoleBadge } from "../_shared/badges";
import { useTabLink } from "../_shared/useTabLink";
import { useWorkspaceCaseId, useStakeholdersData } from "../_shared/useWorkspaceData";
import type { WorkspaceStakeholder } from "../_shared/types";

const POSITION_STYLES: Record<string, string> = {
  champion: "bg-success/10 text-success",
  supporter: "bg-success/10 text-success",
  neutral: "bg-muted text-muted-foreground",
  blocker: "bg-destructive/10 text-destructive",
  detractor: "bg-destructive/10 text-destructive",
};

function PositionBadge({ position }: { position?: string }) {
  if (!position) return null;
  const key = position.toLowerCase();
  const label = position[0].toUpperCase() + position.slice(1);
  return <Tag className={cn(POSITION_STYLES[key])}>{label}</Tag>;
}

export default function StakeholdersTab() {
  const tabLink = useTabLink();
  const { accountId, caseId, isLoading: caseLoading } = useWorkspaceCaseId();
  const { items: stakeholders, isLoading, error } = useStakeholdersData(caseId);

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }
  if (caseLoading || isLoading) {
    return <CenteredLoader message="Loading stakeholders…" />;
  }
  if (error) {
    return (
      <ErrorState
        title="Failed to load stakeholders"
        description="The stakeholder data could not be retrieved."
        error={error}
        fullPage
      />
    );
  }

  return (
    <div>
      <ScreenHeader
        title="Stakeholders"
        description="The people, roles, and influence in the deal. This view answers: who needs to believe this case, and what do they need to see?"
      />

      {stakeholders.length === 0 ? (
        <WorkspaceEmpty
          icon={Users}
          title="No stakeholders mapped yet"
          purpose="Value cases are buying-committee artifacts. Map who must validate, approve, or act on the case."
          bullets={[
            "Roles: economic buyer, champion, technical buyer, sponsor, procurement, blocker, legal",
            "Capture each person's influence, priorities, and objections",
            "Link stakeholders to the drivers they care about",
          ]}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {stakeholders.map((person) => (
            <StakeholderCard key={person.id} person={person} driverLink={tabLink("drivers")} />
          ))}
        </div>
      )}
    </div>
  );
}

function StakeholderCard({
  person,
  driverLink,
}: {
  person: WorkspaceStakeholder;
  driverLink: string;
}) {
  const influence = person.influence ?? person.engagementLevel;
  const priorities = person.priorities ?? [];
  const objections = person.objections ?? [];
  const quotes = person.quotes ?? [];

  return (
    <SectionCard
      title={person.name}
      description={person.title}
      action={<PositionBadge position={person.position} />}
    >
      <div className="space-y-3">
        <div className="flex flex-wrap gap-1.5">
          <RoleBadge role={person.role} />
          <InfluenceBadge level={influence} />
        </div>

        {priorities.length > 0 && (
          <Block label="Priorities">
            <ul className="space-y-1">
              {priorities.map((p) => (
                <li key={p} className="vf-text-caption text-foreground">• {p}</li>
              ))}
            </ul>
          </Block>
        )}

        {objections.length > 0 && (
          <Block label="Objections">
            <ul className="space-y-1">
              {objections.map((o) => (
                <li key={o} className="vf-text-caption text-warning">• {o}</li>
              ))}
            </ul>
          </Block>
        )}

        {quotes.length > 0 && (
          <Block label="Extracted snippets">
            <div className="space-y-1.5">
              {quotes.map((q) => (
                <p
                  key={q}
                  className="flex gap-1.5 rounded-md border border-border bg-muted/30 p-2 vf-text-caption italic text-muted-foreground"
                >
                  <Quote className="h-3 w-3 shrink-0" /> {q}
                </p>
              ))}
            </div>
          </Block>
        )}

        {person.nextAction && (
          <Block label="Next action">
            <p className="vf-text-caption text-foreground">{person.nextAction}</p>
          </Block>
        )}

        {(person.linkedDriver || person.evidenceSource) && (
          <div className="flex items-center justify-between border-t border-border pt-3">
            <span className="vf-text-micro text-muted-foreground">
              {person.evidenceSource ? `Source: ${person.evidenceSource}` : ""}
            </span>
            {person.linkedDriver && (
              <Link
                to={driverLink}
                className="inline-flex items-center gap-1 vf-text-micro font-medium text-primary hover:underline"
              >
                <GitBranch className="h-3 w-3" /> {person.linkedDriver}
              </Link>
            )}
          </div>
        )}
      </div>
    </SectionCard>
  );
}

function Block({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="vf-text-micro font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
      <div className="mt-1.5">{children}</div>
    </div>
  );
}
