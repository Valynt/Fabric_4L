/**
 * Account Intake Modal — "New Value Case"
 *
 * Launched from the Accounts page. Gathers the minimum information
 * needed to seed the Intelligence pipeline:
 *   - Company name (or select existing account)
 *   - Industry
 *   - Primary contact / buyer role
 *   - Known pain points (optional)
 *   - Analysis depth (Fast / Balanced / Deep)
 *
 * On submit:
 *   1. Creates or updates the Account record
 *   2. Navigates to /intelligence/{accountId}/signals
 */
import { useState } from "react";
import { useNavigation } from "@/hooks/useNavigation";
import {
  X,
  Search,
  Sparkles,
  Building2,
  User,
  AlertTriangle,
  Gauge,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { buildCreateAccountPayload, useCreateAccount } from "@/hooks/useAccounts";
import { getOrCreateCanonicalCaseId, persistWorkspaceTab } from "@/hooks/useWorkspaceCase";
import { Btn } from "@/components/ui/fabric";

interface ApiValidationDetail {
  msg?: string;
  message?: string;
  loc?: Array<string | number>;
}

function formatSubmitError(error: unknown): string {
  if (typeof error === "object" && error !== null && "responseData" in error) {
    const responseData = (error as { responseData?: unknown }).responseData;
    if (responseData && typeof responseData === "object") {
      const details = (responseData as { detail?: unknown }).detail;

      if (Array.isArray(details)) {
        const formatted = details
          .map(item => {
            if (!item || typeof item !== "object") return null;
            const detail = item as ApiValidationDetail;
            const field = Array.isArray(detail.loc)
              ? detail.loc.filter(part => part !== "body").join(".")
              : "";
            const message = detail.msg ?? detail.message;
            if (!message) return null;
            return field ? `${field}: ${message}` : message;
          })
          .filter((msg): msg is string => Boolean(msg));

        if (formatted.length > 0) {
          return `Please review the form: ${formatted.join("; ")}`;
        }
      }

      if (typeof details === "string" && details.trim()) {
        return details;
      }

      const message = (responseData as { message?: unknown }).message;
      if (typeof message === "string" && message.trim()) {
        return message;
      }
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return "Failed to create account";
}

function parseAnnualRevenue(value: string): number | undefined {
  const trimmed = value.trim();
  if (!trimmed) return undefined;

  const sanitized = trimmed.replace(/[$,\s]/g, "");
  const match = sanitized.match(/^([0-9]*\.?[0-9]+)([kKmMbBtT])?$/);
  if (!match) return undefined;

  const numeric = Number(match[1]);
  if (!Number.isFinite(numeric)) return undefined;

  const suffix = match[2]?.toLowerCase();
  const multiplierMap: Record<string, number> = {
    k: 1_000,
    m: 1_000_000,
    b: 1_000_000_000,
    t: 1_000_000_000_000,
  };

  return suffix
    ? Math.round(numeric * multiplierMap[suffix])
    : Math.round(numeric);
}

// ── Types ─────────────────────────────────────────────────────────────────────

interface AccountIntakeModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit?: (accountId: string) => void;
}

type AnalysisDepth = "fast" | "balanced" | "deep";

// ── Constants ────────────────────────────────────────────────────────────────────

const INPUT_BASE_CLASSES =
  "w-full h-9 px-3 vf-text-body-s rounded-md border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary";

const TEXTAREA_CLASSES =
  "w-full px-3 py-2 vf-text-body-s rounded-md border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none";

const DEPTH_OPTIONS: {
  key: AnalysisDepth;
  label: string;
  description: string;
}[] = [
  {
    key: "fast",
    label: "Fast",
    description: "Quick scan — web enrichment only",
  },
  {
    key: "balanced",
    label: "Balanced",
    description: "Standard — web + document analysis",
  },
  {
    key: "deep",
    label: "Deep",
    description: "Comprehensive — all sources + competitive intel",
  },
];

// ── Modal ─────────────────────────────────────────────────────────────────────

export default function AccountIntakeModal({
  open,
  onClose,
  onSubmit,
}: AccountIntakeModalProps) {
  const { navigateTo } = useNavigation();
  const createAccount = useCreateAccount();

  // Form state
  const [companyName, setCompanyName] = useState("");
  const [industry, setIndustry] = useState("");
  const [revenue, setRevenue] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactRole, setContactRole] = useState("");
  const [painPoints, setPainPoints] = useState("");
  const [depth, setDepth] = useState<AnalysisDepth>("balanced");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const canSubmit = companyName.trim().length > 0;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setIsSubmitting(true);
    setError(null);

    try {
      const annualRevenue = parseAnnualRevenue(revenue);
      const slug = companyName.trim().toLowerCase().replace(/\s+/g, '-');
      const payload = buildCreateAccountPayload({
        name: companyName.trim(),
        provider: 'manual' as const,
        provider_record_id: `manual-${slug}`,
        domain: `${slug}.com`,
        industry: industry.trim() || undefined,
        owner_name: contactName.trim() || undefined,
        company_size: undefined,
        annual_revenue: annualRevenue,
        website: `${slug}.com`,
        stage: 'prospect' as const,
      });

      const result = await createAccount.mutateAsync(payload);
      const accountId = result.account.id;
      const caseId = await getOrCreateCanonicalCaseId(accountId);
      await persistWorkspaceTab(caseId, "intake", {
        account_id: accountId,
        company_name: companyName.trim(),
        industry: industry.trim() || null,
        revenue: revenue.trim() || null,
        annual_revenue: annualRevenue ?? null,
        contact_name: contactName.trim() || null,
        contact_role: contactRole.trim() || null,
        pain_points: painPoints.trim() || null,
        depth,
        created_at: new Date().toISOString(),
      });

      setIsSubmitting(false);
      onClose();
      if (onSubmit) {
        onSubmit(accountId);
      } else {
        navigateTo('intelligence-overview', { accountId });
      }
    } catch (err) {
      setIsSubmitting(false);
      setError(formatSubmitError(err));
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-background border border-border rounded-lg shadow-xl w-full max-w-[560px] max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-primary" />
            <h2 className="text-base font-bold text-foreground">
              New Value Case
            </h2>
          </div>
          <button type="button"
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
          >
            <X size={16} />
          </button>
        </div>

        {/* Form */}
        <div className="px-6 py-5 space-y-5">
          {/* Company */}
          <div>
            <label className="flex items-center gap-1.5 vf-text-body-s font-semibold text-foreground mb-1.5">
              <Building2 size={13} className="text-muted-foreground" />
              Company Name <span className="text-destructive">*</span>
            </label>
            <div className="relative">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <input
                type="text"
                value={companyName}
                onChange={e => setCompanyName(e.target.value)}
                placeholder="Search or enter company name…"
                className={`${INPUT_BASE_CLASSES} pl-9`}
              />
            </div>
          </div>

          {/* Industry + Revenue */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="vf-text-body-s font-semibold text-foreground mb-1.5 block">
                Industry
              </label>
              <input
                type="text"
                value={industry}
                onChange={e => setIndustry(e.target.value)}
                placeholder="e.g. Manufacturing"
                className={INPUT_BASE_CLASSES}
              />
            </div>
            <div>
              <label className="vf-text-body-s font-semibold text-foreground mb-1.5 block">
                Revenue
              </label>
              <input
                type="text"
                value={revenue}
                onChange={e => setRevenue(e.target.value)}
                placeholder="e.g. $4.2B"
                className={INPUT_BASE_CLASSES}
              />
            </div>
          </div>

          {/* Primary Contact */}
          <div>
            <label className="flex items-center gap-1.5 vf-text-body-s font-semibold text-foreground mb-1.5">
              <User size={13} className="text-muted-foreground" />
              Primary Contact
            </label>
            <div className="grid grid-cols-2 gap-4">
              <input
                type="text"
                value={contactName}
                onChange={e => setContactName(e.target.value)}
                placeholder="Contact name"
                className={INPUT_BASE_CLASSES}
              />
              <input
                type="text"
                value={contactRole}
                onChange={e => setContactRole(e.target.value)}
                placeholder="Role (e.g. VP Operations)"
                className={INPUT_BASE_CLASSES}
              />
            </div>
          </div>

          {/* Known Pain Points */}
          <div>
            <label className="flex items-center gap-1.5 vf-text-body-s font-semibold text-foreground mb-1.5">
              <AlertTriangle size={13} className="text-muted-foreground" />
              Known Pain Points
              <span className="vf-text-micro text-muted-foreground font-normal">
                (optional)
              </span>
            </label>
            <textarea
              value={painPoints}
              onChange={e => setPainPoints(e.target.value)}
              placeholder="Describe any known challenges, priorities, or context…"
              rows={3}
              className={TEXTAREA_CLASSES}
            />
          </div>

          {/* Analysis Depth */}
          <div>
            <label className="flex items-center gap-1.5 vf-text-body-s font-semibold text-foreground mb-2">
              <Gauge size={13} className="text-muted-foreground" />
              Analysis Depth
            </label>
            <div className="grid grid-cols-3 gap-2">
              {DEPTH_OPTIONS.map(opt => (
                <button type="button"
                  key={opt.key}
                  onClick={() => setDepth(opt.key)}
                  className={cn(
                    "flex flex-col items-center px-3 py-2.5 rounded-md border text-center transition-colors",
                    depth === opt.key
                      ? "border-primary bg-primary/5 text-primary"
                      : "border-border text-muted-foreground hover:border-foreground/20"
                  )}
                >
                  <span className="vf-text-body-s font-semibold">{opt.label}</span>
                  <span className="vf-text-micro mt-0.5 leading-tight">
                    {opt.description}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="px-6 pb-4">
            <div className="p-3 rounded-md bg-destructive/10 text-destructive vf-text-body-s">
              {error}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border">
          <Btn variant="outline" onClick={onClose}>
            Cancel
          </Btn>
          <Btn
            variant="primary"
            onClick={handleSubmit}
            disabled={!canSubmit || isSubmitting}
            className="gap-1.5"
          >
            <Sparkles size={13} />
            {isSubmitting ? "Launching…" : "Launch Intelligence"}
          </Btn>
        </div>
      </div>
    </div>
  );
}
