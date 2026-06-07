/**
 * SearchResultItem Component
 *
 * Individual search result display with icon, title, subtitle, and excerpt.
 */

import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import { getSearchResultTypeIcon, getSearchResultTypeLabel } from "@/api/search";
import type { SearchResult } from "./types";
import {
  Building2,
  Activity,
  FileText,
  Users,
  TrendingUp,
  Briefcase,
  Calculator,
  BarChart3,
  Package,
  Network,
  MessageSquare,
  Play,
  FileCheck,
  Search,
} from "lucide-react";

interface SearchResultItemProps {
  result: SearchResult;
  tenantSlug: string;
  onSelect?: () => void;
}

const IconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  Building2,
  Activity,
  FileText,
  Users,
  TrendingUp,
  Briefcase,
  Calculator,
  BarChart3,
  Package,
  Network,
  MessageSquare,
  Play,
  FileCheck,
  Search,
};

export function SearchResultItem({ result, tenantSlug, onSelect }: SearchResultItemProps) {
  const iconName = getSearchResultTypeIcon(result.type);
  const Icon = IconMap[iconName] || Search;
  const typeLabel = getSearchResultTypeLabel(result.type);

  return (
    <Link
      to={result.url}
      onClick={onSelect}
      className="block w-full"
      data-testid="search-result"
    >
      <div className="flex items-start gap-3 px-2 py-2 rounded-md hover:bg-accent hover:text-accent-foreground cursor-pointer transition-colors">
        {/* Icon */}
        <div className="flex-shrink-0 mt-0.5">
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium truncate">{result.title}</span>
            {result.source_layer && (
              <span className="vf-text-micro px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                {result.source_layer.toUpperCase()}
              </span>
            )}
          </div>

          {/* Subtitle */}
          {result.subtitle && (
            <p className="text-xs text-muted-foreground truncate mt-0.5">
              {result.subtitle}
            </p>
          )}

          {/* Excerpt */}
          {result.excerpt && (
            <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5">
              {result.excerpt}
            </p>
          )}

          {/* Type label */}
          <div className="flex items-center gap-2 mt-1">
            <span className="vf-text-micro text-muted-foreground uppercase tracking-wide">
              {typeLabel}
            </span>
            {result.score !== undefined && (
              <span className="vf-text-micro text-muted-foreground">
                {Math.round(result.score * 100)}% match
              </span>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
