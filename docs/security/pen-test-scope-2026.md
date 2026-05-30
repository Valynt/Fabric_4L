# Fabric 4L External Penetration Test Scope — 2026

**Document owner:** Security Engineering  
**Review status:** Security-team reviewed baseline for the 2026 external penetration test engagement.  
**Target environment:** Staging only, unless Security Engineering grants written approval for a narrower production validation.  
**Rules of engagement:** Testers must remain inside the authorized test tenant, avoid destructive testing, preserve evidence, and immediately report suspected cross-tenant exposure, credential leakage, or production-impacting behavior through the escalation contacts in this document.

## Section 1: In-Scope

The following systems and behaviors are authorized for assessment in the staging environment.

### 1.1 API surface

All HTTP methods and paths defined in `contracts/openapi/fabric-4l-api.json` are in scope. The endpoint inventory below is the canonical API scope for this engagement.

| Methods | Path |
|---|---|
| `GET` | `/ready` |
| `GET, POST` | `/v1/accounts` |
| `GET, PATCH` | `/v1/accounts/{account_id}` |
| `GET` | `/v1/accounts/{account_id}/summary` |
| `POST, DELETE` | `/v1/accounts/{account_id}/share` |
| `GET` | `/v1/accounts/{account_id}/signals` |
| `POST` | `/v1/accounts/{account_id}/signals/extract` |
| `GET` | `/v1/accounts/{account_id}/stakeholders` |
| `GET` | `/v1/accounts/{account_id}/ontology-match` |
| `GET` | `/v1/accounts/{account_id}/enrichment` |
| `GET` | `/v1/intelligence/account/{account_id}/signals` |
| `POST` | `/v1/intelligence/account/{account_id}/signals/extract` |
| `GET` | `/v1/intelligence/account/{account_id}/stakeholders` |
| `GET` | `/v1/intelligence/account/{account_id}/ontology-match` |
| `GET` | `/v1/intelligence/account/{account_id}/enrichment` |
| `GET` | `/v1/accounts/{account_id}/hypotheses` |
| `POST` | `/v1/accounts/{account_id}/hypotheses/generate` |
| `PATCH` | `/v1/accounts/{account_id}/hypotheses/{hypothesis_id}` |
| `GET` | `/v1/accounts/{account_id}/drivers` |
| `GET` | `/v1/accounts/{account_id}/value-tree` |
| `POST` | `/v1/accounts/{account_id}/drivers/generate` |
| `PATCH` | `/v1/accounts/{account_id}/drivers/{driver_id}` |
| `GET` | `/v1/accounts/{account_id}/evidence` |
| `POST` | `/v1/accounts/{account_id}/evidence/match` |
| `GET` | `/v1/accounts/{account_id}/evidence/{evidence_id}` |
| `POST` | `/v1/accounts/{account_id}/evidence/{evidence_id}/pii-scan` |
| `GET, POST` | `/v1/accounts/{account_id}/scenarios` |
| `POST` | `/v1/accounts/{account_id}/roi/calculate` |
| `GET` | `/v1/accounts/{account_id}/roi-calculations/{calculation_id}` |
| `GET` | `/v1/accounts/{account_id}/value-case` |
| `POST` | `/v1/accounts/{account_id}/value-case/generate` |
| `PATCH` | `/v1/accounts/{account_id}/value-cases/{value_case_id}` |
| `GET` | `/v1/accounts/{account_id}/gates` |
| `POST` | `/v1/accounts/{account_id}/value-case/{value_case_id}/export` |
| `GET` | `/v1/context-engine/value-packs` |
| `GET` | `/v1/context-engine/value-packs/{value_pack_id}` |
| `GET` | `/v1/context-engine/formulas` |
| `GET` | `/v1/context-engine/formulas/{formula_id}` |
| `GET` | `/v1/context-engine/benchmarks` |
| `GET` | `/v1/context-engine/ontology` |
| `GET` | `/v1/governance/review-queue` |
| `POST` | `/v1/governance/review-decisions` |
| `GET` | `/v1/governance/prod-gates` |
| `GET` | `/v1/governance/audit-log` |
| `POST, GET` | `/v1/accounts/{account_id}/reviews` |
| `GET, PATCH` | `/v1/accounts/{account_id}/reviews/{review_id}` |
| `POST, GET` | `/v1/accounts/{account_id}/reviews/{review_id}/comments` |
| `POST, GET` | `/v1/accounts/{account_id}/snapshots` |
| `GET` | `/v1/accounts/{account_id}/snapshots/{snapshot_id}` |
| `POST` | `/v1/accounts/{account_id}/snapshots/{snapshot_id}/diff` |
| `POST` | `/v1/accounts/{account_id}/snapshots/{snapshot_id}/restore` |
| `POST, GET` | `/v1/accounts/{account_id}/realization-plans` |
| `PATCH` | `/v1/accounts/{account_id}/realization-plans/{plan_id}/actuals` |
| `GET` | `/v1/accounts/{account_id}/realization-plans/{plan_id}/variance` |
| `GET` | `/v1/accounts/{account_id}/realization-plans/{plan_id}/recommendations` |
| `POST` | `/v1/agents/runs` |
| `GET` | `/v1/agents/runs/{run_id}` |
| `POST` | `/v1/agents/runs/{run_id}/resume` |
| `POST` | `/v1/agents/runs/{run_id}/cancel` |
| `POST` | `/v1/agents/workflows` |
| `GET` | `/v1/agents/workflows/active` |
| `GET, DELETE` | `/v1/agents/workflows/{id}` |
| `POST` | `/v1/agents/workflows/{id}/pause` |
| `POST` | `/v1/agents/workflows/{id}/resume` |
| `GET` | `/v1/agents/workflows/{id}/events` |
| `POST` | `/v1/privacy/dsar` |
| `GET` | `/v1/privacy/dsar/{request_id}` |
| `GET` | `/v1/privacy/dsar/packages/{package_id}/download` |
| `POST` | `/internal/webhooks/clerk` |
| `GET` | `/health` |
| `GET` | `/metrics` |

