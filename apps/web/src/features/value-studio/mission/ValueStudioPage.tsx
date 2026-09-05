/**
 * Value Studio (mission-led) — Slice 1 page composition (contract
 * FE-VOS-STUDIO-001 §9, §10).
 *
 * Rendered inside StudioShell as the registry-backed `mission` tab of
 * /t/:tenantSlug/accounts/:accountId/studio/:tabId (DEC-FE-001, revised —
 * StudioShell is the single source of chrome).
 *
 * The page renders ONE typed, versioned case projection and cannot fabricate
 * economic truth, mission activity, authorization, or workflow completion.
 * Every domain action (accept/edit/defer decision, pause/resume mission,
 * undo activity, steer Flo) is separated from local presentation state: in
 * Slice 1 the command backend is not connected, so Proceed/pause/resume/undo
 * surface an explicit no-op notice rather than simulating success
 * (COMMAND_BACKEND_NOTICE).
 *
 * Named states (all ten, §8.1): loading → error → unauthorized → empty →
 * offline/stale/partial banners → ready grid.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { FabricCard } from "@/components/ui/fabric/FabricCard";
import { getStatePath } from "@/navigation/navigationService";
import { useValueStudioProjection } from "./useValueStudioProjection";
import { useStudioDetailRail } from "../StudioRightRailContext";
import {
  VALUE_STUDIO_QUERY_KEYS,
  parseDecisionParam,
  parseFixtureParam,
  parseLensParam,
} from "./queryParams";
import { isValueStudioFixtureSelectorEnabled } from "./prototype";
import {
  buildAcceptRecommendationPreview,
  buildDeferDecisionPreview,
  buildEditDecisionPreview,
  type EditDecisionDraft,
} from "./intentPreview";
import { VALUE_STUDIO_EVENTS, trackValueStudioEvent } from "./analyticsEvents";
import type {
  AudienceLens,
  DecisionIntentPreviewContent,
  DecisionRequestProjection,
  EvidenceReference,
  ValueStudioProjection,
  ValueStudioSectionId,
} from "./types";
import { OpportunityHeader } from "./components/OpportunityHeader";
import { LensSelector } from "./components/LensSelector";
import { LENS_DISCLOSURE } from "./viewModel";
import { JourneyStatus } from "./components/JourneyStatus";
import { MissionStrip } from "./components/MissionStrip";
import { SteerFloTrigger } from "./components/SteerFloTrigger";
import { SteerFloPanel } from "./components/SteerFloPanel";
import { ImpactSummary } from "./components/ImpactSummary";
import { ModelPatchCard } from "./components/ModelPatchCard";
import { BranchComparison } from "./components/BranchComparison";
import { DecisionRail, type DeferDecisionInput } from "./components/DecisionRail";
import { DecisionIntentPreview } from "./components/DecisionIntentPreview";
import { EditDecisionForm } from "./components/EditDecisionForm";
import { EvidenceDrawer } from "./components/EvidenceDrawer";
import { MissionActivityFeed } from "./components/MissionActivityFeed";
import { GenerativeUIFallbackBoundary } from "./components/GenerativeUIFallbackBoundary";
import { StaticGenerativeUIFallback } from "./components/StaticGenerativeUIFallback";
import { InlineError } from "./components/InlineError";
import { OfflineBanner } from "./components/OfflineBanner";
import { ValueStudioSkeletons } from "./components/ValueStudioSkeletons";

/**
 * Slice-1 command policy: the command channel is not connected, so no domain
 * action mutates anything. The notice is explicit and honest — nothing was
 * sent, nothing was changed.
 */
export const COMMAND_BACKEND_NOTICE =
  "No command was sent: the mission command channel is not connected in this slice. Nothing was changed.";

