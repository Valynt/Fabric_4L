import sys

with open("PRODUCTION_READINESS_AUDIT.md", "r") as f:
    text = f.read()

# Replace Top 10 Risks
text = text.replace("1.  **L7 Billing zero authentication** — Accepts tenant identity purely from spoofable headers (`X-Tenant-ID`) without cryptographic validation.\n", "")
text = text.replace("8.  **Dev auth bypass (ALLOW_INSECURE_DEV_AUTH_BYPASS)** present in committed compose files — High risk of misconfiguration in production.\n", "")
text = text.replace("9.  **No PostgreSQL backup implementation** — While Neo4j has a backup manager, the primary transactional DB is unprotected.", "9.  **Incomplete PostgreSQL backup strategy** — While a backup CronJob exists, it lacks documented validation for offsite storage and recovery.")

# Replace Actions
text = text.replace("1.  Add JWT validation + `GovernanceMiddleware` + `RateLimitMiddleware` to L7 Billing immediately.\n", "")
text = text.replace("6.  Implement PostgreSQL pg_dump/base-backup manager and document the recovery runbook.", "6.  Validate the PostgreSQL pg_dump CronJob against offsite storage and document the recovery runbook.")

# Typo
text = text.replace("Postgres RLS,Composite indexes", "Postgres RLS, Composite indexes")

with open("PRODUCTION_READINESS_AUDIT.md", "w") as f:
    f.write(text)