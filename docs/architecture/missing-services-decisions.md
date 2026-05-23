# Missing Services Decision Document

**Purpose**: Convert the missing-services audit into a decision-ready roadmap for Fabric_4L production hardening.

**Created**: 2026-05-23
**Status**: Draft - Proposed Recommendations

---

## Decision Summary

| Decision ID | Finding ID | Status | Priority |
|-------------|------------|--------|----------|
| DEC-001 | MS-INFRA-001 | Proposed | P0 |
| DEC-002 | MS-APP-001 | Needs Confirmation | P0 |
| DEC-003 | MS-APP-002 | Proposed Conditional | P0 |
| DEC-004 | MS-INFRA-003 | Proposed | P0 |
| DEC-005 | MS-INFRA-005 | Proposed | P0 |
| DEC-006 | MS-PR-003 | Proposed | P0 |
| DEC-007 | MS-PR-001 | Deferred | P1 |
| DEC-008 | MS-PR-002 | Decision Required | P1 |
| DEC-009 | MS-PR-004 | Decision Required | P1 |
| DEC-010 | MS-PR-005 | Proposed | P1 |
| DEC-011 | MS-PR-006 | Deferred | P2 |
| DEC-012 | MS-PR-009 | Deferred | P2 |
| DEC-013 | MS-PR-010 | Proposed | P2 |

---

## Detailed Decisions

### DEC-001: Secrets Management Strategy

**Related Finding**: MS-INFRA-001

**Current State**:
- Vault dev mode exists in `docker-compose.full.yml` (dev profile only)
- ExternalSecrets Operator manifests exist in `k8s/external-secrets/`
- ClusterSecretStore configured for Vault integration
- No production Vault HA deployment

**Decision Required**: Choose between Vault HA (self-managed) vs external managed secrets (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager)

**Options**:
1. **Vault HA (self-managed)**: Full control, higher operational overhead, requires auto-unseal setup
2. **External managed secrets**: Lower ops, vendor lock-in, potential egress costs
3. **Hybrid**: Vault for dev/staging, external managed for production

**Recommended Default**: Use Vault + ExternalSecrets for now because repo already has Vault integration, but document external managed secrets as an acceptable future production alternative.

**Rationale**:
- Existing Vault integration reduces immediate implementation effort
- ExternalSecrets Operator provides abstraction layer for future migration
- Production Vault HA can be deployed later without service changes
- External managed secrets add cost and egress latency

**Risks/Trade-offs**:
- Vault HA requires operational expertise (auto-unseal, backup, disaster recovery)
- Self-managed Vault has higher security burden (patching, access control)
- External managed secrets introduce vendor dependency

**Dependencies**:
- DEC-004 (Auth provider) may influence secrets strategy
- Production infrastructure team capacity

**Implementation Impact**:
- Deploy Vault HA cluster (3+ nodes, Raft backend)
- Configure auto-unseal (AWS KMS, Azure Key Vault, or GCP KMS)
- Update ClusterSecretStore to point to production Vault
- Migrate dev Vault secrets to production Vault
- Add Vault backup and restore procedures

**Priority**: P0 (Security/Production Readiness)

**Owner**: TBD (Infrastructure/Security)

**Decision Status**: Proposed

---

### DEC-002: API Gateway Role

**Related Finding**: MS-APP-001

**Current State**:
- `services/api/` directory exists with shared API gateway code
- Not deployed in production compose files
- Not included in K8s base manifests
- Individual services expose ports directly

**Decision Required**: Determine if `services/api/` should be a production ingress gateway or just a shared library

**Options**:
1. **Deploy as API gateway**: nginx/Envoy for rate limiting, auth, routing, unified ingress
2. **Keep as library only**: Use cloud-native ingress (Istio/Gateway API/NGINX Ingress)
3. **Internal gateway only**: Service-to-service routing, external ingress handled separately

**Recommended Default**: Do not make services/api a production ingress gateway yet. Prefer cloud-native ingress/Gateway API/NGINX/Istio for ingress, and treat services/api as either a shared API surface or internal gateway only after confirmation.

**Rationale**:
- Cloud-native ingress is standard pattern in Kubernetes
- Reduces operational burden (managed ingress controllers)
- Avoids introducing another moving part before production validation
- Services/api can be evolved into internal gateway if needed

**Risks/Trade-offs**:
- No unified rate limiting at gateway level (must be per-service)
- No centralized auth enforcement (must be per-service middleware)
- Potential inconsistency in API surface across services

