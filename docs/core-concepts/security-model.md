---
title: "Value Fabric Security Model"
category: "core-concepts"
audience: "intermediate"
last-reviewed: "2026-04-19"
freshness: "current"
related: ["../getting-started/environment", "../how-to-guides/configure-sso", "../reference/layer1-ingestion-api", "../troubleshooting/authentication-errors", "../operations/SECURITY_HARDENING", "../explanations/adr/ADR-003-authentication-strategy", "architecture", "../reference/layer4-agents-api"]
---

# Value Fabric Security Model

> **In this guide, you will:**
> - Understand the authentication and authorization architecture
> - Learn how tenant isolation works across layers
> - Explore the audit trail and compliance mechanisms
> - See security best practices for production deployments

---

## Prerequisites

Before reading this document:

1. Complete the [Quickstart Guide](../getting-started/quickstart.md)
2. Review the [Architecture Overview](./architecture.md)
3. Familiarity with JWT, RBAC, and multi-tenant SaaS concepts

---

## Security Architecture Overview

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web Browser]
        CLI[CLI Tool]
        SDK[SDK Integration]
    end
    
    subgraph "Identity Layer"
        IDP[Identity Provider<br/>OIDC/SAML]
        JWT[JWT Issuer<br/>HS256 / RS256 / ES256 + kid]
        API_KEY[API Key Service<br/>HMAC-SHA256]
    end
    
    subgraph "Access Control"
        GW[API Gateway<br/>GovernanceMiddleware]
        RBAC[RBAC Engine<br/>6 Roles, 17 Permissions]
        TENANT[Tenant Isolation<br/>Scope Enforcement]
    end
    
    subgraph "Service Layer"
        L1[Layer 1: Ingestion]
        L2[Layer 2: Extraction]
        L3[Layer 3: Knowledge Graph]
        L4[Layer 4: Agents]
    end
    
    subgraph "Audit & Compliance"
        AUDIT[Audit Emitter<br/>Structured Events]
        DB_AUDIT[(Audit DB<br/>Append-Only)]
        LOGS[Security Logs]
    end
    
    WEB -->|OIDC/OAuth2| IDP
    CLI -->|API Key| API_KEY
    SDK -->|JWT| JWT
    
    IDP -->|Token| JWT
    JWT -->|Bearer Token| GW
    API_KEY -->|X-API-Key Header| GW
    
    GW -->|Validate + Enforce| RBAC
    RBAC -->|Tenant Check| TENANT
    
    TENANT -->|Authorized Request| L1
    TENANT -->|Authorized Request| L2
    TENANT -->|Authorized Request| L3
    TENANT -->|Authorized Request| L4
    
    L1 -->|Audit Event| AUDIT
    L2 -->|Audit Event| AUDIT
    L3 -->|Audit Event| AUDIT
    L4 -->|Audit Event| AUDIT
    
    AUDIT --> DB_AUDIT
    AUDIT --> LOGS
    
    style GW fill:#e74c3c,color:white
    style RBAC fill:#e74c3c,color:white
    style AUDIT fill:#2ecc71,color:white
    style DB_AUDIT fill:#9b59b6,color:white