### 1.2 Web application

The React/Vite web application under `apps/web/` is in scope, including:

- Authentication and organization-selection screens.
- Tenant-scoped navigation, pages, state transitions, and API calls.
- Client-side access control, route guards, token handling, storage behavior, and browser security headers as observed through the deployed staging site.
- File download user journeys and any UI workflows that trigger API file generation, export, import, or download actions.

### 1.3 Authentication and authorization flows

The following identity and access flows are in scope:

- Clerk JWT issuance, session handling, token forwarding to backend APIs, organization/tenant binding, expiry, and replay resistance.
- Keycloak OIDC compatibility and legacy service-to-service authentication where enabled in staging.
- API key authentication, including key format validation, rate limiting, tenant binding, revocation behavior, and audit logging.
- RBAC, admin, and super-admin authorization boundaries.
- Negative tests for missing tokens, expired tokens, malformed tokens, wrong tenant claims, wrong organization claims, and privilege escalation attempts.

### 1.4 Tenant isolation mechanisms

Tenant isolation is explicitly in scope across API, UI, storage, workflow, audit, and export paths. Testers should assess:

- Cross-tenant read/write protections for account, evidence, value-case, review, snapshot, realization-plan, agent-run, DSAR, and governance resources.
- Direct-object-reference resistance for path parameters such as `account_id`, `evidence_id`, `review_id`, `snapshot_id`, `run_id`, `package_id`, and workflow IDs.
- Enforcement that authenticated tenant context overrides any tenant value supplied in request bodies, query strings, headers, or client-side state.
- Isolation of audit logs, metrics exposure, generated artifacts, and downloaded packages.

