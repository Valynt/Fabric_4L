/**
 * DriversTab — "What value do the signals imply?"
 *
 * Turns detected signals into value levers: the economic or strategic value the
 * case can prove. Each driver links back to its signals and forward to the
 * evidence and metrics needed to model it.
 */
import { Link } from "react-router-dom";
import { GitBranch, Radio, ShieldCheck } from "lucide-react";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { CenteredLoader } from "@/components/CenteredLoader";
import { ErrorState } from "@/components/states/ErrorState";
import { SectionCard } from "@/components/blocks/SectionCard";
import { Btn } from "@/components/ui/fabric";
import { ScreenHeader, Tag, WorkspaceEmpty } from "../_shared/primitives";
import { useTabLink } from "../_shared/useTabLink";
import { useWorkspaceCaseId, useDriversData } from "../_shared/useWorkspaceData";
import type { WorkspaceDriver } from "../_shared/types";

export default function DriversTab() {
  const tabLink = useTabLink();
  const { accountId, caseId, isLoading: caseLoading } = useWorkspaceCaseId();
  const { items: drivers, isLoading, error } = useDriversData(caseId);

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }
  if (caseLoading || isLoading) {
    return <CenteredLoader message="Loading drivers…" />;
  }
  if (error) {
    return (
      <ErrorState
        title="Failed to load drivers"
        description="The driver data could not be retrieved."
        error={error}
        fullPage
      />
    );
  }

  return (
    <div>
      <ScreenHeader
        title="Value Drivers"
        description="Signals translated into value levers. Drivers answer: what economic or strategic value could this case prove? Each one links back to its signals and forward to the metrics and evidence it needs."
        actions={
          <Link to={tabLink("signals")}>
            <Btn variant="outline">
              <Radio className="mr-1 h-3.5 w-3.5" /> Map from signals
            </Btn>
          </Link>
        }
      />

      {drivers.length === 0 ? (
        <WorkspaceEmpty
          icon={GitBranch}
          title="No value drivers yet"
          purpose="This is where Fabric becomes a value engine, not just a note summariser. Accepted signals become drivers — the why-it-matters of the case."
          bullets={[
            "Examples: labor cost avoidance, churn reduction, faster resolution, SLA improvement",
            "Each driver lists its linked signals and the baseline metrics it needs",
            "Promote a signal from the Signals view to create your first driver",
          ]}
          action={
            <Link to={tabLink("signals")}>
              <Btn variant="primary">Go to Signals</Btn>
            </Link>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {drivers.map((driver) => (
            <DriverCard key={driver.id} driver={driver} evidenceLink={tabLink("evidence")} />
          ))}
        </div>
      )}
    </div>
  );
}

function DriverCard({ driver, evidenceLink }: { driver: WorkspaceDriver; evidenceLink: string }) {
  const linkedSignals = driver.linkedSignals ?? (driver.parentSignal ? [driver.parentSignal] : []);
  const neededInputs = driver.neededInputs ?? driver.subDrivers ?? [];

  return (
    <SectionCard
      title={driver.name}
      action={<Tag className="bg-primary/10 text-primary">Value Driver</Tag>}
    >
      <div className="space-y-3">
        {(driver.estimatedImpact || driver.impactArea) && (
          <Field label="Estimated impact">
            <span className="font-semibold text-success">
              {driver.estimatedImpact ?? driver.impactArea}
            </span>
          </Field>
        )}
        {driver.valueLever && (
          <Field label="Value lever">
            <span className="text-foreground">{driver.valueLever}</span>
          </Field>
        )}
        {typeof driver.contribution === "number" && (
          <Field label="Contribution">
            <span className="text-foreground">{driver.contribution}%</span>
          </Field>
        )}
        {driver.readiness && (
          <Field label="Readiness">
            <Tag className="bg-warning/10 text-warning">{driver.readiness}</Tag>
          </Field>
        )}

        {linkedSignals.length > 0 && (
          <div>
            <p className="vf-text-micro font-medium uppercase tracking-wider text-muted-foreground">
              Linked signals
            </p>
            <ul className="mt-1.5 space-y-1">
              {linkedSignals.map((s) => (
                <li key={s} className="flex items-center gap-2 vf-text-caption text-foreground">
                  <Radio className="h-3 w-3 shrink-0 text-muted-foreground" /> {s}
                </li>
              ))}
            </ul>
          </div>
        )}

        {neededInputs.length > 0 && (
          <div>
            <p className="vf-text-micro font-medium uppercase tracking-wider text-muted-foreground">
              Needed inputs
            </p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {neededInputs.map((input) => (
                <Tag key={input}>{input}</Tag>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center justify-between border-t border-border pt-3">
          <span className="flex items-center gap-1 vf-text-micro text-muted-foreground">
            <Radio className="h-3 w-3" /> {linkedSignals.length} mapped signal
            {linkedSignals.length === 1 ? "" : "s"}
          </span>
          <Link
            to={evidenceLink}
            className="inline-flex items-center gap-1 vf-text-micro font-medium text-primary hover:underline"
          >
            <ShieldCheck className="h-3 w-3" /> View evidence
          </Link>
        </div>
      </div>
    </SectionCard>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 vf-text-caption">
      <span className="text-muted-foreground">{label}</span>
      {children}
    </div>
  );
}