```

---

## Authentication Methods

### JWT Authentication (User Sessions)

JWT tokens are used for interactive user sessions:

```http
GET /api/v1/workflows HTTP/1.1
Host: l4.valuefabric.io
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
X-Tenant-ID: 550e8400-e29b-41d4-a716-446655440000
```

**Token Structure:**

```json
{
  "header": {
    "alg": "HS256|RS256|ES256",
    "kid": "active-key-id",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user-123",
    "tenant_id": "550e8400-...",
    "roles": ["analyst", "admin"],
    "permissions": ["workflow:create", "entity:read"],
    "iat": 1713532800,
    "exp": 1713536400,
    "jti": "unique-token-id"
  }
}
```

**Token Properties:**

| Property | Value | Description |
|----------|-------|-------------|
| Algorithm | HS256 / RS256 / ES256 | Symmetric or asymmetric JWT signing |
| Key ID (`kid`) | Required | Enables active/previous key rotation and JWKS lookup |
| Expiration | 1 hour | Short-lived for security |
| Refresh | Supported | Silent refresh before expiry |
| Issuer | `value-fabric` | Fixed issuer claim |

### API Key Authentication (Service-to-Service)

API keys are used for automated integrations and service accounts:

```http
POST /api/v1/ingestion/jobs HTTP/1.1
Host: l1.valuefabric.io
X-API-Key: vf_test_dummy_550e8400e29b41d4a716446655440000
X-Tenant-ID: 550e8400-e29b-41d4-a716-446655440000
```

**API Key Format:**

```
vf_live_<64-char-hex>
vf_test_<64-char-hex>
```

**Security Properties:**

| Property | Implementation | Rationale |
|----------|---------------|-----------|
| Storage | HMAC-SHA256 hash | Fast verification (not bcrypt) |
| Prefix | `vf_live_` / `vf_test_` | Environment identification |
| Rotation | Manual or 90-day auto | Regular credential rotation |
| Rate Limit | Per-key configurable | Tenant-level throttling |

### OIDC/SAML SSO (Enterprise)

Enterprise customers can use their identity provider:

```mermaid
sequenceDiagram
    participant U as User
    participant VF as Value Fabric
    participant IDP as Okta/Azure AD
    participant S as Session
    
    U->>VF: Access /login
    VF->>IDP: Redirect to OIDC
    IDP->>U: Authenticate
    U-->>IDP: Credentials
    IDP-->>VF: Authorization Code
    VF->>IDP: Exchange for Tokens
    IDP-->>VF: ID Token + User Info
    VF->>S: Create Session (JWT)
    S-->>U: Set Cookie + Redirect
```

---

## Role-Based Access Control (RBAC)

### Role Hierarchy

```mermaid
graph BT
    ADMIN[System Admin] -->|inherits| TENANT_ADMIN[Tenant Admin]
    TENANT_ADMIN -->|inherits| ANALYST[Analyst]
    TENANT_ADMIN -->|inherits| DEVELOPER[Developer]
    ANALYST -->|inherits| VIEWER[Viewer]
    DEVELOPER -->|inherits| VIEWER
    
    style ADMIN fill:#e74c3c,color:white
    style TENANT_ADMIN fill:#e67e22,color:white
    style ANALYST fill:#2ecc71,color:white
    style DEVELOPER fill:#3498db,color:white
    style VIEWER fill:#95a5a6,color:white
```

### Roles and Permissions

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| **System Admin** | Platform administration | `tenant:create`, `user:impersonate`, `system:config` |
| **Tenant Admin** | Tenant governance | `user:manage`, `billing:view`, `workflow:admin` |
| **Analyst** | Business analysis work | `workflow:create`, `entity:read`, `report:generate` |
| **Developer** | Integration development | `api_key:manage`, `webhook:configure`, `entity:read` |
| **Viewer** | Read-only access | `entity:read`, `dashboard:view` |

### Permission Definitions

```python
# From shared/identity/permissions.py
ROLE_PERMISSIONS = {
    "system_admin": [
        "tenant:create", "tenant:delete", "tenant:config",
        "user:impersonate", "system:maintenance", "audit:full"
    ],
    "tenant_admin": [
        "user:invite", "user:manage", "role:assign",
        "billing:view", "settings:configure", "workflow:admin"
    ],
    "analyst": [
        "workflow:create", "workflow:delete_own",
        "entity:read", "entity:create",
        "report:generate", "export:data"
    ],
    "developer": [
        "api_key:create", "api_key:revoke",
        "webhook:configure", "integration:manage",
        "entity:read"
    ],
    "viewer": [
        "entity:read", "dashboard:view",
        "report:view", "workflow:view"
    ]
}
```

---

## Tenant Isolation

### Isolation Model

Value Fabric implements strict multi-tenant isolation at every layer:

```mermaid
graph LR
    subgraph "Tenant A Scope"
        A_DATA[(Tenant A Data)]
        A_CACHE[Cache: tenant:a:*]
        A_QUEUE[Queue: jobs:a:*]
    end
    
    subgraph "Tenant B Scope"
        B_DATA[(Tenant B Data)]
        B_CACHE[Cache: tenant:b:*]
        B_QUEUE[Queue: jobs:b:*]
    end
    
    GW[API Gateway] -->|X-Tenant-ID: a| A_DATA
    GW -->|X-Tenant-ID: b| B_DATA
    
    style GW fill:#e74c3c,color:white
    style A_DATA fill:#4a90d9,color:white
    style B_DATA fill:#2ecc71,color:white
