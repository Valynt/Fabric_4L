import { CapabilityGate } from "../components/CapabilityGate";
import { useOperationalAudit } from "@/hooks/useOperationalAudit";

export function PersonalActivity() {
  const { data, isLoading, error } = useOperationalAudit({ eventType: "security", perPage: 20 });

  return (
    <CapabilityGate capability="personal">
      <section className="rounded-lg border bg-card p-5">
        <h3 className="text-sm font-semibold">My Recent Security & Account Events</h3>
        <p className="text-xs text-muted-foreground">Recent authentication, session, and account changes associated with your account.</p>
        {isLoading ? <p className="mt-4 text-sm text-muted-foreground">Loading your activity...</p> : error ? <p className="mt-4 text-sm text-destructive">Unable to load your activity: {error.message}</p> : (
          <ul className="mt-4 space-y-2">
            {data?.entries.length ? data.entries.map((entry) => (
              <li key={entry.id} className="rounded-md border p-3 text-sm">
                <p className="font-medium">{entry.action}</p>
                <p className="text-xs text-muted-foreground">{new Date(entry.timestamp).toLocaleString()}</p>
              </li>
            )) : <li className="rounded-md border p-3 text-sm text-muted-foreground">No recent personal security/account events available.</li>}
          </ul>
        )}
      </section>
    </CapabilityGate>
  );
}