export default function ValueStudioPage() {
  const params = useParams<{ tenantSlug: string; accountId: string }>();
  const tenantSlug = params.tenantSlug ?? "";
  const accountId = params.accountId ?? "";
  const [searchParams, setSearchParams] = useSearchParams();

  // The ?fixture= selector is a dev/test-only debug affordance; production
  // builds ignore it even when the prototype flag is enabled.
  const fixtureName = isValueStudioFixtureSelectorEnabled
    ? parseFixtureParam(searchParams.get(VALUE_STUDIO_QUERY_KEYS.fixture))
    : null;
  const lensParam = parseLensParam(searchParams.get(VALUE_STUDIO_QUERY_KEYS.lens));
  const decisionDeepLink = parseDecisionParam(searchParams.get(VALUE_STUDIO_QUERY_KEYS.decision));

  const { view, isLoading, error, refetch } = useValueStudioProjection(
    tenantSlug,
    accountId,
    fixtureName,
  );

  // ── Local presentation state (never domain state) ──────────────────────────
  const [preview, setPreview] = useState<DecisionIntentPreviewContent | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [editDraft, setEditDraft] = useState<EditDecisionDraft | null>(null);
  const [evidence, setEvidence] = useState<EvidenceReference | null>(null);
  const [steerOpen, setSteerOpen] = useState(false);
  const [railClosed, setRailClosed] = useState(false);
  const [commandNotice, setCommandNotice] = useState<string | null>(null);

  const projectionIdentity =
    view && view.kind !== "loading" && view.kind !== "error" && view.kind !== "unauthorized"
      ? [
          view.projection.projectionVersion,
          view.projection.etag,
          view.projection.decision?.decisionId ?? "no-decision",
          view.projection.decision?.decisionVersion ?? "no-version",
          view.projection.decision?.modelVersion ?? "no-model",
        ].join("/")
      : "unresolved";
  const projectionKey = `${tenantSlug}/${accountId}/${fixtureName ?? "default"}/${projectionIdentity}`;

  // Reset presentation state when a different projection is addressed.
  useEffect(() => {
    setPreview(null);
    setEditOpen(false);
    setEditDraft(null);
    setEvidence(null);
    setSteerOpen(false);
    setRailClosed(false);
    setCommandNotice(null);
  }, [projectionKey]);

  // §14: value_studio_viewed once per projection view (ids + state only).
  useEffect(() => {
    if (!view || view.kind === "loading") return;
    trackValueStudioEvent(VALUE_STUDIO_EVENTS.viewed, {
      fixture: fixtureName ?? "default",
      state: view.kind,
    });
  }, [view, fixtureName]);

  const projection =
    view && view.kind !== "loading" && view.kind !== "error" && view.kind !== "unauthorized"
      ? view.projection
      : null;
  const decision = projection?.decision ?? null;

  // Decision deep link: force the rail open and announce the focus target.
  useEffect(() => {
    if (decisionDeepLink !== null && decision?.decisionId === decisionDeepLink) {
      setRailClosed(false);
      trackValueStudioEvent(VALUE_STUDIO_EVENTS.decisionRailOpened, {
        decisionId: decisionDeepLink,
      });
    }
  }, [decisionDeepLink, decision?.decisionId]);

  const activeLens: AudienceLens = lensParam ?? projection?.activeLens ?? "canonical";

  const selectLens = (lens: AudienceLens) => {
    setSearchParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        if (lens === "canonical") next.delete(VALUE_STUDIO_QUERY_KEYS.lens);
        else next.set(VALUE_STUDIO_QUERY_KEYS.lens, lens);
        return next;
      },
      { replace: true },
    );
    trackValueStudioEvent(VALUE_STUDIO_EVENTS.lensChanged, { lens });
  };

  // ── State machine (contract §10): first match wins ─────────────────────────

  if (isLoading || (!view && !error) || view?.kind === "loading") {
    return <ValueStudioSkeletons />;
  }

  if (error) {
    return (
      <InlineError
        message={error.message}
        correlationId={error.correlationId}
        onRetry={error.retryable ? refetch : undefined}
      />
    );
  }

  if (view?.kind === "error") {
    return (
      <InlineError
        message={view.message}
        correlationId={view.correlationId}
        onRetry={view.retryable ? refetch : undefined}
      />
    );
  }

  // No error and no projection yet — keep showing skeletons until the
  // adapter resolves (keeps `view` narrowed for the remaining states).
  if (!view) {
    return <ValueStudioSkeletons />;
  }

  if (view.kind === "unauthorized") {
    // Contract §8.1: no protected body data in this state.
    return (
      <div className="rounded-lg border border-border bg-card p-6 space-y-3">
        <h1 className="vf-heading-m font-semibold text-foreground">Access required</h1>
        <p className="vf-text-body-m text-muted-foreground">{view.message}</p>
        <Button asChild variant="outline">
          <Link to={getStatePath("accounts", { tenantSlug })}>Back to accounts</Link>
        </Button>
      </div>
    );
  }

  if (view.kind === "empty") {
    return (
      <div className="space-y-6">
        <OpportunityHeader projection={view.projection.case} />
        <FabricCard title="No active mission" padding="loose">
          <p className="vf-text-body-m text-muted-foreground whitespace-pre-line">{view.reason}</p>
          <div className="mt-4">
            <Button asChild>
              <Link to={getStatePath("studio-value-model", { tenantSlug, accountId })}>
                Open value model
              </Link>
            </Button>
          </div>
        </FabricCard>
      </div>
    );
  }

  return (
    <PageBody
      projection={view.projection}
      projectionKey={projectionKey}
      offline={view.kind === "offline"}
      stale={view.kind === "stale"}
      lastSyncedAt={view.kind === "offline" ? view.lastSyncedAt : null}
      activeLens={activeLens}
      decisionDeepLink={decisionDeepLink}
      railClosed={railClosed}
      preview={preview}
      editOpen={editOpen}
      editDraft={editDraft}
      evidence={evidence}
      steerOpen={steerOpen}
      commandNotice={commandNotice}
      onSelectLens={selectLens}
      onReconnect={refetch}
      onAccept={(d) => {
        trackValueStudioEvent(VALUE_STUDIO_EVENTS.decisionIntentPreviewed, {
          decisionId: d.decisionId,
          commandType: "working_target.accept",
        });
        setPreview(buildAcceptRecommendationPreview(d));
      }}
      onEdit={() => setEditOpen(true)}
      onDefer={(d, input) => {
        trackValueStudioEvent(VALUE_STUDIO_EVENTS.decisionIntentPreviewed, {
          decisionId: d.decisionId,
          commandType: "decision.defer",
        });
        setPreview(buildDeferDecisionPreview(d, input));
      }}
      onSubmitDraft={(d, draft) => {
        setEditDraft(draft);
        setEditOpen(false);
        trackValueStudioEvent(VALUE_STUDIO_EVENTS.decisionIntentPreviewed, {
          decisionId: d.decisionId,
          commandType: "decision.edit",
        });
        setPreview(buildEditDecisionPreview(d, draft));
      }}
      onProceed={() => {
        setPreview(null);
        setCommandNotice(COMMAND_BACKEND_NOTICE);
      }}
      onPreviewOpenChange={(open) => {
        if (!open) setPreview(null);
      }}
      onEditOpenChange={setEditOpen}
      onOpenEvidence={(item) => {
        setEvidence(item);
        trackValueStudioEvent(VALUE_STUDIO_EVENTS.evidenceOpened, { evidenceId: item.evidenceId });
      }}
      onEvidenceOpenChange={(open) => {
        if (!open) setEvidence(null);
      }}
      onOpenSteer={() => {
        setSteerOpen(true);
        if (view.projection.mission) {
          trackValueStudioEvent(VALUE_STUDIO_EVENTS.steerFloOpened, {
            missionId: view.projection.mission.missionId,
          });
        }
      }}
      onSteerOpenChange={setSteerOpen}
      onCloseRail={() => setRailClosed(true)}
      onReopenRail={() => setRailClosed(false)}
      onPause={() => setCommandNotice(COMMAND_BACKEND_NOTICE)}
      onResume={() => setCommandNotice(COMMAND_BACKEND_NOTICE)}
      onUndo={() => setCommandNotice(COMMAND_BACKEND_NOTICE)}
      onEventExpanded={(eventId) =>
        trackValueStudioEvent(VALUE_STUDIO_EVENTS.activityEventExpanded, { eventId })
      }
      onDismissNotice={() => setCommandNotice(null)}
    />
  );
}

