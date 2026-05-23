# Runbook: AuthAnomaly

## Overview

A sustained spike in authentication or authorization failures has been detected in service logs. This may indicate credential stuffing, expired tokens at scale, a misconfigured identity provider, or an upstream RBAC regression. The alert evaluates the rate of failure keywords (`InvalidToken`, `SignatureVerification`, `TokenExpired`, `AccessDenied`, `RBAC.denied`) over a 5-minute window.

## Trigger

- **Alert:** `LogAuthAnomaly`
- **Dashboard:** [Value Fabric Security](../../monitoring/grafana/dashboards/value-fabric-security.json) (if available)
- **Detection:**
  - Loki query: `sum by (layer, service) (rate({job="fluent-bit"} |~ "InvalidToken|SignatureVerification|TokenExpired|AccessDenied|RBAC.denied" [5m])) > 1`
  - Sustained for 5 minutes

## Impact

- **Severity:** P2 - Warning
- **User Impact:** Legitimate users may be locked out or experience 401/403 responses
- **Business Impact:** Support ticket surge; possible security incident if attack-driven
- **Data Impact:** None directly; indirect if automated jobs fail and retry

## Diagnosis

### 1. Characterize the Failure Pattern

```bash
# Extract failure types and their distribution
logcli query '{job="fluent-bit"} |~ "InvalidToken|SignatureVerification|TokenExpired|AccessDenied|RBAC.denied"' --since=15m --limit=500

# In Grafana Loki:
# {job="fluent-bit"} |~ "InvalidToken|SignatureVerification|TokenExpired|AccessDenied|RBAC.denied" | pattern "<_> <msg> <_>" | line_format "{{.msg}}"
```

### 2. Correlate with Metrics

```bash
# Check 401/403 HTTP rate from Prometheus
kubectl exec -n value-fabric deployment/prometheus -- \
  curl -s 'http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total{status=~"401|403"}[5m]))by(layer)'

# Check rate-limit 429s (may precede or follow auth anomalies)
kubectl exec -n value-fabric deployment/prometheus -- \
  curl -s 'http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total{status="429"}[5m]))by(layer)'
```

### 3. Identify Source IP / Tenant

```bash
# If logs contain client_ip or tenant_id, group by source
kubectl logs -n value-fabric -l app=api-gateway --since=15m | grep -iE "InvalidToken|AccessDenied" | awk -F'client_ip=' '{print $2}' | awk '{print $1}' | sort | uniq -c | sort -rn | head -10

# Check if a single tenant is disproportionately affected
kubectl logs -n value-fabric -l app=api-gateway --since=15m | grep -iE "InvalidToken|AccessDenied" | awk -F'tenant_id=' '{print $2}' | awk '{print $1}' | sort | uniq -c | sort -rn | head -10
```

### 4. Check Identity Provider Status

```bash
# Keycloak / OIDC health
kubectl exec -n value-fabric deployment/keycloak -- curl -s http://localhost:8080/health/ready

# Token introspection endpoint latency
kubectl exec -n value-fabric deployment/api-gateway -- \
  curl -w "\n%{time_total}s\n" -s -o /dev/null $KEYCLOAK_INTROSPECT_URL
```

## Resolution

| Scenario | Action |
|---|---|
| Credential stuffing / brute force | Enable WAF rate limiting; block offending IPs at ingress; check `AuthBruteforcePattern` alert |
| Mass token expiry (IdP rotation) | Notify customers to re-authenticate; verify IdP key rotation schedule |
| RBAC policy change regression | Revert the RBAC ConfigMap or policy bundle; verify with `tests/security/` suite |
| Single misconfigured client | Reach out to tenant admin; rotate the client secret if compromised |
| IdP outage or latency spike | Enable cached token validation if available; follow IdP status page |

## Escalation

1. **On-call engineer** acknowledges within 5 minutes
2. **If failure rate > 10/sec or affects > 3 tenants**, page security lead
3. **If confirmed attack pattern**, follow DDoS/incident response playbook

## Post-Incident

- Tune WAF and rate-limit thresholds if attack-driven
- Update token refresh documentation if expiry-driven
- Add regression test for the RBAC path if regression-driven
