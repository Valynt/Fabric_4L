/**
 * Action Plan Tab — Enhanced with DIL hooks
 *
 * Primary data: synthesized from validated hypotheses + product portfolio
 * DIL enrichment: value hypotheses + product capabilities for recommendation generation
 */
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { ChevronDown, ChevronUp, Lightbulb, Package, Sparkles, ArrowRight } from "lucide-react";
import ValueStudioShellComponent from "@/components/workspace/ValueStudioShell";
import RightRail, { type RightRailMode } from "@/components/workspace/RightRail";
import { useAgentEvents } from "@/agui";
import { useAccount } from "@/hooks/useAccounts";
import { useNavigation } from "@/hooks";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { CenteredLoader } from "@/components/CenteredLoader";
import { ErrorState } from "@/components/states/ErrorState";
import { cn } from "@/lib/utils";

// DIL hooks
import { useAccountHypotheses, type ValueHypothesis } from "@/hooks/useHypotheses";
import { useProducts, type Product, type ProductListResponse, type ProductCapability } from "@/hooks/useProducts";
import { SectionCard } from "@/components/blocks/SectionCard";
import { MetricCard, Btn } from "@/components/ui/fabric";

// ── Types ──────────────────────────────────────────────────────────────────────
interface Recommendation {
  id: string;
  title: string;
  priority: "critical" | "high" | "medium";
  projectedValue: string;
  confidence: "high" | "medium" | "low";
  horizon: string;
  prospectPain: string;
  rootDriver: string;
  ourCapability: string;
  grounding_type?: "evidence_backed" | "assumption" | "inference" | "fact";
}

const PRIORITY_COLORS: Record<string, string> = {
  critical: "bg-destructive/10 text-destructive",
  high: "bg-warning/10 text-warning",
  medium: "bg-primary/10 text-primary",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-muted text-muted-foreground",
  validated: "bg-success/10 text-success",
  rejected: "bg-destructive/10 text-destructive",
  converted: "bg-primary/10 text-primary",
};

// Grounding label styles for assumption vs fact distinction
const GROUNDING_LABELS: Record<string, { class: string; text: string }> = {
  evidence_backed: { class: "bg-success/10 text-success border border-success/20", text: "Evidence-backed" },
  assumption: { class: "bg-warning/10 text-warning border border-warning/20", text: "Assumption" },
  inference: { class: "bg-primary/10 text-primary border border-primary/20", text: "Inference" },
  fact: { class: "bg-success/10 text-success border border-success/20", text: "Fact" },
};

// ── Recommendation Synthesis ───────────────────────────────────────────────────

function synthesizeRecommendations(
  hypotheses: ValueHypothesis[],
  products: Product[]
): Recommendation[] {
  return hypotheses.map((h) => {
    const impact = h.estimated_impact_usd ?? 0;
    const confidenceScore = h.confidence_score ?? h.confidence ?? 0.5;

    // Priority: revenue uplift + high confidence = critical
    let priority: Recommendation["priority"] = "medium";
    if (h.value_path_category === "revenue_uplift" && confidenceScore >= 0.75) {
      priority = "critical";
    } else if (confidenceScore >= 0.7 || h.value_path_category === "revenue_uplift") {
      priority = "high";
    }

    // Confidence label
    let confidence: Recommendation["confidence"] = "low";
    if (confidenceScore >= 0.8) confidence = "high";
    else if (confidenceScore >= 0.5) confidence = "medium";

    // Find a matching product by capability or fallback to first product
    const matchingProduct = products.find((p) =>
      p.capabilities?.some(
        (c: ProductCapability) =>
          (c.name as string | undefined)?.toLowerCase() ===
          (h.capability_name ?? "").toLowerCase()
      )
    );
    const productName = matchingProduct?.name ?? products[0]?.name ?? "Our Solution";

    return {
      id: h.id,
      title: h.hypothesis_text,
      priority,
      projectedValue: impact >= 1000 ? `$${(impact / 1000).toFixed(1)}K` : `$${impact.toLocaleString()}`,
      confidence,
      horizon: h.value_path_category === "cost_savings" ? "0–6 months" : "6–12 months",
      prospectPain: h.signal_name ?? "Identified pain signal",
      rootDriver: h.capability_name ?? "Value driver",
      ourCapability: productName,
      grounding_type: h.status === "validated" ? "evidence_backed" : "assumption",
    };
  });
}