```

### Isolation Mechanisms

| Layer | Mechanism | Implementation |
|-------|-----------|----------------|
| **API** | Header validation | `X-Tenant-ID` required, verified against JWT |
| **Database** | Row-level security | PostgreSQL RLS policies, `tenant_id` column |
| **Graph** | Label partitioning + validated tenant session | Neo4j tenant labels, `TenantScopedCypher`, and Layer 3 approved dependency `services/layer3-knowledge/src/api/dependencies_tenant_secured.py` (legacy shim `dependencies_tenant.py` removal date: 2026-09-30) |
| **Cache** | Key prefixing | Redis keys prefixed with `tenant:{id}:` |
| **Queue** | Queue namespacing | Job queues isolated per tenant |
| **Storage** | Path prefixing | S3 paths include tenant prefix |

### Cross-Tenant Access Prevention

```python
# Example: Tenant isolation in query
class TenantScopedQuery:
    def execute(self, query, tenant_id):
        # All queries MUST include tenant filter
        if "tenant_id" not in query:
            raise SecurityError("Missing tenant isolation")
        
        # Verify tenant matches authenticated context
        if tenant_id != get_current_tenant():
            raise ForbiddenError("Cross-tenant access denied")
        
        return db.execute(query, tenant_id=tenant_id)
```

---

## Audit Trail

### Audit Event Structure

Every security-relevant action generates an audit event:

```json
{
  "event_id": "audit-660e8400-...",
  "timestamp": "2025-01-01T00:00:00Z",
  "action": "workflow:create",
  "actor": {
    "type": "user",
    "id": "user-123",
    "tenant_id": "550e8400-..."
  },
  "resource": {
    "type": "workflow",
    "id": "wf-770e8400-..."
  },
  "context": {
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "request_id": "req-880e8400-..."
  },
  "result": "success",
  "changes": {
    "before": null,
    "after": {"status": "created"}
  }
}
```

### Audit Actions

| Category | Actions | Retention |
|----------|---------|-----------|
| **Authentication** | `login`, `logout`, `token:refresh`, `token:revoke` | 1 year |
| **Authorization** | `access:denied`, `permission:elevated` | 2 years |
| **Data Access** | `entity:read`, `entity:create`, `entity:update`, `entity:delete` | 90 days |
| **Workflow** | `workflow:create`, `workflow:pause`, `workflow:resume` | 1 year |
| **Admin** | `user:invite`, `role:assign`, `api_key:create` | 2 years |

### Append-Only Guarantee

```sql
-- Database trigger prevents modification
CREATE TRIGGER prevent_audit_modification
BEFORE UPDATE OR DELETE ON audit_events
FOR EACH ROW
BEGIN
    RAISE EXCEPTION 'Audit events are immutable';
END;
```

---

## Security Best Practices

### Secrets Management

| Secret Type | Storage | Rotation |
|-------------|---------|----------|
| API Keys | Infisical / HashiCorp Vault | 90 days |
| JWT Secret | Environment variable | 180 days |
| Database passwords | Vault dynamic credentials | 24 hours |
| LLM API keys | Infisical with usage monitoring | 90 days |

### Network Security

```mermaid
graph TB
    subgraph "Public Zone"
        CDN[CDN/WAF]
    end
    
    subgraph "DMZ"
        LB[Load Balancer<br/>SSL Termination]
        GW[API Gateway<br/>Rate Limiting]
    end
    
    subgraph "Private Zone"
        SVC[Services L1-L4]
        DB[(Databases)]
    end
    
    subgraph "Secure Zone"
        VAULT[HashiCorp Vault]
    end
    
    CDN -->|HTTPS| LB
    LB -->|mTLS| GW
    GW -->|Internal mTLS| SVC
    SVC -->|TLS + Auth| DB
    SVC -->|Vault Agent| VAULT
    
    style GW fill:#e74c3c,color:white
    style VAULT fill:#9b59b6,color:white
