import * as React from "react";
import {
  AlertCircle,
  ArrowRight,
  Briefcase,
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  Cloud,
  FileText,
  Gauge,
  Globe,
  Headphones,
  Loader2,
  Mail,
  Search,
  ShieldCheck,
  Users,
} from "lucide-react";

import { PageShell } from "@/components";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { useAuthContext } from "@/contexts/AuthContext";
import { useRecentIngestionJobs, type IngestionJob } from "@/hooks/useIngestion";
import { useNavigation } from "@/hooks/useNavigation";
import { useProspectSetupAccountCreate } from "@/hooks/useProspectSetupAccount";
import {
  buildProspectPayloadFromDraft,
  parseValueCaseDraft,
  type IntakeSource,
  type SourceMode,
  type ValueCaseDraft,
} from "./valueNarrativeHomeParser";

type SourceAction = {
  mode: SourceMode;
  label: string;
  description: string;
  icon: React.ElementType;
};

type WebMode = "url" | "search";

const SOURCE_LIMIT = 10;

const SOURCE_ACTIONS: SourceAction[] = [
  {
    mode: "notes",
    label: "Notes",
    description: "Copied text",
    icon: ClipboardList,
  },
  {
    mode: "url",
    label: "Web/Search",
    description: "URL or research",
    icon: Globe,
  },
  {
    mode: "audio",
    label: "Audio",
    description: "Call recording",
    icon: Headphones,
  },
  {
    mode: "crm",
    label: "CRM Link",
    description: "Opportunity URL",
    icon: Briefcase,
  },
  {
    mode: "file",
    label: "PDF File",
    description: "Docs or images",
    icon: FileText,
  },
  {
    mode: "meeting",
    label: "Meeting",
    description: "Calendar notes",
    icon: CalendarClock,
  },
];

function sourceStatusLabel(status: IntakeSource["status"]): string {
  if (status === "processed") return "Processed";
  if (status === "pending") return "Pending";
  return "Not connected";
}

function sourceStatusClass(status: IntakeSource["status"]): string {
  if (status === "processed") return "border-success/30 bg-success/10 text-success";
  if (status === "pending") return "border-warning/30 bg-warning/10 text-warning";
  return "border-border bg-muted text-muted-foreground";
}

function evidenceClass(strength: "Low" | "Medium" | "High"): string {
  if (strength === "High") return "text-success";
  if (strength === "Medium") return "text-warning";
  return "text-muted-foreground";
}

function jobIcon(job: IngestionJob) {
  if (job.status === "completed") return <CheckCircle2 className="h-3.5 w-3.5 text-success" />;
  if (job.status === "processing") return <Loader2 className="h-3.5 w-3.5 animate-spin text-info" />;
  if (job.status === "failed") return <AlertCircle className="h-3.5 w-3.5 text-destructive" />;
  return <Cloud className="h-3.5 w-3.5 text-muted-foreground" />;
}

function createLocalSource(mode: SourceMode, detail?: string): IntakeSource {
  const action = SOURCE_ACTIONS.find(item => item.mode === mode);
  const isConnectedMode = mode === "notes" || mode === "url";
  return {
    id: `${mode}-${Date.now()}`,
    mode,
    label: action?.label ?? mode,
    detail,
    status: isConnectedMode ? "processed" : mode === "crm" ? "not_connected" : "pending",
  };
}

function createAskClientEmail(draft: ValueCaseDraft): string {
  const champion = draft.stakeholders[0]?.name || "there";
  const account = draft.companyName || "the account";
  const initiative = draft.knownInitiative || draft.valueLevers[0]?.toLowerCase() || "the value case";
  const missing = draft.missingMetrics.map((metric, index) => `${index + 1}. ${metric.label}`).join("\n");

  return `Hi ${champion},

To complete the ROI model for ${account}, we need two baseline inputs for ${initiative}:

${missing}

With those, we can estimate the savings range and prepare a stronger executive case before the target decision date.`;
}

