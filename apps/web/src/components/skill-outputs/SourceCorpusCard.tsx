/**
 * SourceCorpusCard — Compact summary card for a SourceCorpus record.
 *
 * UI Contract (Data):
 *   - `corpus` : SourceCorpusSummary from the list endpoint
 *   - `onSelect` : optional callback when the card is clicked
 *   - `selected` : highlights the card when true
 *
 * UI Contract (Rendering):
 *   - Shows company name, corpus type, source count, extraction status, and date
 *   - Uses StatusBadgeBlock for extraction_status
 *   - Follows SectionCard border/rounded conventions
 *   - No provenance arrays — summary only
 */
import { Building2, FileStack } from 'lucide-react';
import { cn } from '@/lib/utils';
import { StatusBadgeBlock, type BlockStatus as Status } from '@/components/ui/fabric/StatusBadge';
import type { SourceCorpusSummary } from '@/hooks/useSkillJobs';

function extractionStatusToStatus(s: string): Status {
  switch (s) {
    case 'ready_for_extraction': return 'queued';
    case 'sent_to_layer_2':      return 'running';
    case 'extraction_complete':  return 'completed';
    case 'extraction_failed':    return 'failed';
    default:                     return 'paused';
  }
}

function extractionStatusLabel(s: string): string {
  switch (s) {
    case 'ready_for_extraction': return 'Ready';
    case 'sent_to_layer_2':      return 'Extracting';
    case 'extraction_complete':  return 'Complete';
    case 'extraction_failed':    return 'Failed';
    default:                     return s;
  }
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export interface SourceCorpusCardProps {
  corpus: SourceCorpusSummary;
  onSelect?: (id: string) => void;
  selected?: boolean;
  className?: string;
}

export function SourceCorpusCard({
  corpus,
  onSelect,
  selected = false,
  className,
}: SourceCorpusCardProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect?.(corpus.id)}
      className={cn(
        'w-full text-left rounded-xl border bg-card px-4 py-3 transition-colors',
        'hover:border-primary/40 hover:bg-accent/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        selected && 'border-primary bg-primary/5',
        !selected && 'border-border',
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <Building2 className="w-4 h-4 shrink-0 text-muted-foreground" />
          <div className="min-w-0">
            <p className="text-sm font-semibold text-foreground truncate">{corpus.company_name}</p>
            {corpus.company_id && (
              <p className="text-xs text-muted-foreground truncate">{corpus.company_id}</p>
            )}
          </div>
        </div>
        <StatusBadgeBlock
          status={extractionStatusToStatus(corpus.extraction_status)}
          label={extractionStatusLabel(corpus.extraction_status)}
          size="sm"
        />
      </div>

      <div className="mt-2 flex items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <FileStack className="w-3 h-3" />
          {corpus.source_count} sources
        </span>
        <span className="capitalize">{corpus.corpus_type.replace(/_/g, ' ')}</span>
        <span className="ml-auto">{formatDate(corpus.created_at)}</span>
      </div>
    </button>
  );
}