// ── Composed body (ready/offline/stale/partial) ──────────────────────────────

interface PageBodyProps {
  readonly projection: ValueStudioProjection;
  readonly projectionKey: string;
  readonly offline: boolean;
  readonly stale: boolean;
  readonly lastSyncedAt: string | null;
  readonly activeLens: AudienceLens;
  readonly decisionDeepLink: string | null;
  readonly railClosed: boolean;
  readonly preview: DecisionIntentPreviewContent | null;
  readonly editOpen: boolean;
  readonly editDraft: EditDecisionDraft | null;
  readonly evidence: EvidenceReference | null;
  readonly steerOpen: boolean;
  readonly commandNotice: string | null;
  readonly onSelectLens: (lens: AudienceLens) => void;
  readonly onReconnect: () => void;
  readonly onAccept: (decision: DecisionRequestProjection) => void;
  readonly onEdit: () => void;
  readonly onDefer: (decision: DecisionRequestProjection, input: DeferDecisionInput) => void;
  readonly onSubmitDraft: (decision: DecisionRequestProjection, draft: EditDecisionDraft) => void;
  readonly onProceed: () => void;
  readonly onPreviewOpenChange: (open: boolean) => void;
  readonly onEditOpenChange: (open: boolean) => void;
  readonly onOpenEvidence: (evidence: EvidenceReference) => void;
  readonly onEvidenceOpenChange: (open: boolean) => void;
  readonly onOpenSteer: () => void;
  readonly onSteerOpenChange: (open: boolean) => void;
  readonly onCloseRail: () => void;
  readonly onReopenRail: () => void;
  readonly onPause: () => void;
  readonly onResume: () => void;
  readonly onUndo: (eventId: string) => void;
  readonly onEventExpanded: (eventId: string) => void;
  readonly onDismissNotice: () => void;
}