export default function ValueNarrativeHome() {
  const [notes, setNotes] = React.useState("");
  const [sourceUrl, setSourceUrl] = React.useState("");
  const [activeMode, setActiveMode] = React.useState<SourceMode>("notes");
  const [webMode, setWebMode] = React.useState<WebMode>("url");
  const [sources, setSources] = React.useState<IntakeSource[]>([]);
  const [metricOverrides, setMetricOverrides] = React.useState<Record<string, string>>({});
  const [launchError, setLaunchError] = React.useState("");
  const [showClientEmail, setShowClientEmail] = React.useState(false);
  const { isAuthenticated, isLoading: authLoading } = useAuthContext();
  const canLoadRecentJobs = isAuthenticated && !authLoading;
  const { data: recentJobs = [], isLoading: jobsLoading } = useRecentIngestionJobs(4, {
    suppressAuthRedirect: true,
    enabled: canLoadRecentJobs,
  });
  const { navigateTo } = useNavigation();
  const prospectSetup = useProspectSetupAccountCreate();

  const draft = React.useMemo(
    () => parseValueCaseDraft({ notes, sourceUrl, sources, metricOverrides }),
    [metricOverrides, notes, sourceUrl, sources]
  );

  const processedSources = sources.filter(source => source.status === "processed").length;
  const sourceProgress = Math.min(100, (sources.length / SOURCE_LIMIT) * 100);
  const roiReady = draft.evidenceStrength === "High";
  const canLaunch = Boolean(draft.companyName.trim()) && !prospectSetup.isSubmitting;

  const addOrReplaceSource = React.useCallback((mode: SourceMode, detail?: string) => {
    setSources(current => {
      const next = createLocalSource(mode, detail);
      return [...current.filter(source => source.mode !== mode), next];
    });
  }, []);

  const addWebSource = React.useCallback((mode: WebMode, detail: string) => {
    const label = mode === "url" ? "Known URL" : "Web search";
    const status: IntakeSource["status"] = mode === "url" ? "processed" : "pending";
    setSources(current => [
      ...current.filter(source => source.id !== `web-${mode}`),
      {
        id: `web-${mode}`,
        mode: "url",
        label,
        detail,
        status,
      },
    ]);
  }, []);

  const handleNotesBlur = () => {
    if (notes.trim().length > 0) {
      addOrReplaceSource("notes", `Extracted ${notes.trim().split(/\s+/).length} words`);
    }
  };

  const handleWebSubmit = () => {
    const value = sourceUrl.trim();
    if (value) {
      addWebSource(webMode, value);
      setLaunchError("");
    }
  };

  const handleUnavailableSource = (mode: SourceMode) => {
    addOrReplaceSource(mode, mode === "crm" ? "Connector not configured" : "Queued for connector setup");
  };

  const handleMetricChange = (metricId: string, value: string) => {
    setMetricOverrides(current => ({ ...current, [metricId]: value }));
  };

  const handleLaunch = async () => {
    if (!draft.companyName.trim()) {
      setLaunchError("Add an account name or source context before launching.");
      return;
    }

    setLaunchError("");
    const result = await prospectSetup.createSetup(buildProspectPayloadFromDraft(draft));
    if (result?.accountId) {
      navigateTo("intelligence-overview", { accountId: result.accountId });
    }
  };

  return (
    <PageShell fullWidth>
      <div className="mx-auto flex w-full max-w-screen-2xl flex-col gap-4 px-2 pb-8 sm:px-4 lg:px-6">
        <div className="flex flex-col gap-3 border-b border-border pb-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              Fabric Value Case Intake Cockpit
            </h1>
            <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
              Ingest source material, extract the first structured value case, score evidence strength, and launch the workspace.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={handleLaunch} disabled={!canLaunch}>
              {prospectSetup.isSubmitting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <ArrowRight className="mr-2 h-4 w-4" />
              )}
              Launch Case
            </Button>
          </div>
        </div>

        {launchError && (
          <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <AlertCircle className="h-4 w-4" />
            {launchError}
          </div>
        )}

        <div className="grid gap-4 xl:grid-cols-12">
          <section className="flex min-w-0 flex-col gap-4 xl:col-span-6">
            <Card className="h-full overflow-hidden">
              <CardHeader className="border-b border-border pb-3">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <CardTitle className="flex items-center gap-2 text-sm uppercase tracking-wide">
                      <span className="h-2.5 w-2.5 rounded-full bg-primary" />
                      Source Ingestion Layer
                    </CardTitle>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Messy fragments to evidence structure.
                    </p>
                  </div>
                  <Badge variant="outline">{sources.length} / {SOURCE_LIMIT} sources</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 p-4">
                <div className="grid grid-cols-3 gap-1 rounded-lg border border-border bg-muted/30 p-1 sm:grid-cols-6">
                  {SOURCE_ACTIONS.map(action => {
                    const Icon = action.icon;
                    const source = sources.find(item => item.mode === action.mode);
                    const isActive = activeMode === action.mode;
                    return (
                      <button
                        key={action.mode}
                        type="button"
                        onClick={() => {
                          setActiveMode(action.mode);
                          if (action.mode !== "notes" && action.mode !== "url" && !source) {
                            handleUnavailableSource(action.mode);
                          }
                        }}
                        className={`rounded-md border px-2 py-2 text-center transition-colors ${
                          isActive ? "border-border bg-background text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        <Icon className={`mx-auto h-4 w-4 ${isActive ? "text-primary" : ""}`} />
                        <span className="mt-1 block text-[10px] font-semibold uppercase tracking-wide">{action.label}</span>
                      </button>
                    );
                  })}
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Source limit</span>
                    <span>{sources.length} / {SOURCE_LIMIT}</span>
                  </div>
                  <Progress value={sourceProgress} aria-label="Source intake progress" />
                </div>

                <div className="rounded-lg border border-border bg-muted/20 p-3">
                  {activeMode === "notes" && (
                    <div className="space-y-3">
                      <p className="text-xs text-muted-foreground">
                        Paste transcript, discovery briefs, or describe the business case directly below.
                      </p>
                      <div className="relative">
                        <Textarea
                          id="source-notes"
                          aria-label="Copied discovery text"
                          value={notes}
                          onChange={event => setNotes(event.target.value)}
                          onBlur={handleNotesBlur}
                          placeholder="Paste unstructured meeting fragments here..."
                          className="min-h-[290px] resize-none font-mono text-xs leading-6"
                        />
                        <div className="absolute bottom-3 right-3 rounded border border-border bg-background px-2 py-0.5 text-[10px] text-muted-foreground">
                          Word Count: {notes.trim().split(/\s+/).filter(Boolean).length}
                        </div>
                      </div>
                    </div>
                  )}

                  {activeMode === "url" && (
                    <div className="space-y-4">
                      <div className="flex rounded-md border border-border bg-background p-1">
                        <button
                          type="button"
                          onClick={() => setWebMode("url")}
                          className={`flex-1 rounded px-3 py-2 text-xs font-medium ${webMode === "url" ? "bg-muted text-foreground" : "text-muted-foreground"}`}
                        >
                          Add known URL
                        </button>
                        <button
                          type="button"
                          onClick={() => setWebMode("search")}
                          className={`flex-1 rounded px-3 py-2 text-xs font-medium ${webMode === "search" ? "bg-muted text-foreground" : "text-muted-foreground"}`}
                        >
                          Search Web
                        </button>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="source-url">
                          {webMode === "url" ? "Known website or source URL" : "Agentic discovery query"}
                        </Label>
                        <div className="flex gap-2">
                          <Input
                            id="source-url"
                            aria-label="URL or research query"
                            value={sourceUrl}
                            onChange={event => setSourceUrl(event.target.value)}
                            placeholder={webMode === "url" ? "https://acme.com/pricing" : "Acme support automation benchmarks"}
                            className="font-mono text-xs"
                          />
                          <Button type="button" variant="secondary" onClick={handleWebSubmit} aria-label="Add URL or search">
                            <Search className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                      <div className="rounded-md border border-border bg-background p-3 text-xs text-muted-foreground">
                        {webMode === "url"
                          ? "Known URLs are tracked as deterministic user-provided sources."
                          : "Web search is queued as discovered-source context for later enrichment."}
                      </div>
                    </div>
                  )}

                  {activeMode !== "notes" && activeMode !== "url" && (
                    <div className="space-y-3">
                      <div className="rounded-md border border-border bg-background p-3">
                        <p className="text-sm font-medium text-foreground">
                          {SOURCE_ACTIONS.find(action => action.mode === activeMode)?.label}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          Backend import is not connected in this pass. This control adds a local source record so the intake brief can show pending provenance.
                        </p>
                      </div>
                      <Button type="button" variant="secondary" size="sm" onClick={() => handleUnavailableSource(activeMode)}>
                        Add pending source record
                      </Button>
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-3">
                    <h2 className="text-xs font-semibold uppercase tracking-wide text-foreground">Sources added</h2>
                    <span className="text-xs text-muted-foreground">{processedSources} processed</span>
                  </div>
                  {sources.length === 0 ? (
                    <p className="rounded-lg border border-dashed border-border p-3 text-xs text-muted-foreground">
                      Add source context to start extraction and evidence scoring.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {sources.map(source => (
                        <div key={source.id} className="rounded-lg border border-border bg-background px-3 py-2">
                          <div className="flex items-center justify-between gap-3">
                            <div className="min-w-0">
                              <p className="truncate text-xs font-medium text-foreground">{source.label}</p>
                              {source.detail && <p className="mt-1 truncate text-xs text-muted-foreground">{source.detail}</p>}
                            </div>
                            <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium ${sourceStatusClass(source.status)}`}>
                              {sourceStatusLabel(source.status)}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </section>

          <section className="flex min-w-0 flex-col gap-4 xl:col-span-6">
            <Card className="overflow-hidden">
              <CardHeader className="border-b border-border pb-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <CardTitle className="flex items-center gap-2 text-sm uppercase tracking-wide">
                      <ShieldCheck className="h-4 w-4 text-primary" />
                      Fabric Found Summary
                    </CardTitle>
                    <p className="mt-1 text-xs text-muted-foreground">
                      What Layer 1 understood from the source material.
                    </p>
                  </div>
                  <span className={`text-xs font-semibold ${evidenceClass(draft.evidenceStrength)}`}>
                    {draft.evidenceStrength} Evidence Strength
                  </span>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 p-4">
                <div className="grid gap-3 md:grid-cols-[120px_1fr]">
                  <div className="rounded-lg border border-border bg-muted/20 p-3 text-center">
                    <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Score</p>
                    <p className={`mt-1 text-2xl font-semibold ${evidenceClass(draft.evidenceStrength)}`}>{draft.evidenceScore}%</p>
                    <p className="text-[11px] text-muted-foreground">{draft.evidenceStrength}</p>
                  </div>
                  <div className="rounded-lg border border-border bg-muted/20 p-3">
                    <div className="mb-2 flex items-center justify-between text-xs">
                      <span className="flex items-center gap-2 font-medium text-foreground">
                        <Gauge className="h-4 w-4 text-primary" />
                        Evidence readiness
                      </span>
                      <span className="font-medium text-muted-foreground">{roiReady ? "Baseline ready" : "Needs quantified inputs"}</span>
                    </div>
                    <Progress value={draft.evidenceScore} aria-label="Evidence readiness score" />
                    <p className="mt-2 text-xs text-muted-foreground">
                      Qualitative source extraction is available immediately. CFO-grade ROI requires baseline metrics.
                    </p>
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-lg border border-border bg-background p-3">
                    <span className="block text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Firmographics</span>
                    <div className="mt-2 space-y-2 text-xs">
                      <div className="flex items-center justify-between gap-3 border-b border-border pb-1">
                        <span className="text-muted-foreground">Account</span>
                        <span className="truncate font-semibold text-foreground">{draft.companyName || "Not detected"}</span>
                      </div>
                      <div className="flex items-center justify-between gap-3 border-b border-border pb-1">
                        <span className="text-muted-foreground">Opportunity</span>
                        <span className="truncate font-medium text-foreground">{draft.knownInitiative || "Value case intake"}</span>
                      </div>
                      <div className="flex items-center justify-between gap-3 border-b border-border pb-1">
                        <span className="text-muted-foreground">Deal Size</span>
                        <span className="truncate font-mono font-semibold text-foreground">{draft.dealSize || "Unknown"}</span>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-muted-foreground">Target Close</span>
                        <span className="truncate font-medium text-foreground">{draft.targetTiming || "Unknown"}</span>
                      </div>
                    </div>
                  </div>
                  <section className="rounded-lg border border-border bg-background p-3">
                    <span className="flex items-center gap-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                      <Users className="h-3.5 w-3.5" />
                      Identified Stakeholders
                    </span>
                    {draft.stakeholders.length === 0 ? (
                      <p className="mt-2 rounded-lg border border-dashed border-border p-3 text-xs text-muted-foreground">No stakeholders detected yet.</p>
                    ) : (
                      <div className="mt-2 space-y-2">
                        {draft.stakeholders.map(stakeholder => (
                          <div key={`${stakeholder.name}-${stakeholder.role}`} className="rounded-md border border-border bg-muted/30 px-2 py-1.5 text-xs">
                            <span className="font-semibold text-foreground">{stakeholder.name}</span>
                            <span className="text-muted-foreground"> - {stakeholder.role}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </section>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <section className="rounded-lg border border-border bg-background p-3">
                    <span className="block text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Detected Pain Points</span>
                    {draft.businessPain.length === 0 ? (
                      <p className="mt-2 rounded-lg border border-dashed border-border p-3 text-xs text-muted-foreground">
                        Add pain, risk, or friction statements to strengthen the draft.
                      </p>
                    ) : (
                      <ul className="mt-2 space-y-2">
                        {draft.businessPain.slice(0, 4).map(item => (
                          <li key={item} className="rounded-md border border-border bg-muted/20 px-2 py-1.5 text-xs text-foreground">
                            {item}
                          </li>
                        ))}
                      </ul>
                    )}
                  </section>
                  <section className="rounded-lg border border-border bg-background p-3">
                    <span className="block text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Mapped Value Levers</span>
                    <div className="mt-2 space-y-2">
                      {draft.valueLevers.map(lever => (
                        <div key={lever} className="rounded-md border border-border bg-muted/20 px-2 py-1.5 text-xs font-medium text-foreground">
                          {lever}
                        </div>
                      ))}
                    </div>
                  </section>
                </div>

                <div className="rounded-lg border border-border bg-muted/20 p-3">
                  <div className="flex items-start justify-between gap-3 border-b border-border pb-2">
                    <div>
                      <h2 className="text-xs font-semibold uppercase tracking-wide text-foreground">Actionable Missing Inputs</h2>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Override with direct parameters before CFO-facing ROI.
                      </p>
                    </div>
                    <Badge variant={roiReady ? "success" : "warning"}>{roiReady ? "Complete" : "Action needed"}</Badge>
                  </div>
                  <div className="mt-3 space-y-3">
                    {draft.missingMetrics.map(metric => (
                      <div key={metric.id} className="rounded-md border border-border bg-background p-2">
                        <div className="mb-2 flex items-center justify-between gap-3 text-xs">
                          <Label htmlFor={`metric-${metric.id}`} className="text-xs">{metric.label}</Label>
                          <span className="text-[10px] text-muted-foreground">{metric.unit}</span>
                        </div>
                        <div className="flex gap-2">
                          <Input
                            id={`metric-${metric.id}`}
                            aria-label={metric.label}
                            value={metricOverrides[metric.id] ?? ""}
                            onChange={event => handleMetricChange(metric.id, event.target.value)}
                            placeholder="Override baseline"
                            className="h-8 text-xs"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <Button type="button" variant="outline" size="sm">
                      Override with CRM Value
                    </Button>
                    <Button type="button" variant="outline" size="sm" onClick={() => setShowClientEmail(current => !current)}>
                      <Mail className="mr-2 h-4 w-4" />
                      Draft Ask-Client Email
                    </Button>
                  </div>
                  {showClientEmail && (
                    <div className="mt-3 rounded-lg border border-border bg-background p-3">
                      <p className="mb-2 text-xs font-semibold text-foreground">Generated email draft</p>
                      <pre className="whitespace-pre-wrap font-sans text-xs leading-5 text-muted-foreground">
                        {createAskClientEmail(draft)}
                      </pre>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </section>
        </div>

        <Card className="border-primary/20 bg-primary/5">
          <CardContent className="flex flex-col gap-4 p-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm font-semibold text-foreground">Launch Action Area</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Launch creates the account workspace now and carries missing ROI inputs forward as follow-up requirements.
              </p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button type="button" variant="outline" onClick={() => setShowClientEmail(true)}>
                Request CFO Pre-read
              </Button>
              <Button type="button" onClick={handleLaunch} disabled={!canLaunch}>
                {prospectSetup.isSubmitting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <ArrowRight className="mr-2 h-4 w-4" />
                )}
                Launch Case
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-base">Recent ingestion activity</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {recentJobs.length === 0 && !jobsLoading ? (
              <p className="text-sm text-muted-foreground">No recent ingestion jobs.</p>
            ) : (
              recentJobs.map(job => (
                <div key={job.id} className="flex items-start gap-3 rounded-lg border border-border p-3">
                  <span className="mt-0.5">{jobIcon(job)}</span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">{job.domain}</p>
                    <p className="text-xs text-muted-foreground">
                      {job.status} - {job.progress}%
                    </p>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </PageShell>
  );
}