### 1.5 File upload and download endpoints

File and artifact handling is in scope, including:

- DSAR package download: `GET /v1/privacy/dsar/packages/{package_id}/download`.
- Value-case export: `POST /v1/accounts/{account_id}/value-case/{value_case_id}/export`.
- Any staging UI path that accepts, generates, previews, exports, or downloads files through the web application.
- Content-type validation, content disposition, path traversal, unsafe file names, authorization checks, malware-safe handling assumptions, size limits, and tenant isolation for generated artifacts.

### 1.6 Webhook endpoints

Webhook integration points are in scope, including signature verification, replay resistance, event authorization, idempotency, IP/header trust assumptions, error behavior, and log redaction.

- Clerk webhook endpoint in the unified API: `POST /internal/webhooks/clerk`.
- Stripe billing webhook integration point: `POST /v1/billing/webhook` when routed in staging through the Layer 4 billing service or Layer 7 billing service.
- CRM webhook routes may be tested only when Security Engineering adds them to the written engagement addendum; they are not required for this 2026 scope.

### 1.7 Admin and super-admin endpoints

Administrative capabilities are in scope wherever exposed through the staging UI or API, including:

- Governance queues, review decisions, production gates, and audit-log access.
- Account sharing, restore, cancellation, resume, workflow control, and other privileged state-changing operations.
- Super-admin or internal roles used for tenant management, tenant provisioning, support operations, or emergency access.

## Section 2: Out-of-Scope

The following activities are not authorized under this penetration test unless a separate written addendum is approved by Security Engineering.

- Infrastructure-level denial-of-service, volumetric DDoS, stress testing, resource exhaustion, or cloud-provider control-plane testing.
- Physical security testing, office access attempts, hardware attacks, badge cloning, or device theft scenarios.
- Social engineering, phishing, vishing, smishing, pretexting, or attempts to obtain credentials from employees, customers, vendors, or support channels.
- Direct testing of third-party services operated by Clerk, Stripe, OpenAI, Infisical, cloud providers, or other vendors. Fabric 4L API integration points with those services remain in scope.
- Mobile application testing, because Fabric 4L does not currently provide mobile applications.
- Testing against production customer tenants, production data, employee accounts, or vendor-managed dashboards.
- Destructive persistence, ransomware simulation, cryptomining, data exfiltration beyond minimum proof-of-concept evidence, or modifications that cannot be cleanly reverted.
- Attempts to bypass rate limits through botnets, residential proxy networks, credential stuffing lists, or leaked credentials.

## Section 3: Test Credentials

Security Engineering provisions all credentials in an isolated staging tenant. Testers must not create additional accounts, invite external users, or reuse these credentials outside the engagement window.

| Item | Value |
|---|---|
| Staging web URL | `https://staging.valuepact.ai` |
| Staging API base URL | `https://staging.valuepact.ai` |
| Test tenant name | `VF-PENTEST-2026-READONLY` |
| Test tenant ID | `tenant_pentest_2026_readonly` |
| Read-only user | `pentest-readonly@staging.valuepact.ai` |
| Read-only role | `org:auditor` / read-only tenant member |
| Read-only password delivery | Secret value delivered through the approved vault path `Infisical:/security/pen-test/2026/PENTEST_READONLY_PASSWORD` and a separate out-of-band unlock message from Security Engineering. |
| API key alias | `vfpk_stg_pentest_2026_rate_limited` |
| API key tenant binding | `tenant_pentest_2026_readonly` only |
| API key permissions | Read-only endpoints plus explicitly approved webhook-signature negative testing; no production access. |
| API key rate limit | 60 requests per minute and 5,000 requests per day, isolated from customer tenants. |
| API key delivery | Secret value delivered through `Infisical:/security/pen-test/2026/PENTEST_API_KEY`. |
| Clerk webhook test URL | `https://staging.valuepact.ai/internal/webhooks/clerk` |
| Clerk webhook secret delivery | `Infisical:/security/pen-test/2026/CLERK_WEBHOOK_TEST_SECRET` for signature-generation tests only. |
| Stripe webhook test URL | `https://staging.valuepact.ai/v1/billing/webhook` |
| Stripe webhook secret delivery | `Infisical:/security/pen-test/2026/STRIPE_WEBHOOK_TEST_SECRET` for signature-generation tests only. |
| Support ticket queue | `SEC-PENTEST-2026` in the security issue tracker. |

