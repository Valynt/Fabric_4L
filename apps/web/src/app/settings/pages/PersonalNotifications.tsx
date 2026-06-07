export function PersonalNotifications() {
  const channels = [
    { label: "Email alerts", desc: "Receive important updates via email" },
    { label: "In-app alerts", desc: "Show notifications inside the platform" },
    { label: "Push notifications", desc: "Browser push notifications" },
    { label: "Slack alerts", desc: "Send alerts to a connected Slack channel" },
  ];

  const events = [
    "Account changes",
    "Billing events",
    "Security alerts",
    "Team invitations",
    "Data ingestion completions",
    "Governance policy updates",
  ];

  return (
    <div className="space-y-6">
      <section className="rounded-lg border bg-card p-5">
        <h3 className="text-sm font-semibold">Notification Channels</h3>
        <div className="mt-4 space-y-3">
          {channels.map((c) => (
            <div key={c.label} className="flex items-center justify-between rounded-md border p-3">
              <div>
                <p className="text-sm font-medium">{c.label}</p>
                <p className="text-xs text-muted-foreground">{c.desc}</p>
              </div>
              <label className="relative inline-flex cursor-pointer items-center">
                <input type="checkbox" className="peer sr-only" defaultChecked />
                <div className="h-5 w-9 rounded-full bg-muted-foreground/30 transition-colors peer-checked:bg-primary" />
                <div className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-background transition-transform peer-checked:translate-x-4" />
              </label>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border bg-card p-5">
        <h3 className="text-sm font-semibold">Event Subscriptions</h3>
        <p className="text-xs text-muted-foreground">Choose which events you want to be notified about.</p>
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {events.map((e) => (
            <label key={e} className="flex items-center gap-2 rounded-md border p-3">
              <input type="checkbox" defaultChecked className="h-4 w-4 rounded border" />
              <span className="text-sm">{e}</span>
            </label>
          ))}
        </div>
      </section>
    </div>
  );
}
