export function PersonalSessions() {
  const sessions = [
    { device: "Chrome on macOS", location: "New York, US", current: true, lastActive: "Now" },
    { device: "Safari on iPhone", location: "New York, US", current: false, lastActive: "2 hours ago" },
    { device: "Firefox on Windows", location: "Remote", current: false, lastActive: "3 days ago" },
  ];

  return (
    <div className="space-y-6">
      <section className="rounded-lg border bg-card p-5">
        <h3 className="text-sm font-semibold">Active Sessions</h3>
        <p className="text-xs text-muted-foreground">Review and manage devices signed into your account.</p>
        <div className="mt-4 space-y-2">
          {sessions.map((s) => (
            <div key={s.device} className="flex items-center justify-between rounded-md border p-3">
              <div>
                <p className="text-sm font-medium">
                  {s.device}
                  {s.current && (
                    <span className="ml-2 inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 vf-text-micro font-medium text-primary">
                      Current
                    </span>
                  )}
                </p>
                <p className="text-xs text-muted-foreground">{s.location} • {s.lastActive}</p>
              </div>
              {!s.current && (
                <button type="button" className="text-xs font-medium text-destructive hover:underline">
                  Revoke
                </button>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border bg-card p-5">
        <h3 className="text-sm font-semibold">Sign Out Everywhere</h3>
        <p className="text-xs text-muted-foreground">Terminate all other active sessions across all devices.</p>
        <div className="mt-4">
          <button type="button" className="inline-flex h-9 items-center rounded-md border px-4 text-sm font-medium hover:bg-accent">
            Sign out all other sessions
          </button>
        </div>
      </section>
    </div>
  );
}