// ── Hypothesis Card ────────────────────────────────────────────────────────────
function HypothesisCard({ h }: { h: ValueHypothesis }) {
  return (
    <div className="px-3 py-2.5 border border-border rounded-md">
      <div className="flex items-start gap-2">
        <Lightbulb size={13} className="text-warning mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="vf-text-body-s font-medium leading-snug truncate">
            {h.hypothesis_text}
          </p>
          <div className="flex items-center gap-2 mt-1.5">
            <span className={cn("vf-text-micro px-1.5 py-0.5 rounded font-semibold", STATUS_COLORS[h.status] ?? "bg-muted text-muted-foreground")}>
              {h.status}
            </span>
            <span className="vf-text-micro text-muted-foreground">
              {Math.round((h.confidence_score ?? h.confidence ?? 0.5) * 100)}% confidence
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Product Badge ──────────────────────────────────────────────────────────────
function ProductBadge({ p }: { p: Product }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 border border-border rounded-md">
      <Package size={13} className="text-primary shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="vf-text-body-s font-medium truncate">{p.name}</p>
        <p className="vf-text-micro text-muted-foreground truncate">{p.category}</p>
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────
export default function ActionPlanTab() {
  const { accountId } = useParams<{ accountId: string }>();
  const { data: account, isLoading: accountLoading } = useAccount(accountId ?? null);
  const { navigateTo } = useNavigation();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [railMode, setRailMode] = useState<RightRailMode>("agent");
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);

  // DIL data
  const { data: hypothesesData, isLoading: hypothesesLoading } = useAccountHypotheses(
    accountId ?? null,
    { status: "validated" }
  );
  const { data: productsData } = useProducts();

  const hypotheses = hypothesesData?.hypotheses ?? [];
  const products = productsData?.products ?? [];

  const hasGenerated = recommendations.length > 0;

  const handleGenerate = () => {
    const generated = synthesizeRecommendations(hypotheses, products);
    setRecommendations(generated);
  };

  const totalValue = useMemo(
    () =>
      recommendations.reduce(
        (sum, rec) => sum + Number((rec.projectedValue || "").replace(/[^\d.]/g, "")),
        0
      ),
    [recommendations]
  );

  const { messages, sendMessage, suggestedActions, steps, isStreaming, metadata } = useAgentEvents({
    activeTab: "action-plan",
    accountName: account?.name ?? "Account",
    accountId: accountId ?? undefined,
  });

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }

  if (accountLoading || hypothesesLoading) {
    return <CenteredLoader message="Loading action plan…" />;
  }

  if (!account) {
    return <ErrorState title="Account not found" description="Select a valid account to continue in this workspace." fullPage />;
  }

  return (
    <ValueStudioShellComponent
      account={{
        accountName: account?.name ?? "Account",
        industry: account?.industry ?? "Unknown",
        revenue: account?.annual_revenue ? `$${account.annual_revenue.toLocaleString()}` : "N/A",
      }}
      rightRail={
        <RightRail
          mode={railMode}
          onModeChange={setRailMode}
          activeTab="action-plan"
          messages={messages}
          onSendMessage={sendMessage}
          suggestedActions={suggestedActions}
          steps={steps}
          isStreaming={isStreaming}
          runMetadata={metadata}
        />
      }
    >
      {/* Metrics row */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <MetricCard label="Recommendations" value={String(recommendations.length)} />
        <MetricCard label="Total Projected Value" value={`$${totalValue.toLocaleString()}`} />
        <MetricCard
          label="Avg Confidence"
          value={`${Math.round(
            (recommendations.filter((r) => r.confidence === "high").length /
              Math.max(recommendations.length, 1)) *
              100
          )}% high`}
        />
        <MetricCard
          label="Validated Hypotheses"
          value={String(hypotheses.length)}
          trend={hypotheses.length > 0 ? "From DIL engine" : undefined}
        />
      </div>

      {/* DIL Hypotheses Section */}
      {hypotheses.length > 0 && (
        <SectionCard title="Value Hypotheses" className="mb-4">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles size={13} className="text-warning" />
            <span className="vf-text-caption text-muted-foreground">
              Generated by the Value Hypothesis Engine — validated signals mapped to product capabilities
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {hypotheses.slice(0, 6).map((h) => (
              <HypothesisCard key={h.id} h={h} />
            ))}
          </div>
          {hypotheses.length > 6 && (
            <p className="vf-text-micro text-muted-foreground mt-2">
              +{hypotheses.length - 6} more hypotheses
            </p>
          )}
          {!hasGenerated && (
            <div className="mt-4">
              <Btn variant="primary" onClick={handleGenerate}>
                <Sparkles size={12} /> Generate Recommendations from Hypotheses
              </Btn>
            </div>
          )}
        </SectionCard>
      )}

      {/* Recommendations */}
      {recommendations.length === 0 ? (
        <SectionCard title="Recommendations">
          <div className="text-sm text-muted-foreground">
            {hypotheses.length === 0
              ? "No validated hypotheses available. Promote and validate signals in the Intelligence workspace to generate recommendations."
              : "Click 'Generate Recommendations from Hypotheses' above to synthesize action items."}
          </div>
        </SectionCard>
      ) : (
        <div className="space-y-3">
          {recommendations.map((rec) => {
            const expanded = expandedId === rec.id;
            return (
              <SectionCard key={rec.id}>
                <button
                  onClick={() => setExpandedId(expanded ? null : rec.id)}
                  className="flex items-start gap-3 w-full text-left"
                >
                  <span
                    className={cn(
                      "vf-text-micro px-1.5 py-0.5 rounded font-semibold shrink-0 mt-0.5",
                      PRIORITY_COLORS[rec.priority] ?? "bg-muted"
                    )}
                  >
                    {rec.priority}
                  </span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="vf-text-body-m font-bold">{rec.title}</h3>
                      {rec.grounding_type && GROUNDING_LABELS[rec.grounding_type] && (
                        <span className={cn("vf-text-micro px-1.5 py-0.5 rounded", GROUNDING_LABELS[rec.grounding_type].class)}>
                          {GROUNDING_LABELS[rec.grounding_type].text}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {rec.horizon} · {rec.projectedValue}
                    </div>
                  </div>
                  {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
                {expanded && (
                  <div className="mt-3 text-xs space-y-2 pl-8">
                    <p>
                      <b>Prospect Pain:</b> {rec.prospectPain}
                    </p>
                    <p>
                      <b>Root Driver:</b> {rec.rootDriver}
                    </p>
                    <p>
                      <b>Capability:</b> {rec.ourCapability}
                    </p>
                    <div className="flex items-center gap-2 pt-1">
                      <Btn
                        variant="primary"
                        onClick={() =>
                          navigateTo("calculator", { accountId }, { query: { hypothesisId: rec.id } })
                        }
                      >
                        Model Impact <ArrowRight size={12} />
                      </Btn>
                    </div>
                  </div>
                )}
              </SectionCard>
            );
          })}
        </div>
      )}

      {/* Product Portfolio (DIL) */}
      {products.length > 0 && (
        <SectionCard title="Product Portfolio" className="mt-4">
          <p className="vf-text-caption text-muted-foreground mb-3">
            Products from the knowledge graph that map to identified capabilities
          </p>
          <div className="grid grid-cols-3 gap-2">
            {products.slice(0, 6).map((p) => (
              <ProductBadge key={p.id} p={p} />
            ))}
          </div>
        </SectionCard>
      )}
    </ValueStudioShellComponent>
  );
}
