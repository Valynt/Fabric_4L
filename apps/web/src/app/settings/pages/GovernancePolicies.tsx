export function GovernancePolicies() {
  const policies = [
    { name: "Data Retention", description: "Retain ingested data for 7 years.", scope: "Tenant", lastUpdated: "Aug 1, 2025" },
    { name: "RBAC Enforcement", description: "Require explicit role assignments for all workspace access.", scope: "Tenant", lastUpdated: "Sep 10, 2025" },
    { name: "Formula Approval", description: "New formulas require admin approval before production use.", scope: "Tenant", lastUpdated: "Jul 22, 2025" },
  ];

  return (
    <div className="space-y-6">
      <section className="rounded-lg border bg-card p-5">
        <h3 className="text-sm font-semibold">Governance Policies</h3>
        <p className="text-xs text-muted-foreground">Tenant-wide rules for data, access, and model governance.</p>
        <div className="mt-4 space-y-2">
          {policies.map((p) => (
            <div key={p.name} className="rounded-md border p-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">{p.name}</p>
                <button type="button" className="text-xs font-medium text-primary hover:underline">Edit policy</button>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{p.description}</p>
              <p className="mt-2 vf-text-micro text-muted-foreground">Scope: {p.scope} • Last updated {p.lastUpdated}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