```

### Production Checklist

- [ ] JWT_SECRET changed from default/changeme
- [ ] All secrets in Vault/Infisical (not in code)
- [ ] Audit logging enabled
- [ ] Rate limiting configured
- [ ] mTLS between services
- [ ] Database encryption at rest
- [ ] Backup encryption
- [ ] Security headers configured
- [ ] WAF rules active
- [ ] Penetration testing completed

---

## Troubleshooting Security Issues

### Authentication Failures

**Symptom:** `401 Unauthorized` errors

**Diagnostic Steps:**

```bash
# Check JWT validity
echo $JWT | jq -R 'split(".") | .[1] | @base64d | fromjson'

# Verify expiration
date -d @$(echo $JWT | jq -r '.exp')  # Unix timestamp

# Check tenant context
curl -H "Authorization: Bearer $JWT" \
  https://l4.valuefabric.io/api/v1/auth/validate
```

**Common Causes:**
- Expired token (1 hour TTL)
- Wrong tenant ID in header
- JWT secret mismatch
- Clock skew between services

### Authorization Denied

**Symptom:** `403 Forbidden` errors

**Resolution:**
- Verify user role has required permission
- Check tenant isolation boundaries
- Review recent role changes
- Inspect audit logs for context

---

## Compliance

### Supported Standards

| Standard | Implementation | Status |
|----------|---------------|--------|
| **SOC 2 Type II** | Audit controls, access logs | In Progress |
| **GDPR** | Data retention, deletion, export | Implemented |
| **CCPA** | Consumer privacy rights | Implemented |
| **HIPAA** | PHI handling (optional add-on) | Available |

### Data Residency

- **Default:** US-East (AWS/GCP/Azure)
- **EU:** EU-West (GDPR-compliant)
- **Enterprise:** Custom region configuration

---

## Threat Model

This section describes security threats using STRIDE and LINDDUN methodologies.

### STRIDE Analysis

#### S - Spoofing (Identity)

| Threat | Description | Mitigation | Status |
|--------|-------------|------------|--------|
| **T1.1** | Attacker spoofs OIDC identity | JWT validation with JWKS, short TTL (15 min) | ✅ Implemented |
| **T1.2** | Attacker steals session token | HttpOnly cookies, CSRF protection, token rotation | ✅ Implemented |
| **T1.3** | Attacker impersonates service | mTLS between services, service account tokens | ⚠️ Partial (K8s only) |
| **T1.4** | Attacker forges webhook calls | HMAC-SHA256 signatures, timestamp validation | ✅ Implemented |

#### T - Tampering

| Threat | Description | Mitigation | Status |
|--------|-------------|------------|--------|
| **T2.1** | Request/response tampering in transit | TLS 1.3 everywhere, certificate pinning | ✅ Implemented |
| **T2.2** | Data tampering at rest | Fernet (AES-128-CBC + HMAC-SHA256) for Layer 4 credentials, plus database-level encryption at rest | ✅ Implemented |
| **T2.3** | Audit log tampering | Append-only logs, DB trigger enforcement, WORM storage | ✅ Implemented |
| **T2.4** | Build artifact tampering | Signed containers (Cosign), SBOM verification | 🔄 In Progress |
| **T2.5** | Configuration tampering | GitOps, drift detection, signed configs | 🔄 In Progress |

#### R - Repudiation

| Threat | Description | Mitigation | Status |
|--------|-------------|------------|--------|
| **T3.1** | User denies action | Immutable audit logs with user ID, timestamp, IP | ✅ Implemented |
| **T3.2** | Admin denies configuration change | Git commit history, signed commits, CODEOWNERS | ✅ Implemented |
| **T3.3** | System denies processing | Structured logging with trace IDs, request correlation | ✅ Implemented |

#### I - Information Disclosure

| Threat | Description | Mitigation | Status |
|--------|-------------|------------|--------|
| **T4.1** | Sensitive data in logs | PII classification, redaction at source, log filtering | ✅ Implemented |
| **T4.2** | Error messages leak internals | Generic error messages, detailed logs internal only | ✅ Implemented |
| **T4.3** | Tenant data leakage | Row-level security, tenant ID validation on every query | ✅ Implemented |
| **T4.4** | Secrets in repository | Gitleaks pre-commit, CI secrets scanning | ✅ Implemented |
| **T4.5** | Cache side-channel | Cache isolation by tenant, constant-time comparisons | ⚠️ Partial |

#### D - Denial of Service

| Threat | Description | Mitigation | Status |
|--------|-------------|------------|--------|
| **T5.1** | API rate limit abuse | Tiered rate limits (auth: 5/min, API: 100/min) | ✅ Implemented |
| **T5.2** | Resource exhaustion | Resource quotas, autoscaling, circuit breakers | ✅ Implemented |
| **T5.3** | Graph query complexity | Query depth limits, timeout enforcement, cost analysis | ✅ Implemented |
| **T5.4** | LLM token flooding | Token budget per request, concurrent request limits | ✅ Implemented |
| **T5.5** | Large payload attacks | Request size limits (10MB), streaming for large data | ✅ Implemented |

#### E - Elevation of Privilege

| Threat | Description | Mitigation | Status |
|--------|-------------|------------|--------|
| **T6.1** | Horizontal privilege escalation | Tenant isolation middleware, row-level security | ✅ Implemented |
| **T6.2** | Vertical privilege escalation | RBAC enforcement, role validation on every endpoint | ✅ Implemented |
| **T6.3** | Service account abuse | Least-privilege IAM, workload identity, short-lived tokens | ⚠️ Partial |
| **T6.4** | Container escape | Distroless images, non-root user, restricted capabilities | 🔄 In Progress |

### Attack Scenarios

#### Scenario 1: Cross-Tenant Data Access

**Attacker**: Tenant A user tries to access Tenant B data  
**Vector**: Modified request with spoofed tenant ID header  
**Mitigation**:
1. JWT contains tenant claim (immutable)
2. Every query includes `WHERE tenant_id = :jwt_tenant_id`
3. RLS policies enforced at database level  
**Test**: `tests/security/test_tenant_isolation.py`

#### Scenario 2: Privilege Escalation

**Attacker**: Standard user tries admin operations  
**Vector**: Modified JWT role claim, or direct API call to admin endpoints  
**Mitigation**:
1. RBAC middleware validates role on every request
2. Admin endpoints require `role=admin` in JWT
3. Role changes require re-authentication  
**Test**: `tests/security/test_rbac.py`

#### Scenario 3: Injection Attacks

**Attacker**: SQL/NoSQL/XSS injection via input fields  
**Vector**: Malicious input in graph queries or entity creation  
**Mitigation**:
1. SecurityMiddleware with pattern detection
2. Parameterized queries only
3. Input sanitization, HTML escaping  
**Test**: `tests/security/test_injection.py`

#### Scenario 4: Supply Chain Poisoning

**Attacker**: Compromised dependency or build process  
**Vector**: Malicious package version, tampered container  
**Mitigation**:
1. Pinned dependencies (lockfiles)
2. Signed containers (Cosign)
3. SBOM verification
4. Admission controller blocks unsigned images  
**Test**: `tests/security/test_supply_chain.py`

---

## Next Steps

- [Configure SSO](../how-to-guides/configure-sso.md) — OIDC/SAML setup
- [Authentication Errors](../troubleshooting/authentication-errors.md) — Debug issues
- [Security Hardening](../operations/SECURITY_HARDENING.md) — Production hardening
- [API Authentication](./layer1-ingestion-api.md) — Authenticating API calls

---

*Last updated: 2026-04-27 | [Edit this page](https://github.com/bmsull560/Fabric_4L/edit/main/docs/core-concepts/security-model.md)*

## JWT Algorithm Migration and Rollback

1. Set `JWT_ACTIVE_KID` and keep current key as `JWT_PREVIOUS_KID` for overlap.
2. For HS256 rotation, set `JWT_PREVIOUS_SECRET` during the overlap window.
3. For RS256/ES256 migration, set `JWT_PRIVATE_KEY_PEM`, `JWT_PUBLIC_KEY_PEM`, and `JWT_PREVIOUS_PUBLIC_KEY_PEM`.
4. Publish the new public keys via JWKS (`shared.identity.jwt.get_jwks`) before switching issuers.
5. After token TTL + skew has elapsed, remove previous key env vars.

**Rollback:** restore prior active key material, swap `JWT_ACTIVE_KID` back to the previous value, and keep both keys published until newly issued tokens expire.