**Dependencies**:
- Production ingress controller selection (Istio vs NGINX vs Gateway API)
- DEC-004 (Auth provider) for gateway auth integration

**Implementation Impact**:
- If deployed as gateway: Add to production compose, K8s manifests, configure routing
- If library only: Document usage patterns, add to shared dependencies
- If internal gateway: Service mesh or internal load balancer configuration

**Priority**: P0 (Architecture/Production Readiness)

**Owner**: TBD (Architecture/Platform)

**Decision Status**: Needs Confirmation

---

### DEC-003: Layer 2.5 Signal Refinery Production Status

**Related Finding**: MS-APP-002

**Current State**:
- `services/layer2-5-signal-refinery/` exists with code
- Only in `docker-compose.dev.yml` (port 8007)
- Not in `docker-compose.full.yml` or `docker-compose.prod.yml`
- No K8s manifests
- No OpenAPI spec in `contracts/openapi/`

**Decision Required**: Include in production stack or keep as experimental

**Options**:
1. **Production-candidate**: Include in production stack after readiness checks
2. **Experimental**: Keep as dev-only, evaluate for future inclusion
3. **Decommission**: Remove if not architecturally aligned

**Recommended Default**: Treat as architecturally intentional and production-candidate, but gate production inclusion on readiness checks, health endpoint, metrics, contract coverage, and dependency wiring.

**Rationale**:
- Service exists with meaningful code, likely intentional
- Signal refinement is valuable capability in data pipeline
- Gating on readiness checks ensures production quality
- Allows time to validate dependencies and performance

**Risks/Trade-offs**:
- Additional operational overhead if included
- May have unknown dependencies on L1/L2/L3
- Resource requirements not yet characterized
- Potential performance impact on downstream services

**Dependencies**:
- Health endpoint implementation
- Metrics instrumentation
- OpenAPI contract generation
- Dependency validation (L1, L2, L3, L4 connectivity)
- Resource profiling (CPU, memory, latency)

**Implementation Impact**:
- Add to `docker-compose.full.yml` and `docker-compose.prod.yml`
- Create K8s deployment manifests
- Generate OpenAPI spec
- Add to monitoring and alerting
- Configure service discovery

**Priority**: P0 (Architecture/Production Readiness)

**Owner**: TBD (Layer 2 Team / Architecture)

**Decision Status**: Proposed Conditional

---

### DEC-004: Auth Provider Strategy

**Related Finding**: MS-INFRA-003

**Current State**:
- Keycloak manifests exist in `infra/keycloak/`
- Keycloak in dev compose (`docker-compose.dev.yml`)
- JWT authentication implemented in services
- OIDC callback endpoints exist
- No production IdP configured

**Decision Required**: Choose between self-hosted Keycloak vs external managed IdP (Auth0, Okta, Azure AD, Google Identity)

**Options**:
1. **Self-hosted Keycloak**: Full control, maintenance burden, SSO complexity
2. **External managed IdP**: Managed service, cost, potential latency, vendor lock-in
3. **Hybrid**: Keycloak for dev/staging, external IdP for production

**Recommended Default**: Use external managed IdP for production unless there is a strong reason to self-host Keycloak. Keep Keycloak for local/dev/integration testing.

**Rationale**:
- External IdP reduces operational burden (patching, availability, scaling)
- Production security posture improved (managed security expertise)
- Keycloak remains available for dev/testing without external dependencies
- SSO integration easier with established IdP providers

**Risks/Trade-offs**:
- External IdP adds recurring cost
- Vendor lock-in (migration complexity)
- Potential latency in auth flows
- Dependency on external service availability

**Dependencies**:
- DEC-001 (Secrets management) for IdP client secrets
- Production budget approval for IdP service
- SSO requirements (SAML, SCIM, social login)

**Implementation Impact**:
- Select IdP provider (Auth0, Okta, Azure AD, etc.)
- Configure OIDC application in IdP
- Update environment variables for production
- Configure JWT validation for IdP tokens
- Update Keycloak for dev-only use
- Add IdP health monitoring

**Priority**: P0 (Security/Production Readiness)

**Owner**: TBD (Security/Platform)

**Decision Status**: Proposed

---

### DEC-005: Object Storage Requirement

**Related Finding**: MS-INFRA-005

**Current State**:
- No object storage configured
- Layer 1 crawling may persist raw files
- No S3-compatible storage in compose files
- No storage abstraction layer

