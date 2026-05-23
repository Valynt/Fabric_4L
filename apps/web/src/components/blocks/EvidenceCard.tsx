/**
 * EvidenceCard — Consistent card for displaying evidence with provenance
 *
 * UI Contract (Data):
 *   - `source` : Source attribution (document, URL, or system)
 *   - `claim` : The claim or evidence text
 *   - `confidence` : Confidence score (0-1)
 *   - `validated` : Whether the evidence has been validated
 *   - `timestamp` : When the evidence was extracted/created
 *   - `onClick` : Optional click handler for drill-down
 *
 * UI Contract (Rendering):
 *   - Compact card with source, claim, confidence, and validation status
 *   - Hover state when clickable
 *   - Truncated claim text (line-clamp-2)
 *   - Formatted timestamp
 *
 * Use Cases:
 *   - Evidence lists in intelligence workspace
 *   - Claim traceability in business cases
 *   - Provenance panels in right rail
 */
import { cn } from "@/lib/utils";
import { SectionCard } from "./SectionCard";
import { StatusBadge } from "@/components/ui/fabric/StatusBadge";
import { formatDate } from "@/lib/formatters";

export interface EvidenceCardProps {
  source: string;
  claim: string;
  confidence: number;
  validated: boolean;
  timestamp: string;
  onClick?: () => void;
  className?: string;
}

export function EvidenceCard({ 
  source, 
  claim, 
  confidence, 
  validated, 
  timestamp,
  onClick,
  className 
}: EvidenceCardProps) {
  const cardContent = (
    <SectionCard
      noPad
      className={cn(
        onClick && "hover:border-primary/50 transition-colors",
        className
      )}
    >
      <div className="p-3 space-y-2">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs text-muted-foreground truncate flex-1" title={source}>
            {source}
          </span>
          <div className="flex items-center gap-2 flex-shrink-0">
            <StatusBadge status={validated ? "completed" : "processing"} />
            <span className="text-xs text-muted-foreground font-medium">
              {Math.round(confidence * 100)}%
            </span>
          </div>
        </div>
        <p className="text-sm text-foreground line-clamp-2 leading-relaxed" title={claim}>
          {claim}
        </p>
        <div className="text-xs text-muted-foreground">
          {formatDate(timestamp)}
        </div>
      </div>
    </SectionCard>
  );

  if (onClick) {
    return (
      <button
        onClick={onClick}
        className="w-full text-left cursor-pointer"
        type="button"
      >
        {cardContent}
      </button>
    );
  }

  return cardContent;
}
