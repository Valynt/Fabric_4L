import sys
import re

with open("PRODUCTION_READINESS_AUDIT.md", "r") as f:
    text = f.read()

# Remove PROD-P0-001 section
text = re.sub(r'### PROD-P0-001: L7 Billing Has Zero Authentication\n.*?(?=\n### PROD-P0-002:)', '', text, flags=re.DOTALL)

# Fix PROD-P0-005 title and description
text = text.replace('### PROD-P0-005: No PostgreSQL Backup Implementation', '### PROD-P0-005: Incomplete PostgreSQL Backup Strategy')
text = text.replace('- **Description**: While Neo4j has a robust automated backup system via Aura/cron, the core PostgreSQL transactional database has no documented or automated backup implementation.', '- **Description**: While a PostgreSQL `pg_dump` CronJob exists, there is no documented offsite storage, automated recovery runbook, or regular restore validation.')

# TICKET-INFRA-001 fix
text = text.replace('**Problem**: The core PostgreSQL database has no automated backup implementation.', '**Problem**: The core PostgreSQL database backup CronJob lacks documented offsite storage and restore validation.')

# Phase 0 PROD-P0-006 -> TICKET-SEC-004
text = text.replace('PROD-P0-006 (Auth bypass fix)', 'TICKET-SEC-004 (Auth bypass fix)')

# Phase 1 PROD-P0-001 -> remove, add TICKET-SEC-005
text = text.replace('PROD-P0-001 (L7 Auth), PROD-P0-002 (L2 Auth), PROD-P0-003 (L1 SSRF), PROD-P1-001 (S2S Auth).', 'PROD-P0-002 (L2 Auth), PROD-P0-003 (L1 SSRF), PROD-P1-001 (S2S Auth), TICKET-SEC-005 (Neo4j encryption).')

# Remove TICKET-SEC-001 section
text = re.sub(r'### \[TICKET-SEC-001\] Add Authentication and Rate Limiting to L7 Billing\n.*?(?=\n### \[TICKET-SEC-002\])', '', text, flags=re.DOTALL)

# Phase 3 PROD-P0-010 -> TICKET-SEC-006, PROD-FE-003 -> TICKET-FE-001
text = text.replace('PROD-P0-010 (Demo data), PROD-FE-003 (Entitlements)', 'TICKET-SEC-006 (Demo data), TICKET-FE-001 (Entitlements)')

# Replace TICKET-FE-001 (entitlements TODO)
text = text.replace('**Problem**: The frontend uses `// TODO` stubs for critical entitlements checks, bypassing server-side RBAC validation.', '**Problem**: The frontend entitlements check requires robust caching and error handling around the server-side API call.')

with open("PRODUCTION_READINESS_AUDIT.md", "w") as f:
    f.write(text)