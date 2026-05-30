# Neo4j Authentication Rate-Limit Recovery Runbook

## Purpose

Recover Neo4j access when authentication failures or rate limits lock out service users while preserving data and tenant isolation.

## Trigger

Layer 3 readiness failures, repeated Neo4j authentication errors, lockout alerts, graph API errors, or failed migrations caused by credential rejection.

## Severity

SEV-1 if production graph APIs are unavailable; SEV-2 if only write paths or a subset of tenants are degraded; SEV-3 for non-production or preventive credential drift.

## Preconditions

Break-glass admin access, secret manager access, current Neo4j connection settings, affected service list, and rollback credentials are available.

## Immediate Actions

1. Declare or confirm the incident owner and severity.
2. Freeze risky automated changes affecting the impacted service or control.
3. Capture initial timestamps, tenant/customer scope, deployment version, and active alerts.
4. Use the diagnosis steps below before applying destructive or irreversible changes.

## Diagnosis Steps

1. Confirm the trigger condition and affected environment.
2. Review the relevant dashboards, logs, audit records, and CI/readiness gate output.
3. Identify whether the issue is isolated to one tenant, service, dependency, or deployment version.
4. Preserve evidence before restarting services, rotating credentials, restoring data, or changing routing.

## Resolution Steps

1. Apply the least-risk corrective action that addresses the confirmed failure mode.
2. Keep tenant isolation, contract compatibility, and fail-closed security behavior intact.
3. Escalate to the service owner or incident commander before any destructive operation.
4. Record each operator action, command, and configuration change in the incident record.

## Validation

- Re-run the relevant health checks, smoke tests, contract checks, or readiness gates listed below.
- Confirm impacted tenants/customers can complete the critical path that failed.
- Confirm logs, metrics, and audit records show recovery and no new cross-tenant or security errors.

## Rollback / Fallback

- Prefer rollback to the last known-good deployment, configuration, registry record, backup, or credential set.
- If rollback is unsafe, isolate the impacted component, drain traffic where supported, and use the documented fallback path in the procedure details.
- Do not delete evidence or failed artifacts until the incident commander approves cleanup.

## Customer / Stakeholder Communication

- Notify the incident channel and accountable product/support stakeholders when customer impact is confirmed or likely.
- Provide scope, severity, current mitigation, expected next update time, and known customer-facing symptoms.
- Avoid sharing secrets, raw tenant data, provider tokens, or unreviewed root-cause speculation.

## Evidence to Preserve

- Alert names, timestamps, dashboard snapshots or links, and runbook version.
- Deployment SHAs, configuration diffs, migration IDs, registry versions, or backup artifact IDs.
- Sanitized logs, audit events, gate outputs, validation commands, and operator action timeline.

## Related Gates

Observability alert gates for Neo4j auth failures/lockouts, Layer 3 readiness gates, tenant-isolation gates after credential changes, migration readiness gates if migrations were interrupted, and deployment gates for secret rollouts.

## Related Runbooks

- [Neo4j Backup and Restore Runbook](neo4j-backup-restore.md)
- [Neo4j High Availability Runbook](neo4j-ha.md)
- [CI Infisical OIDC Recovery and Secret Rotation](operational/ci-infisical-oidc-recovery.md)

## Post-Incident Follow-Up

- Attach validation evidence and gate results to the incident record.
- File corrective actions for missing alerts, missing tests, stale documentation, or slow recovery steps.
- Update this runbook and related gates if the incident exposed drift or an undocumented dependency.

---

## Procedure Details

### Overview

This runbook covers recovery procedures for Neo4j authentication failures caused by rate-limit lockout. Neo4j Enterprise Edition has built-in authentication rate limiting that temporarily locks accounts after repeated failed authentication attempts.

### Detection

#### Symptoms

- Layer3 health check returns `neo4j_uninitialized` or `dependency_unhealthy`
- Neo4j connection errors with authentication failure messages
- Logs show: `Authentication failed: too many failed attempts`
- Schema migration jobs fail with connection refused

#### Verification

```bash
# Check Neo4j logs for auth failures
docker-compose -f docker-compose.live.yml logs neo4j | grep -i "auth"

# Test direct Neo4j connection
docker-compose -f docker-compose.live.yml exec neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD "RETURN 1"
```

### Recovery Procedures

#### Environment-Specific Recovery

##### Development Environment Only

**WARNING: Data deletion is ONLY acceptable in development environments.**

If running in a development environment and you need to quickly recover:

```bash
# Stop all services
docker-compose -f docker-compose.live.yml down

# Remove Neo4j data volume (DELETES ALL DATA)
docker volume rm vf-live_neo4j-data

# Restart services
docker-compose -f docker-compose.live.yml up -d

# Run migrations
docker-compose -f docker-compose.live.yml run --rm layer3-neo4j-migrate
```