**Decision Required**: Determine if raw file ingestion requires S3-compatible storage, and choose implementation

**Options**:
1. **MinIO (self-hosted)**: S3-compatible, self-managed, lower cost
2. **AWS S3**: Managed, high durability, egress costs
3. **Azure Blob Storage**: Managed, integration with Azure ecosystem
4. **GCS**: Managed, integration with GCP ecosystem
5. **No object storage**: Use ephemeral storage or database BLOBs

**Recommended Default**: Add S3-compatible abstraction. Use MinIO locally and S3-compatible managed storage in production if Layer 1 persists raw uploads or crawl artifacts.

**Rationale**:
- S3-compatible abstraction provides flexibility for provider choice
- MinIO for dev reduces external dependencies
- Production managed storage provides durability and scalability
- Abstraction layer allows future migration without code changes

**Risks/Trade-offs**:
- Self-hosted MinIO has operational overhead (backup, scaling)
- Managed storage adds cost and egress fees
- Storage abstraction adds complexity to codebase
- May be unnecessary if Layer 1 doesn't persist raw files

**Dependencies**:
- Layer 1 requirements analysis (raw file persistence needs)
- DEC-001 (Secrets management) for storage credentials
- Data retention policy

**Implementation Impact**:
- Add S3-compatible storage abstraction layer
- Configure MinIO in dev compose
- Select production storage provider
- Update Layer 1 to use storage abstraction
- Add storage backup/restore procedures
- Configure lifecycle policies (retention, archival)

**Priority**: P0 (Architecture/Production Readiness)

**Owner**: TBD (Layer 1 Team / Architecture)

**Decision Status**: Proposed

---

### DEC-006: SIEM Provider and Wiring

**Related Finding**: MS-PR-003

**Current State**:
- `SIEMAuditSink` library exists in `packages/shared/src/value_fabric/shared/audit/siem_integration.py`
- Webhook delivery with retry logic implemented
- Dead-letter queue support exists
- No SIEM provider selected
- No service configuration/wiring
- Runbook exists: `docs/troubleshooting/runbooks/application/siem-webhook-outage-and-replay.md`

**Decision Required**: Choose SIEM provider and configure service wiring

**Options**:
1. **Splunk**: Enterprise-grade, high cost, comprehensive
2. **Datadog**: Managed, good integration, cost scales with volume
3. **Sumo Logic**: Cloud-native, flexible pricing
4. **Elastic Stack (ELK)**: Self-hosted option, operational burden
5. **Provider-neutral**: Keep webhook delivery, defer provider selection

**Recommended Default**: Keep SIEMAuditSink provider-neutral. Implement webhook delivery hardening, retry, DLQ, and configuration before locking into a specific SIEM.

**Rationale**:
- Provider-neutral webhook delivery maintains flexibility
- Existing library has retry, DLQ, and metrics
- Allows time to evaluate SIEM options based on volume and budget
- Hardening delivery infrastructure is valuable regardless of provider

**Risks/Trade-offs**:
- No SIEM-specific optimizations (parsing, dashboards)
- Webhook delivery may have reliability issues without provider SDK
- Deferred SIEM selection delays monitoring capabilities
- May need to re-implement for provider-specific features

**Dependencies**:
- SIEM budget and requirements analysis
- Audit volume estimation
- DEC-001 (Secrets management) for SIEM credentials

**Implementation Impact**:
- Configure SIEM endpoint in environment variables
- Add SIEM credentials to secrets management
- Wire SIEMAuditSink into service audit paths
- Add SIEM delivery monitoring and alerting
- Implement dead-letter queue replay automation
- Test delivery hardening (retry, backoff, signature)

**Priority**: P0 (Security/Production Readiness)

**Owner**: TBD (Security/Observability)

**Decision Status**: Proposed

---

### DEC-007: Super Admin Console

**Related Finding**: MS-PR-001

**Current State**:
- No admin console exists
- Audit logging infrastructure exists
- No protected admin routes
- No admin UI

**Decision Required**: Determine scope and implementation approach for super admin console

**Options**:
1. **Separate admin service**: Dedicated admin API and UI
2. **Admin routes in existing services**: Protected endpoints in each service
3. **CLI tool**: Command-line admin interface
4. **No console**: Use direct database/infrastructure access

**Recommended Default**: Defer full console. Start with protected read-only admin routes and audit logging, then build UI later.