function PageBody({
  projection,
  projectionKey,
  offline,
  stale,
  lastSyncedAt,
  activeLens,
  decisionDeepLink,
  railClosed,
  preview,
  editOpen,
  editDraft,
  evidence,
  steerOpen,
  commandNotice,
  onSelectLens,
  onReconnect,
  onAccept,
  onEdit,
  onDefer,
  onSubmitDraft,
  onProceed,
  onPreviewOpenChange,
  onEditOpenChange,
  onOpenEvidence,
  onEvidenceOpenChange,
  onOpenSteer,
  onSteerOpenChange,
  onCloseRail,
  onReopenRail,
  onPause,
  onResume,
  onUndo,
  onEventExpanded,
  onDismissNotice,
}: PageBodyProps) {
  const decision = projection.decision;
  const sectionUnavailableReason = (section: ValueStudioSectionId): string | null => {
    if (!projection.partial?.unavailableSections.includes(section)) return null;
    return projection.partial.reasons[section] ?? "This section is temporarily unavailable.";
  };
  const activityUnavailable = sectionUnavailableReason("activity");

  // ── Single-chrome decision rail (DEC-FE-001/008) ───────────────────────────
  // The decision surface is injected into the StudioShell-owned right rail via
  // useStudioDetailRail; the page never renders a second, page-local rail.
  // Handler identities change every render, so they are read through a ref —
  // the memoized rail content only changes identity when its real inputs do
  // (otherwise every shell re-render would loop through setDetailContent).
  const railHandlers = useRef({
    onAccept,
    onEdit,
    onDefer,
    onOpenEvidence,
    onCloseRail,
    onReopenRail,
  });
  useEffect(() => {
    railHandlers.current = {
      onAccept,
      onEdit,
      onDefer,
      onOpenEvidence,
      onCloseRail,
      onReopenRail,
    };
  });

  const decisionRailContent = useMemo<ReactNode>(() => {
    if (!decision) return null;
    if (railClosed) {
      return (
        <FabricCard title="Review required" padding="compact">
          <p className="vf-text-body-s text-muted-foreground">
            {decision.decisionId} — {decision.title}
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={() => railHandlers.current.onReopenRail()}
          >
            Reopen review
          </Button>
        </FabricCard>
      );
    }
    return (
      <>
        {decisionDeepLink !== null && decision.decisionId === decisionDeepLink && (
          <span className="sr-only" data-testid="decision-deep-link">
            Focused decision {decisionDeepLink}
          </span>
        )}
        <DecisionRail
          decision={decision}
          stale={stale}
          offline={offline}
          submitting={false}
          onAccept={() => railHandlers.current.onAccept(decision)}
          onEdit={() => railHandlers.current.onEdit()}
          onDefer={(input) => railHandlers.current.onDefer(decision, input)}
          onOpenEvidence={(item) => railHandlers.current.onOpenEvidence(item)}
          onClose={() => railHandlers.current.onCloseRail()}
        />
      </>
    );
  }, [decision, railClosed, stale, offline, decisionDeepLink]);
  useStudioDetailRail(decisionRailContent);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <OpportunityHeader projection={projection.case} />
        <div className="flex flex-wrap items-center gap-3">
          {projection.mission && (
            <SteerFloTrigger mission={projection.mission} onOpen={onOpenSteer} />
          )}
          <LensSelector activeLens={activeLens} onSelect={onSelectLens} />
        </div>
      </div>

      {/* FE-VOS-STUDIO-001: each lens discloses what it emphasizes. */}
      <p data-testid="lens-disclosure" className="vf-text-caption text-muted-foreground">
        Viewing as {LENS_DISCLOSURE[activeLens]}
      </p>

      {/* Slice 1 renders fixture-backed demo data only; the badge must stay
          visible so nobody mistakes it for live account data. */}
      <div className="flex items-center gap-2">
        <span
          data-testid="demo-data-badge"
          className="inline-flex items-center rounded-md border border-warning/40 bg-warning/10 px-2 py-0.5 vf-text-caption font-medium text-foreground"
        >
          Demo data — prototype
        </span>
      </div>

      <JourneyStatus journey={projection.journey} />

      {offline && lastSyncedAt !== null && (
        <OfflineBanner lastSyncedAt={lastSyncedAt} onReconnect={onReconnect} />
      )}

      {stale && projection.stale && (
        <div
          role="alert"
          className="rounded-md border border-destructive/40 bg-destructive/5 px-4 py-3"
        >
          <p className="vf-text-body-s font-medium text-destructive">
            This view is out of date.
          </p>
          <p className="vf-text-caption text-muted-foreground mt-0.5">
            {projection.stale.reason} (expected model {projection.stale.expectedModelVersion},
            current {projection.stale.currentModelVersion})
          </p>
          <Button variant="outline" size="sm" className="mt-2" onClick={onReconnect}>
            Load latest projection
          </Button>
        </div>
      )}

      {projection.partial && (
        <div
          role="status"
          className="rounded-md border border-warning/40 bg-warning/10 px-4 py-3"
        >
          <p className="vf-text-body-s text-foreground">
            Some sections are temporarily unavailable. Available data is unaffected and shown
            below.
          </p>
        </div>
      )}

      {commandNotice && (
        <div
          role="status"
          className="flex items-start justify-between gap-3 rounded-md border border-border bg-muted/40 px-4 py-3"
        >
          <p className="vf-text-body-s text-foreground">{commandNotice}</p>
          <Button variant="ghost" size="sm" onClick={onDismissNotice}>
            Dismiss
          </Button>
        </div>
      )}

      {projection.mission && (
        <MissionStrip
          mission={projection.mission}
          onPause={onPause}
          onResume={onResume}
          commandPending={false}
          stale={stale}
          offline={offline}
        />
      )}

      <ImpactSummary economics={projection.case.economics} />

      {projection.generativeUiFallback && (
        <StaticGenerativeUIFallback
          componentName={projection.generativeUiFallback.componentName}
          failureClass={projection.generativeUiFallback.failureClass}
        />
      )}

      {/* Single-column workspace: decision chrome lives in the shell-owned
          right rail (injected above), never in a second page-local rail. */}
      <div className="space-y-6 min-w-0">
        {projection.patch && <ModelPatchCard patch={projection.patch} />}

        <GenerativeUIFallbackBoundary componentName="BranchComparison" resetKey={projectionKey}>
          <BranchComparison comparison={projection.branchComparison} />
        </GenerativeUIFallbackBoundary>

        {activityUnavailable !== null ? (
          <FabricCard title="Mission activity" padding="normal">
            <p role="status" className="vf-text-body-s text-muted-foreground">
              {activityUnavailable}
            </p>
          </FabricCard>
        ) : (
          <MissionActivityFeed
            events={projection.activity}
            onUndo={onUndo}
            onEventExpanded={onEventExpanded}
            stale={stale}
            offline={offline}
          />
        )}

        {!decision && (
          <FabricCard title="Review required" padding="compact">
            <p className="vf-text-body-s text-muted-foreground">
              No open decisions for this mission.
            </p>
          </FabricCard>
        )}
      </div>

      {decision && (
        <>
          <DecisionIntentPreview
            preview={preview}
            open={preview !== null}
            onOpenChange={onPreviewOpenChange}
            onProceed={onProceed}
          />
          <EditDecisionForm
            decision={decision}
            open={editOpen}
            onOpenChange={onEditOpenChange}
            onSubmitDraft={(draft) => onSubmitDraft(decision, draft)}
            initialDraft={editDraft}
          />
        </>
      )}

      <EvidenceDrawer
        evidence={evidence}
        open={evidence !== null}
        onOpenChange={onEvidenceOpenChange}
      />

      {projection.mission && (
        <SteerFloPanel
          mission={projection.mission}
          open={steerOpen}
          onOpenChange={onSteerOpenChange}
        />
      )}
    </div>
  );
}
