/**
 * SkillOutputPanel — Right-rail detail panel for a completed skill job's output.
 *
 * UI Contract (Data):
 *   - `jobId` : the job whose skill output to display
 *   - `onClose` : optional close callback
 *
 * UI Contract (Rendering):
 *   - Fetches the skill output envelope via useJobSkillOutput
 *   - Renders SourceCorpusDetail or AccountIntelligencePacketDetail based on output_contract
 *   - Shows loading, empty, and error states
 *   - Follows right-rail panel conventions (fixed width, scrollable content)
 *   - Does not render if jobId is null
 */
import { X, Building2, Signal, FileStack, Tag, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SectionCard } from '@/components/blocks/SectionCard';
import { useJobSkillOutput, type SourceCorpusDetail, type AccountIntelligencePacketDetail } from '@/hooks/useSkillJobs';

// =============================================================================
// Sub-panels
// =============================================================================

function SourceCorpusPanel({ data }: { data: SourceCorpusDetail }) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Company"
        icon={<Building2 className="w-4 h-4" />}
      >
        <div className="px-5 py-3 space-y-1">
          <p className="text-sm font-semibold text-foreground">{data.company_name}</p>
          {data.company_id && (
            <p className="text-xs text-muted-foreground">{data.company_id}</p>
          )}
          <p className="text-xs text-muted-foreground capitalize">
            {data.corpus_type.replace(/_/g, ' ')}
          </p>
        </div>
      </SectionCard>

      {data.source_groups.length > 0 && (
        <SectionCard
          title="Source groups"
          icon={<FileStack className="w-4 h-4" />}
        >
          <ul className="divide-y divide-border/50">
            {data.source_groups.map((g) => {
              const group = g as { source_type?: string; count?: number };
              return (
                <li key={String(group.source_type ?? Math.random())} className="px-5 py-2 flex items-center justify-between text-xs">
                  <span className="text-foreground capitalize">{String(group.source_type ?? '').replace(/_/g, ' ')}</span>
                  <span className="text-muted-foreground">{group.count ?? 0} sources</span>
                </li>
              );
            })}
          </ul>
        </SectionCard>
      )}

      {data.candidate_concepts.length > 0 && (
        <SectionCard
          title="Candidate concepts"
          icon={<Tag className="w-4 h-4" />}
        >
          <div className="px-5 py-3 flex flex-wrap gap-1.5">
            {data.candidate_concepts.map((c) => (
              <span
                key={c}
                className="inline-flex items-center rounded-full bg-primary/10 text-primary text-xs px-2.5 py-0.5 font-medium"
              >
                {c}
              </span>
            ))}
          </div>
        </SectionCard>
      )}

      <div className="px-1 text-xs text-muted-foreground">
        Status: <span className="font-medium text-foreground capitalize">{data.extraction_status.replace(/_/g, ' ')}</span>
      </div>
    </div>
  );
}

function AccountIntelligencePacketPanel({ data }: { data: AccountIntelligencePacketDetail }) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Account"
        icon={<Building2 className="w-4 h-4" />}
      >
        <div className="px-5 py-3 space-y-1">
          <p className="text-sm font-semibold text-foreground">{data.account_name}</p>
          {data.account_id && (
            <p className="text-xs text-muted-foreground">{data.account_id}</p>
          )}
        </div>
      </SectionCard>

      {data.observed_signals.length > 0 && (
        <SectionCard
          title={`Signals (${data.observed_signals.length})`}
          icon={<Signal className="w-4 h-4" />}
        >
          <ul className="divide-y divide-border/50">
            {data.observed_signals.map((s) => {
              const sig = s as { signal?: unknown; description?: unknown; source?: unknown };
              return (
                <li key={String(sig.signal ?? sig.description ?? Math.random())} className="px-5 py-2 text-xs">
                  <p className="text-foreground">{String(sig.signal ?? sig.description ?? 'Signal')}</p>
                  {Boolean(sig.source) && (
                    <p className="text-muted-foreground mt-0.5 capitalize">{String(sig.source).replace(/_/g, ' ')}</p>
                  )}
                </li>
              );
            })}
          </ul>
        </SectionCard>
      )}

      {data.likely_pain_areas.length > 0 && (
        <SectionCard title="Likely pain areas">
          <ul className="px-5 py-3 space-y-1">
            {data.likely_pain_areas.map((p) => (
              <li key={p} className="text-xs text-foreground flex items-start gap-1.5">
                <span className="mt-1 w-1.5 h-1.5 rounded-full bg-warning/100 shrink-0" />
                {p}
              </li>
            ))}
          </ul>
        </SectionCard>
      )}

      {data.likely_stakeholders.length > 0 && (
        <SectionCard title="Likely stakeholders">
          <div className="px-5 py-3 flex flex-wrap gap-1.5">
            {data.likely_stakeholders.map((s) => (
              <span
                key={s}
                className="inline-flex items-center rounded-full bg-muted text-muted-foreground text-xs px-2.5 py-0.5"
              >
                {s}
              </span>
            ))}
          </div>
        </SectionCard>
      )}
    </div>
  );
}

// =============================================================================
// Main panel
// =============================================================================

export interface SkillOutputPanelProps {
  jobId: string | null;
  onClose?: () => void;
  className?: string;
}

export function SkillOutputPanel({ jobId, onClose, className }: SkillOutputPanelProps) {
  const { data, isLoading, isError, error } = useJobSkillOutput(jobId);

  if (!jobId) return null;

  return (
    <aside
      className={cn(
        'flex flex-col w-80 shrink-0 border-l border-border bg-background overflow-hidden',
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <h2 className="text-sm font-semibold text-foreground">
          {data?.output_contract === 'SourceCorpus'
            ? 'Source Corpus'
            : data?.output_contract === 'AccountIntelligencePacket'
            ? 'Account Intelligence'
            : 'Skill Output'}
        </h2>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Close panel"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {isLoading && (
          <div className="flex items-center justify-center h-24 text-xs text-muted-foreground">
            Loading output…
          </div>
        )}

        {isError && (
          <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
            <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
            <span>{error?.message ?? 'Failed to load skill output'}</span>
          </div>
        )}

        {!isLoading && !isError && !data && (
          <div className="flex items-center justify-center h-24 text-xs text-muted-foreground">
            No output available yet
          </div>
        )}

        {data?.output_contract === 'SourceCorpus' && (
          <SourceCorpusPanel data={data.data as SourceCorpusDetail} />
        )}

        {data?.output_contract === 'AccountIntelligencePacket' && (
          <AccountIntelligencePacketPanel data={data.data as AccountIntelligencePacketDetail} />
        )}
      </div>
    </aside>
  );
}