**Rationale**:
- Admin routes provide immediate operational capability without UI overhead
- Audit logging is prerequisite for any admin interface
- UI can be built incrementally based on actual usage patterns
- Reduces initial implementation scope

**Risks/Trade-offs**:
- No visual admin interface increases operational complexity
- CLI-only access may limit usability for non-technical operators
- Deferred UI may delay admin capability adoption
- Security risk if admin routes not properly protected

**Dependencies**:
- DEC-004 (Auth provider) for admin role/permission enforcement
- Audit logging infrastructure
- RBAC design (admin roles, permissions)

**Implementation Impact**:
- Add protected admin routes to key services (tenant management, system config)
- Implement RBAC middleware for admin access
- Add audit logging for all admin actions
- Document admin API endpoints
- Design admin UI for future implementation

**Priority**: P1 (Operational Capability)

**Owner**: TBD (Platform/Security)

**Decision Status**: Deferred

---

### DEC-008: DSAR/Privacy Data Export API

**Related Finding**: MS-PR-002

**Current State**:
- No DSAR API exists
- No data inventory
- No retention policy defined
- Multi-layer data (PostgreSQL, Neo4j, Redis)

**Decision Required**: Determine implementation scope and data retention policy for DSAR/privacy data export

**Options**:
1. **Full DSAR orchestration**: Automated cross-layer data aggregation, export formats
2. **Minimal DSAR API**: Basic data export endpoints, manual orchestration
3. **Defer implementation**: Wait until data inventory and retention policy defined

**Recommended Default**: Create a minimal DSAR orchestration API design first. Do not implement until data inventory and retention policy are defined.

**Rationale**:
- DSAR requires complete data inventory (what data, where, how long)
- Retention policy must be defined before export can be implemented
- Cross-layer aggregation is complex and error-prone
- Design-first approach ensures compliance requirements are met

**Risks/Trade-offs**:
- Deferred implementation may delay compliance readiness
- Data inventory effort is significant
- Cross-layer query complexity may require architectural changes
- GDPR/CCPA timelines may pressure implementation

**Dependencies**:
- Data inventory (all data stores, fields, retention periods)
- Legal/compliance review of retention policy
- Data export format requirements (JSON, CSV, PDF)
- Identity verification for DSAR requests

**Implementation Impact**:
- Conduct data inventory across all layers
- Define retention policy with legal review
- Design DSAR orchestration API
- Implement per-layer data export endpoints
- Add identity verification for DSAR requests
- Implement audit logging for DSAR processing

**Priority**: P1 (Compliance)

**Owner**: TBD (Legal/Compliance/Platform)

**Decision Status**: Decision Required

---

### DEC-009: Stripe Billing Integration

**Related Finding**: MS-PR-004

**Current State**:
- Partial Stripe integration exists
- No complete billing implementation
- Pricing model not decided
- No subscription management

**Decision Required**: Determine billing model and complete Stripe integration scope

**Options**:
1. **Usage-based billing**: Meter and charge per API call/compute
2. **Tiered pricing**: Fixed plans with feature limits
3. **Per-seat pricing**: Charge per user/seat
4. **Hybrid**: Base fee + usage overage
5. **Defer implementation**: Wait until pricing model decided

**Recommended Default**: Defer until pricing model is decided. Do not build full billing until usage/tier/per-seat model is selected.

**Rationale**:
- Billing implementation is tightly coupled to pricing model
- Wrong pricing model assumption requires significant rework
- Pricing model is business decision, not technical
- Partial integration can be completed without full billing

**Risks/Trade-offs**:
- Deferred billing delays revenue generation
- Pricing model decision may take time
- Stripe integration complexity depends on model
- May need to refactor existing partial integration

**Dependencies**:
- Pricing model decision (business/product)
- Stripe account setup
- Billing UI requirements
- Invoice delivery preferences

**Implementation Impact**:
- Complete Stripe integration based on pricing model
- Implement subscription management
- Add billing webhooks handling
- Create billing UI or admin routes
- Implement invoice generation and delivery
- Add billing metrics and reporting

**Priority**: P1 (Business Capability)

**Owner**: TBD (Product/Engineering)

**Decision Status**: Decision Required

---

### DEC-010: Feature Flag Service

**Related Finding**: MS-PR-005

**Current State**:
- No feature flag service exists
- No runtime validation
- Some feature flag K8s manifests exist

