import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Building2, Briefcase, Globe,
  CheckCircle2, BrainCircuit, AlertTriangle, ArrowRight
} from "lucide-react";

type Status = "complete" | "inferred" | "needed";

interface StatusPill {
  label: string;
  status: Status;
}

function StatusChip({ pill }: { pill: StatusPill }) {
  const config: Record<Status, { icon: typeof CheckCircle2; classes: string }> = {
    complete: { icon: CheckCircle2, classes: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20" },
    inferred: { icon: BrainCircuit, classes: "bg-muted text-muted-foreground border-border" },
    needed: { icon: AlertTriangle, classes: "bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/20" },
  };
  const c = config[pill.status];
  const Icon = c.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 h-7 rounded-full text-[13px] font-medium border ${c.classes}`}>
      <Icon className="w-3.5 h-3.5" />
      {pill.label}
    </span>
  );
}

const objectives = [
  "Reduce costs",
  "Increase revenue",
  "Improve efficiency",
  "Mitigate risk",
  "Custom…",
];

export default function ProspectSetup() {
  const navigate = useNavigate();
  const [company, setCompany] = useState("Meridian Automotive Components");
  const [contact, setContact] = useState("Patricia Chen");
  const [title, setTitle] = useState("VP Manufacturing Operations");
  const [objective, setObjective] = useState<string | null>(null);
  const [customObjective, setCustomObjective] = useState("");
  const [buyerConfirmed, setBuyerConfirmed] = useState(false);
  const [companyConfirmed, setCompanyConfirmed] = useState(false);
  const [crmReviewed, setCrmReviewed] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const objectiveError = !objective && !isAnalyzing;

  const statusPills: StatusPill[] = [
    { label: "Company", status: company.trim() ? "complete" : "needed" },
    { label: "Primary Contact", status: contact.trim() ? "complete" : "needed" },
    { label: `Buyer Role ${buyerConfirmed ? "" : "(inferred)"}`, status: buyerConfirmed ? "complete" : title ? "inferred" : "needed" },
    { label: `Primary Objective ${objective ? "" : "(needed)"}`, status: objective ? "complete" : "needed" },
  ];

  const canContinue = company.trim() && contact.trim() && objective;

  const handleContinue = () => {
    if (!canContinue) return;
    setIsAnalyzing(true);
    setTimeout(() => navigate("/intelligence"), 1500);
  };

  return (
    <main className="max-w-[880px] mx-auto pt-10 pb-24" aria-label="Prospect Setup">
      {/* Step Label */}
      <div className="mb-5">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Step 1 of 7</span>
        <div className="w-20 h-[3px] bg-primary rounded-full mt-2" />
      </div>

      {/* Hero */}
      <header className="text-center mb-7">
        <h1 className="text-[42px] leading-[48px] font-bold text-foreground tracking-tight">
          Construct a Value Model
        </h1>
        <p className="text-xl leading-8 text-muted-foreground max-w-[680px] mx-auto mt-3">
          Start with the company and primary contact. ValuePilot will enrich the rest and highlight anything that needs confirmation.
        </p>
      </header>

      {/* Setup Status Strip */}
      <section className="flex flex-wrap items-center gap-3 px-4 py-3 bg-card border border-border rounded-[14px] mb-6">
        <span className="text-sm font-semibold text-foreground mr-1">Setup status</span>
        {statusPills.map((pill) => (
          <StatusChip key={pill.label} pill={pill} />
        ))}
      </section>

      {/* Main Intake Card */}
      <section className="bg-card border border-border rounded-[20px] p-7 mb-5">
        {/* Card header */}
        <div className="flex items-center gap-2.5 mb-2">
          <Building2 className="w-[18px] h-[18px] text-primary" />
          <h2 className="text-2xl leading-8 font-semibold text-foreground">Prospect Context</h2>
        </div>
        <p className="text-[15px] leading-6 text-muted-foreground">
          These inputs unlock everything else. We'll enrich, infer, and validate automatically.
        </p>
        <hr className="border-border my-5" />

        {/* Company */}
        <div className="mb-5">
          <label className="block text-sm font-semibold text-foreground mb-2">Company Name</label>
          <input
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="e.g. Meridian Automotive Components"
            className="w-full h-14 px-4 bg-muted border border-input rounded-[14px] text-lg placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent transition-all"
          />
        </div>

        {/* Contact Row */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div>
            <label className="block text-sm font-semibold text-foreground mb-2">Main Contact</label>
            <input
              value={contact}
              onChange={(e) => setContact(e.target.value)}
              placeholder="e.g. Patricia Chen"
              className="w-full h-14 px-4 bg-muted border border-input rounded-[14px] text-lg placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent transition-all"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-foreground mb-2">Contact Title</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. VP Manufacturing Operations"
              className="w-full h-14 px-4 bg-muted border border-input rounded-[14px] text-lg placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent transition-all"
            />
          </div>
        </div>

        {/* Primary Objective */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-1.5">
            <label className="text-sm font-semibold text-foreground">Primary Objective</label>
            <span className="inline-flex items-center text-xs font-medium text-amber-800 bg-amber-50 dark:text-amber-400 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 px-2 py-0.5 rounded-full">
              Required
            </span>
          </div>
          <p className="text-[13px] leading-5 text-muted-foreground mb-3">
            What is the main outcome you want to demonstrate?
          </p>

          <div className="grid grid-cols-2 gap-3">
            {objectives.map((obj) => (
              <button
                key={obj}
                onClick={() => { setObjective(obj); if (obj !== "Custom…") setCustomObjective(""); }}
                className={`flex items-center min-h-[52px] px-4 py-3.5 rounded-[14px] border text-[15px] font-medium text-left transition-all ${
                  objective === obj
                    ? "border-foreground bg-muted ring-2 ring-primary/20"
                    : "border-input bg-card hover:border-muted-foreground/30"
                }`}
              >
                {obj}
              </button>
            ))}
          </div>

          {objective === "Custom…" && (
            <input
              value={customObjective}
              onChange={(e) => setCustomObjective(e.target.value)}
              placeholder="Describe your custom objective..."
              className="w-full h-14 px-4 mt-3 bg-muted border border-input rounded-[14px] text-lg placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent transition-all"
            />
          )}

          {objectiveError && (
            <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">
              Choose the main outcome so we can shape the model correctly.
            </p>
          )}
        </div>

        {/* Inline Intelligence Cards */}
        <div className="space-y-3 mt-6">
          {/* Buyer Role Detected */}
          {contact && title && !buyerConfirmed && (
            <div className="border border-border rounded-2xl p-4">
              <div className="flex items-start gap-3">
                <BrainCircuit className="w-[18px] h-[18px] text-primary shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <h3 className="text-base font-semibold text-foreground">Buyer Role Detected</h3>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    Based on title &ldquo;{title}&rdquo;
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-base font-semibold text-foreground">Economic Buyer</span>
                    <span className="inline-flex items-center text-[11px] font-medium text-muted-foreground bg-muted border border-border px-2 py-0.5 rounded-full">
                      Inferred
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    Likely priorities: Cost reduction, throughput, labor efficiency
                  </p>
                  <div className="flex items-center gap-3 mt-3">
                    <button
                      onClick={() => setBuyerConfirmed(true)}
                      className="h-9 px-3.5 bg-primary text-primary-foreground rounded-[10px] text-sm font-semibold hover:bg-primary/90 transition-colors"
                    >
                      Confirm
                    </button>
                    <button className="h-9 px-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                      Adjust
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {buyerConfirmed && (
            <div className="flex items-center gap-2 px-4 py-2.5 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 rounded-2xl">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span className="text-sm text-emerald-700 dark:text-emerald-400 font-medium">Economic Buyer confirmed — {title}</span>
            </div>
          )}

          {/* Company Profile Found */}
          {company && (
            <div className="border border-border rounded-2xl p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <Globe className="w-[18px] h-[18px] text-muted-foreground shrink-0 mt-0.5" />
                  <div>
                    <h3 className="text-base font-semibold text-foreground">Company Profile Found</h3>
                    <p className="text-sm text-foreground font-medium mt-1">12K employees · $4.2B revenue</p>
                    <p className="text-sm text-muted-foreground mt-0.5">Source: enrichment</p>
                  </div>
                </div>
                {!companyConfirmed ? (
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => setCompanyConfirmed(true)}
                      className="h-9 px-3.5 bg-primary text-primary-foreground rounded-[10px] text-sm font-semibold hover:bg-primary/90 transition-colors"
                    >
                      Confirm
                    </button>
                    <button className="h-9 px-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                      Edit
                    </button>
                  </div>
                ) : (
                  <span className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400 font-semibold shrink-0">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Confirmed
                  </span>
                )}
              </div>
            </div>
          )}

          {/* CRM Opportunity Found */}
          <div className="border border-border rounded-2xl p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <Briefcase className="w-[18px] h-[18px] text-muted-foreground shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-base font-semibold text-foreground">CRM Opportunity Found</h3>
                  <p className="text-sm text-foreground font-medium mt-1">MAC-2026-0417 (Salesforce)</p>
                </div>
              </div>
              {!crmReviewed ? (
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => setCrmReviewed(true)}
                    className="h-9 px-3.5 bg-primary text-primary-foreground rounded-[10px] text-sm font-semibold hover:bg-primary/90 transition-colors"
                  >
                    Review
                  </button>
                  <button
                    onClick={() => setCrmReviewed(true)}
                    className="h-9 px-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Ignore
                  </button>
                </div>
              ) : (
                <span className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400 font-semibold shrink-0">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Reviewed
                </span>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Action Row */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleContinue}
          disabled={!canContinue || isAnalyzing}
          className={`h-[52px] px-5 rounded-[14px] text-[15px] font-semibold inline-flex items-center gap-2 transition-all ${
            canContinue && !isAnalyzing
              ? "bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm"
              : "bg-muted text-muted-foreground cursor-not-allowed"
          }`}
        >
          {isAnalyzing ? (
            <>
              <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              Continue to Intelligence
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
        <button className="text-[15px] font-medium text-muted-foreground hover:text-foreground transition-colors px-3 h-[52px]">
          Save draft
        </button>
      </div>

      {/* Optional: Missing inputs cue (subtle, only when needed) */}
      {!canContinue && (
        <div className="mt-4 flex items-start gap-2 text-xs text-muted-foreground">
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
          <div>
            <span className="font-medium text-foreground">Before we continue:</span>
            <ul className="mt-0.5 space-y-0.5 ml-1">
              {!company.trim() && <li>· Add company name</li>}
              {!contact.trim() && <li>· Add primary contact</li>}
              {!objective && <li>· Select a primary objective</li>}
            </ul>
          </div>
        </div>
      )}
    </main>
  );
}
