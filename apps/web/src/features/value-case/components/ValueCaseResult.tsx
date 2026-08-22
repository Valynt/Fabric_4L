import { memo } from "react";
import { CheckCircle2, FileText, Loader2, Send, Users, AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SectionCard } from "@/components/blocks/SectionCard";
import type { ValueCaseResultViewModel } from "../presentation/valueCaseViewModels";

export interface ValueCaseResultProps {
  result: ValueCaseResultViewModel;
  onPublish?: (versionId: string) => void;
  isPublishing?: boolean;
}

export const ValueCaseResult = memo(function ValueCaseResult({
  result,
  onPublish,
  isPublishing = false,
}: ValueCaseResultProps) {
  return (
    <div className="space-y-6" role="article" aria-label={`Value Case Version ${result.version}`}>
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-lg border border-border bg-card">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-foreground">
              {result.narrativeTitle}
            </h3>
            <Badge variant={result.statusBadgeVariant} data-testid="artifact-status-badge">
              {result.statusBadgeLabel}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Version {result.version} • Created {result.createdAtFormatted}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {!result.isPublished && onPublish && (
            <Button
              variant="default"
              size="sm"
              onClick={() => onPublish(result.id)}
              disabled={isPublishing}
              aria-busy={isPublishing}
            >
              {isPublishing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Publishing…
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" />
                  Publish Artifact
                </>
              )}
            </Button>
          )}
          {result.isPublished && (
            <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2.5 py-1 rounded-md border border-emerald-200 dark:border-emerald-800">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Published Artifact
            </div>
          )}
        </div>
      </div>

      {/* Executive Summary */}
      <SectionCard title="Executive Summary">
        <p className="text-sm text-muted-foreground leading-relaxed">
          {result.businessCaseSummary}
        </p>
      </SectionCard>

      {/* Narrative Sections */}
      {result.narrativeSections.length > 0 && (
        <SectionCard title="Value Narrative" subtitle="Strategic value pillars and justification">
          <div className="space-y-4">
            {result.narrativeSections.map((section, idx) => (
              <div key={idx} className="space-y-1.5 border-b border-border/50 pb-3 last:border-b-0 last:pb-0">
                <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
                  <FileText className="h-4 w-4 text-primary" />
                  {section.heading}
                </h4>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed pl-6">
                  {section.content}
                </p>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Stakeholder Framing */}
      {result.stakeholderFraming.length > 0 && (
        <SectionCard
          title="Stakeholder Framing"
          subtitle="Targeted value propositions tailored by organizational persona"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {result.stakeholderFraming.map((stakeholder, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-border p-4 bg-background/50 space-y-2.5"
              >
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-primary" />
                  <h5 className="text-sm font-medium text-foreground">
                    {stakeholder.role}
                  </h5>
                </div>
                {stakeholder.priorities.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {stakeholder.priorities.map((p, pIdx) => (
                      <Badge key={pIdx} variant="outline" className="text-xs">
                        {p}
                      </Badge>
                    ))}
                  </div>
                )}
                <p className="text-xs text-muted-foreground leading-normal">
                  {stakeholder.valueMessage}
                </p>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Risk Notes & Mitigation */}
      {result.risks.length > 0 && (
        <SectionCard title="Risk Analysis & Mitigation">
          <ul className="space-y-2 text-sm text-muted-foreground">
            {result.risks.map((risk, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                <span>{risk}</span>
              </li>
            ))}
          </ul>
        </SectionCard>
      )}
    </div>
  );
});