Credential handling requirements:

1. Treat all staging secrets as confidential even when rate limited or tenant isolated.
2. Store generated tokens, HAR files, request logs, screenshots, and proof-of-concept payloads in the encrypted evidence workspace supplied by Security Engineering.
3. Do not paste bearer tokens, API keys, session cookies, webhook secrets, or raw JWTs into the final report; include redacted prefixes and enough metadata to reproduce the finding.
4. Report lost credentials immediately to `security@valuepact.ai` and the `#security-incidents` channel so keys can be revoked and reissued.

## Section 4: Known Limitations

### 4.1 Known issues from previous audits

No unresolved CRITICAL or HIGH security exception is approved as accepted risk for this test baseline. Prior audit artifacts that testers should review for regression context include:

- `docs/archive/2026-05-28/tenant-management-security-audit.json` for tenant-management regression history.
- `docs/archive/2026-05-28/layer3-tenant-isolation-audit.md` for graph and retrieval isolation history.
- `docs/archive/2026-05-28/auth-tenant-todo-audit-2026-05-12.md` for authentication and tenant-context follow-up history.
- `docs/archive/2026-04-27/ARCHIVED_SECURITY_AUDIT_REPORT.md` and `docs/archive/2026-04-27/ARCHIVED_ADVERSARIAL_SECURITY_AUDIT.md` for historical adversarial-test context.
- `services/layer4-agents/tests/BILLING_SECURITY_AUDIT_COMPLETE.md` for Stripe webhook and billing-security hardening context.

Rediscovery of a historical issue should be reported as a new finding if it is exploitable in staging, affects the current API contract, or demonstrates an incomplete remediation.

### 4.2 WAF, rate limiting, and security controls

The staging environment may enforce the following controls that can affect testing:

- Web application firewall managed rules for SQL injection, cross-site scripting, local/remote file inclusion, request smuggling indicators, command injection strings, and known scanner signatures.
- Request-size limits for JSON bodies, uploads, generated exports, and multipart requests.
- Per-IP, per-session, per-tenant, and per-API-key rate limits.
- Stripe webhook IP allowlisting when the Stripe route is exercised through the billing service.
- Clerk and Stripe signature checks that intentionally reject unsigned, stale, malformed, or replayed webhook events.
- Bot and automation heuristics on authentication routes.
- Audit logging, anomaly detection, and alerting for repeated authorization failures or cross-tenant probes.

These controls are part of the assessment. If a control blocks test coverage, testers should request a temporary allowlist rather than bypassing with unauthorized infrastructure.

### 4.3 Allowlist and escalation contacts

| Need | Contact | Expected response |
|---|---|---|
| Temporary source-IP allowlist | `security@valuepact.ai` with subject `SEC-PENTEST-2026 allowlist request` | Same business day during the approved test window |
| Active test coordination | `#security-incidents` for urgent issues and `SEC-PENTEST-2026` tracker for normal requests | 15 minutes for suspected CRITICAL/HIGH, 1 business day for routine requests |
| Credential reset or revocation | `security@valuepact.ai` and `#security-incidents` | 30 minutes during the approved test window |
| Suspected cross-tenant exposure | Immediately page Security Engineering through `#security-incidents` and stop that test path | Immediate acknowledgement target: 15 minutes |

Whitelist requests must include source CIDR blocks, tester name, company, requested dates/times in UTC, test objective, expected request volume, and confirmation that testing remains limited to the staging tenant.

