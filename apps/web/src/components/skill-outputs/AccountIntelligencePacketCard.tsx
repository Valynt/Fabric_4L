/**
 * AccountIntelligencePacketCard — Compact summary card for an AccountIntelligencePacket.
 *
 * UI Contract (Data):
 *   - `packet` : AccountIntelligencePacketSummary from the list endpoint
 *   - `onSelect` : optional callback when the card is clicked
 *   - `selected` : highlights the card when true
 *
 * UI Contract (Rendering):
 *   - Shows account name, signal count, high-confidence signal count, and date
 *   - No source_references arrays — summary only
 *   - Follows SectionCard border/rounded conventions
 */
import { Building2, Signal } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AccountIntelligencePacketSummary } from '@/hooks/useSkillJobs';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function confidenceLabel(high: number, total: number): string {
  if (total === 0) return 'No signals';
  const ratio = high / total;
  if (ratio >= 0.7) return 'High confidence';
  if (ratio >= 0.4) return 'Medium confidence';
  return 'Low confidence';
}

function confidenceClasses(high: number, total: number): string {
  if (total === 0) return 'text-muted-foreground';
  const ratio = high / total;
  if (ratio >= 0.7) return 'text-success';
  if (ratio >= 0.4) return 'text-warning';
  return 'text-muted-foreground';
}

export interface AccountIntelligencePacketCardProps {
  packet: AccountIntelligencePacketSummary;
  onSelect?: (id: string) => void;
  selected?: boolean;
  className?: string;
}

export function AccountIntelligencePacketCard({
  packet,
  onSelect,
  selected = false,
  className,
}: AccountIntelligencePacketCardProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect?.(packet.id)}
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
            <p className="text-sm font-semibold text-foreground truncate">{packet.account_name}</p>
            {packet.account_id && (
              <p className="text-xs text-muted-foreground truncate">{packet.account_id}</p>
            )}
          </div>
        </div>
        <span
          className={cn(
            'text-xs font-medium shrink-0',
            confidenceClasses(packet.high_confidence_signal_count, packet.observed_signal_count),
          )}
        >
          {confidenceLabel(packet.high_confidence_signal_count, packet.observed_signal_count)}
        </span>
      </div>

      <div className="mt-2 flex items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <Signal className="w-3 h-3" />
          {packet.observed_signal_count} signal{packet.observed_signal_count !== 1 ? 's' : ''}
        </span>
        <span>{packet.high_confidence_signal_count} high confidence</span>
        <span className="ml-auto">{formatDate(packet.created_at)}</span>
      </div>
    </button>
  );
}