**Decision Required**: Choose between external provider (LaunchDarkly, Split) vs self-hosted solution

**Options**:
1. **External provider (LaunchDarkly/Split)**: Managed, feature-rich, cost
2. **Self-hosted simple flags**: Tenant-aware, deny-by-default, kill-switch
3. **Database-backed flags**: Simple implementation, less feature-rich
4. **No feature flags**: Use deployment-based feature toggles

**Recommended Default**: Keep self-hosted/simple tenant-aware feature flags initially, with deny-by-default behavior and kill-switch tests. Consider LaunchDarkly/Split later.

**Rationale**:
- Self-hosted flags reduce initial cost and complexity
- Deny-by-default ensures safe rollout
- Kill-switch tests provide safety net
- External provider can be adopted later if advanced features needed

**Risks/Trade-offs**:
- Self-hosted flags have limited feature set (no A/B testing, gradual rollout UI)
- Operational burden for flag management
- No real-time flag updates without infrastructure
- External provider adds cost and dependency

**Dependencies**:
- Flag evaluation rules design
- Kill-switch test requirements
- Flag management workflow

**Implementation Impact**:
- Implement tenant-aware feature flag storage (database or config)
- Add flag evaluation middleware to services
- Implement deny-by-default behavior
- Add kill-switch tests for critical features
- Create flag management admin routes
- Document flag lifecycle and governance

**Priority**: P1 (Production Safety)

**Owner**: TBD (Platform/Engineering)

**Decision Status**: Proposed

---

### DEC-011: Notification Service

**Related Finding**: MS-PR-006

**Current State**:
- No notification service exists
- No retry logic for notifications
- No multi-channel support

**Decision Required**: Determine channel support and implementation scope

**Options**:
1. **Multi-channel service**: Email, SMS, in-app, push notifications
2. **Limited channels**: In-app and email only
3. **Defer implementation**: No notifications until required

**Recommended Default**: Defer broad multi-channel notifications. Start with in-app/email only if required for workflow approvals or DSAR/billing/security events.

**Rationale**:
- Multi-channel notifications add significant complexity
- Many SaaS products succeed with in-app notifications only
- Email can be added via existing services (SendGrid, SES)
- SMS/push add cost and regulatory complexity

**Risks/Trade-offs**:
- Limited notification channels may reduce user engagement
- Email-only may miss urgent notifications
- Deferred implementation may delay workflow automation
- SMS/push may be required for security events (2FA)

**Dependencies**:
- Workflow requirements (approvals, DSAR, billing)
- Security event notification requirements
- Email service provider (SendGrid, SES, Mailgun)

**Implementation Impact**:
- Implement in-app notification storage and delivery
- Add email service integration
- Create notification preferences API
- Add notification retry logic
- Implement notification templates
- Add notification metrics and monitoring

**Priority**: P2 (User Experience)

**Owner**: TBD (Platform/Product)

**Decision Status**: Deferred

---

### DEC-012: Health Aggregation Service

**Related Finding**: MS-PR-009

**Current State**:
- Per-service health endpoints exist
- Prometheus/Grafana/Alertmanager configured
- No centralized health aggregation
- No status page

**Decision Required**: Determine if centralized health aggregation is needed

**Options**:
1. **Central health endpoint**: Aggregate all service health into single endpoint
2. **Prometheus/Grafana only**: Use existing observability stack
3. **Status page**: External status page for customers
4. **No aggregation**: Rely on per-service health and monitoring

**Recommended Default**: Use Prometheus/Grafana/Alertmanager as the primary operational view. Add a lightweight health aggregation endpoint only if needed for status page or deployment gates.

**Rationale**:
- Existing observability stack provides comprehensive health view
- Central health endpoint adds operational burden
- Status page is customer-facing, can be added later
- Deployment gates can use per-service health checks

**Risks/Trade-offs**:
- No single health endpoint for simple health checks
- Status page requires external hosting and maintenance
- Prometheus query complexity for overall system health
- May need custom dashboards for operational health

**Dependencies**:
- Status page requirements (customer-facing vs internal)
- Deployment gate health check requirements
- Prometheus/Grafana dashboard coverage

**Implementation Impact**:
- If central endpoint: Create health aggregation service, query all services
- If status page: Configure status page provider, integrate health checks
- If Prometheus only: Ensure dashboards cover all critical services
- Update deployment gates to use appropriate health checks

**Priority**: P2 (Operational Maturity)