## Section 5: Success Criteria

The engagement is considered successful when all of the following conditions are met:

1. **Zero CRITICAL findings** remain open at report delivery.
2. **All HIGH findings** have an owner, ticket, containment decision, and remediation plan within 48 hours of validation by Security Engineering.
3. **All MEDIUM findings** are tracked with severity-appropriate remediation SLAs, owners, and target dates.
4. All LOW and informational findings are triaged for risk acceptance, backlog tracking, or remediation.
5. All findings include CVSS scoring, business impact, affected endpoint or UI route, reproduction steps, evidence, exploit preconditions, and recommended remediation.
6. Any suspected tenant-isolation, authentication-bypass, credential-exposure, or data-exfiltration issue is escalated immediately and not held until final report delivery.
7. Evidence is delivered securely, secrets are redacted, and no test artifacts remain accessible in the staging tenant beyond the agreed retention period.

## Section 6: Reporting Template

Testers must use the following structure for the final report and for any interim CRITICAL or HIGH finding notification.

```markdown
# Fabric 4L External Penetration Test Report — 2026

## Executive Summary

- Assessment dates:
- Testing company:
- Lead tester:
- Fabric 4L engagement owner:
- Environment tested:
- Overall risk rating:
- Summary of CRITICAL/HIGH/MEDIUM/LOW/Informational findings:

## Scope Confirmation

- In-scope systems tested:
- In-scope systems not tested and reason:
- Out-of-scope systems observed but not tested:
- Source IPs used:
- Test accounts used:
- Tools used:

## Methodology

- Reconnaissance approach:
- Authentication and authorization testing approach:
- Tenant-isolation testing approach:
- API testing approach:
- Web application testing approach:
- Webhook testing approach:
- File handling testing approach:
- Limitations encountered:

## Finding Summary

| ID | Title | Severity | CVSS v3.1/vector | Affected asset | Status |
|---|---|---:|---|---|---|
| F-001 | Example title | HIGH | 8.1 / AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N | `/example` | Open |

## Detailed Findings

### F-001: Finding title

- **Severity:** CRITICAL / HIGH / MEDIUM / LOW / Informational
- **CVSS score and vector:**
- **Affected endpoint, UI route, or component:**
- **Affected tenant or role:**
- **Finding type:** Authentication / Authorization / Tenant Isolation / Injection / File Handling / Webhook / Session Management / Configuration / Other
- **Description:**
- **Business impact:**
- **Technical impact:**
- **Exploit preconditions:**
- **Proof of concept:** Include exact HTTP requests, UI steps, payloads, or scripts needed to reproduce. Redact secrets.
- **Evidence:** Screenshots, sanitized response snippets, timestamps, request IDs, trace IDs, audit IDs, or logs.
- **Recommended remediation:**
- **References:** CWE, OWASP ASVS, OWASP Top 10, or vendor guidance.
- **Retest guidance:**

## Positive Security Observations

- Control observed:
- Evidence:

## Appendix A: Evidence Inventory

| Evidence ID | Finding ID | File name | Hash | Description |
|---|---|---|---|---|

## Appendix B: Retest Results

| Finding ID | Retest date | Result | Evidence | Notes |
|---|---|---|---|---|
```

Reporting requirements:

- Provide CVSS v3.1 scoring and full vector strings for all findings, including LOW and informational findings where applicable.
- Provide a proof-of-concept for every finding. If a proof-of-concept would be destructive or expose another tenant's data, stop at the minimum safe evidence and coordinate with Security Engineering.
- Include affected endpoints, HTTP methods, roles, tenants, request IDs, timestamps, and sanitized payloads.
- Redact all secrets, tokens, cookies, API keys, webhook signatures, customer data, and personal data.
- Deliver the report and evidence through the approved encrypted evidence workspace, not email attachments.