##### Staging/Production Environments

**FORBIDDEN: Do not delete Neo4j data volumes in staging or production.**

Use one of the following safe recovery methods:

#### Method 1: Wait for Rate-Limit Expiration

Neo4j's rate-limit lockout is temporary. The default lockout duration is typically 5-15 minutes.

1. Monitor the situation for up to 15 minutes
2. Retry authentication after the lockout period expires
3. Verify Layer3 health check passes

#### Method 2: Reset via Neo4j Admin (Enterprise)

If you have Neo4j Enterprise Edition with admin access:

```bash
# Connect to Neo4j with admin credentials
docker-compose -f docker-compose.live.yml exec neo4j cypher-shell -u neo4j -a

# Reset failed authentication attempts for the user
CALL dbms.security.clearFailedAuthAttempts('neo4j')

# Verify the user is unlocked
CALL dbms.security.listUsers()
```

#### Method 3: Change Password via Admin

If the password is unknown or compromised:

```bash
# Connect as admin
docker-compose -f docker-compose.live.yml exec neo4j cypher-shell -u neo4j -a

# Change the password for the neo4j user
ALTER USER neo4j SET PASSWORD 'new_secure_password'

# Update environment variables
# Update NEO4J_PASSWORD in .env or secret management
# Update NEO4J_AUTH environment variable if used
```

#### Method 4: Create New Service User

If the neo4j user cannot be recovered:

```bash
# Connect as admin
docker-compose -f docker-compose.live.yml exec neo4j cypher-shell -u neo4j -a

# Create a new service user with appropriate privileges
CREATE USER fabric_service SET PASSWORD 'secure_password' CHANGE NOT REQUIRED
GRANT ROLE reader TO fabric_service
GRANT ROLE editor TO fabric_service
GRANT ROLE publisher TO fabric_service

# Update Layer3 configuration to use the new user
# Update NEO4J_USER and NEO4J_PASSWORD environment variables
```

### Prevention

#### 1. Use Correct Credentials

Ensure `NEO4J_AUTH` environment variable is set correctly in all services:

```yaml
# docker-compose.live.yml
environment:
  NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
```

#### 2. Implement Connection Pooling

Configure connection pools in Layer3 to avoid excessive connection attempts:

```python
# value_fabric/layer3/api/dependencies.py
from neo4j import AsyncGraphDatabase

driver = AsyncGraphDatabase.driver(
    settings.neo4j_uri,
    auth=(settings.neo4j_user, settings.neo4j_password),
    max_connection_lifetime=3600,
    max_connection_pool_size=50,
    connection_acquisition_timeout=60,
)
```

#### 3. Add Health Check Backoff

Implement exponential backoff in Layer3 health checks:

```python
# value_fabric/layer3/api/routes/system.py
import asyncio

async def check_dependencies_with_backoff():
    max_retries = 5
    base_delay = 2
    
    for attempt in range(max_retries):
        try:
            return await check_dependencies()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)
```

#### 4. Monitor Authentication Failures

Set up monitoring for Neo4j authentication failures:

```bash
# Add to observability stack
# Track metrics: neo4j_auth_failures_total, neo4j_auth_lockouts_total
```

### Post-Recovery Validation

After any recovery procedure:

1. Verify Neo4j connectivity:
   ```bash
   docker-compose -f docker-compose.live.yml exec layer3 python -c "
   import requests
   print(requests.get('http://localhost:8001/health').text)
   "
   ```

2. Verify schema initialization:
   ```bash
   docker-compose -f docker-compose.live.yml exec layer3 python -c "
   from value_fabric.layer3.schema.initializer import SchemaInitializer
   # Verify schema status
   "
   ```

3. Verify all Layer3 endpoints are healthy:
   ```bash
   curl http://localhost:8001/health
   curl http://localhost:8001/readiness
   ```

### Escalation

If recovery procedures fail:

1. Check Neo4j logs for additional errors:
   ```bash
   docker-compose -f docker-compose.live.yml logs neo4j --tail=100
   ```

2. Verify Neo4j service is running:
   ```bash
   docker-compose -f docker-compose.live.yml ps neo4j
   ```

3. Check Neo4j resource limits (memory, CPU)

4. Escalate to platform engineering team for:
   - Neo4j Enterprise support contact
   - Database administrator review
   - Potential data backup/restore if corruption is suspected

### Related Documentation

- [Neo4j Security Documentation](https://neo4j.com/docs/operations-manual/current/security/)
- [Layer3 Architecture](../reference/layer-runtime-path-governance.md)
- [Platform Contract](../contract.md)