**Owner**: TBD (Observability/Platform)

**Decision Status**: Deferred

---

### DEC-013: Dead-Letter Queue Handling

**Related Finding**: MS-PR-010

**Current State**:
- SIEMAuditSink has dead-letter queue support
- No persistent DLQ storage
- No DLQ replay automation
- No DLQ monitoring/alerting

**Decision Required**: Determine persistent storage and replay automation for dead-letter queues

**Options**:
1. **Redis streams**: Lightweight, existing Redis infrastructure
2. **Kafka**: Durable, scalable, operational overhead
3. **SQS/SNS**: Managed, cost, vendor lock-in
4. **In-memory only**: Current state, no persistence
5. **No DLQ**: Fail fast, no retry

**Recommended Default**: Implement DLQ pattern where async delivery already exists, especially SIEM/webhooks and background jobs. Do not introduce Kafka unless needed.

**Rationale**:
- DLQ is critical for async delivery reliability (SIEM, notifications)
- Redis streams leverage existing infrastructure
- Kafka adds significant operational complexity
- Managed queues add cost and vendor dependency
- Start simple, scale if needed

**Risks/Trade-offs**:
- Redis streams have lower durability than Kafka
- No DLQ means data loss on delivery failures
- Kafka provides better scalability and durability
- Managed queues reduce operational burden

**Dependencies**:
- SIEM delivery criticality (influences storage choice)
- Background job failure handling requirements
- Redis capacity planning for DLQ storage

**Implementation Impact**:
- Configure Redis streams for DLQ persistence
- Add DLQ monitoring and alerting
- Implement DLQ replay automation (cron job or admin route)
- Add DLQ metrics (queue depth, age, replay success rate)
- Document DLQ replay procedures
- Test DLQ failure scenarios

**Priority**: P2 (Reliability) - may be P1 if SIEM is critical

**Owner**: TBD (Platform/Engineering)

**Decision Status**: Proposed

---

## Implementation Sequencing

### Phase 0 — Decisions Before Build

**Goal**: Resolve architectural decisions before implementation begins.

**Items**:
- DEC-004: Auth provider strategy (external IdP vs Keycloak)
- DEC-001: Secrets management strategy (Vault HA vs external)
- DEC-002: API gateway role (gateway vs library vs internal)
- DEC-003: Layer 2.5 production status (production-candidate vs experimental)
- DEC-005: Object storage requirement (MinIO vs S3 vs none)

**Acceptance Criteria**:
- All Phase 0 decisions have "Accepted" status
- Documented rationale and trade-offs
- Stakeholder sign-off on decisions
- Implementation plan updated based on decisions

**Estimated Duration**: 1-2 weeks (decision workshops, stakeholder review)

---

### Phase 1 — Production Blockers/Security Foundation

**Goal**: Implement critical security and production readiness infrastructure.

**Items**:
- MS-PR-008: Migration runner sequencing (COMPLETED)
- DEC-001: Secrets management implementation
- MS-INFRA-002: ExternalSecrets integration (COMPLETED)
- MS-PR-007: Backup/restore automation (COMPLETED)
- DEC-004: Auth provider wiring
- MS-INFRA-004: PgBouncer (COMPLETED)

**Acceptance Criteria**:
- Vault HA deployed and operational
- ExternalSecrets Operator syncing secrets
- Auth provider configured and tested
- Backup jobs running and verified
- Migration sequencing tested with concurrent deployments
- PgBouncer pooling configured and monitored

**Estimated Duration**: 2-3 weeks

---

### Phase 2 — Production Hardening

**Goal**: Harden production services and complete missing production-critical features.

**Items**:
- DEC-006: SIEM delivery hardening
- DEC-010: Feature flag kill-switch
- DEC-003: Layer 2.5 production wiring (if accepted)
- DEC-002: API gateway/ingress finalization
- DEC-005: Object storage implementation

**Acceptance Criteria**:
- SIEM delivery hardened with retry, DLQ, monitoring
- Feature flags with deny-by-default and kill-switch tests
- Layer 2.5 production-ready (if accepted)
- Ingress/gateway configured and tested
- Object storage operational with backup

**Estimated Duration**: 3-4 weeks

---

### Phase 3 — SaaS/Compliance Capabilities

**Goal**: Implement SaaS business capabilities and compliance features.

**Items**:
- DEC-008: DSAR API (after data inventory)
- DEC-007: Super admin console (read-only routes first)
- DEC-009: Stripe billing (after pricing model)
- DEC-011: Notification service (in-app/email only)

