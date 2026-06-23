export function DataValuePacks() {
  const packs = [
    { name: "Manufacturing", description: "OEE, throughput, and plant optimization formulas.", status: "Enabled" },
    { name: "AI / Data Platform", description: "LLM cost models, MLOps, and inference pricing.", status: "Enabled" },
    { name: "Financial Services", description: "Regulatory capital, risk-adjusted returns, and compliance.", status: "Available" },
    { name: "Healthcare", description: "Patient throughput, device utilization, and clinical value.", status: "Available" },
  ];

  return (
    <div className="space-y-6">
      <section className="rounded-lg border bg-card p-5">
        <h3 className="text-sm font-semibold">Value Packs</h3>
        <p className="text-xs text-muted-foreground">Enable industry capabilities, formulas, templates, and benchmarks.</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {packs.map((p) => (
            <div key={p.name} className="rounded-md border p-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">{p.name}</p>
                <span className={p.status === "Enabled" ? "vf-text-micro font-medium text-primary" : "vf-text-micro font-medium text-muted-foreground"}>{p.status}</span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{p.description}</p>
              <div className="mt-3">
                <button
                  type="button"
                  className={p.status === "Enabled"
                    ? "inline-flex h-7 items-center rounded-md border px-2 text-xs font-medium hover:bg-accent"
                    : "inline-flex h-7 items-center rounded-md bg-primary px-2 text-xs font-medium text-primary-foreground hover:opacity-90"
                  }
                >
                  {p.status === "Enabled" ? "Manage" : "Enable"}
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