**Acceptance Criteria**:
- DSAR API implemented with audit logging
- Admin routes protected and audited
- Stripe billing integrated based on pricing model
- In-app/email notifications operational

**Estimated Duration**: 4-6 weeks (depends on decision dependencies)

---

### Phase 4 — Operational Maturity

**Goal**: Improve operational tooling and monitoring.

**Items**:
- DEC-012: Health aggregation (if needed)
- DEC-013: Dead-letter queue handling
- MS-INFRA-006: Local vector DB (COMPLETED)
- MS-APP-003: Orphan directory cleanup (COMPLETED)

**Acceptance Criteria**:
- Health aggregation endpoint (if needed)
- DLQ with Redis streams and replay automation
- Local vector DB for development
- Clean repository structure

**Estimated Duration**: 2-3 weeks

---

## Dependencies Graph

```
Phase 0 (Decisions)
├── DEC-004 (Auth) ──┐
├── DEC-001 (Secrets) ├──> Phase 1 (Security Foundation)
├── DEC-002 (Gateway) ─┘
├── DEC-003 (Layer 2.5) ──> Phase 2 (Production Hardening)
└── DEC-005 (Object Storage) ──> Phase 2

Phase 1 (Security Foundation)
└── All items ──> Phase 2 (Production Hardening)

Phase 2 (Production Hardening)
├── DEC-006 (SIEM) ──> DEC-013 (DLQ)
├── DEC-010 (Feature Flags) ──> Phase 3
└── DEC-003 (Layer 2.5) ──> Phase 3

Phase 3 (SaaS/Compliance)
├── DEC-008 (DSAR) ──> DEC-007 (Admin Console)
├── DEC-009 (Billing) ──> DEC-007 (Admin Console)
└── DEC-011 (Notifications) ──> Phase 4

Phase 4 (Operational Maturity)
└── DEC-013 (DLQ) ──> DEC-012 (Health Aggregation)
```

---

## Risk Matrix

| Decision | Risk | Impact | Mitigation |
|----------|------|--------|------------|
| DEC-001 | Vault HA operational burden | High | Document procedures, consider external managed as fallback |
| DEC-002 | Gateway complexity | Medium | Start with library-only, defer gateway decision |
| DEC-003 | Layer 2.5 unknown dependencies | Medium | Thorough dependency analysis before production |
| DEC-004 | External IdP cost/lock-in | Medium | Evaluate multiple providers, negotiate enterprise pricing |
| DEC-005 | Object storage unnecessary | Low | Validate Layer 1 requirements before implementation |
| DEC-006 | SIEM delivery reliability | High | Harden webhook delivery, DLQ, monitoring |
| DEC-008 | DSAR compliance timeline | High | Start data inventory early, engage legal early |
| DEC-009 | Billing model rework | Medium | Validate pricing model with customers before implementation |
| DEC-010 | Feature flag complexity | Low | Start simple, deny-by-default, add features as needed |
| DEC-011 | Notification scope creep | Low | Limit to in-app/email initially |
| DEC-012 | Health aggregation unnecessary | Low | Use existing Prometheus/Grafana, defer central endpoint |
| DEC-013 | DLQ storage scalability | Medium | Start with Redis streams, migrate to Kafka if needed |

---

## Next Steps

1. **Review and Approve Decisions**: Stakeholder review of Phase 0 decisions
2. **Decision Workshops**: Schedule workshops for decisions requiring input
3. **Update Status**: Change decision statuses from "Propposed" to "Accepted" as decisions are made
4. **Implementation Planning**: Create detailed implementation plans for Phase 1
5. **Resource Allocation**: Assign owners and estimate effort for each phase

---

## Appendix: Completed Items

The following items from the missing services audit have already been completed:

- **MS-APP-003**: Deleted empty orphaned `services/services/` directory
- **MS-INFRA-004**: Added PgBouncer to production compose files
- **MS-PR-008**: Added `pg_advisory_lock` to migration runner
- **MS-PR-007**: Added automated backup jobs for PostgreSQL and Neo4j
- **MS-INFRA-002**: Added ExternalSecrets Operator to K8s base manifests
- **MS-INFRA-006**: Added Qdrant vector database to dev compose
- **MS-PR-003**: Verified SIEM integration library exists (requires provider selection)

These items are reflected in the implementation sequencing as completed prerequisites.
