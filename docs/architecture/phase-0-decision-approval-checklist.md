# Phase 0 Decision Approval Checklist

**Purpose**: Stakeholder approval checklist for Phase 0 architectural decisions before engineering implementation begins.

**Instructions**: Review each decision below. For each, select one status: Approved, Rejected, Deferred, or Needs more research. Add comments if needed.

**Deadline**: [Insert deadline]

**Stakeholders**: [Insert stakeholder names]

---

## DEC-001: Secrets Management Strategy

**Recommended Default**: Use Vault + ExternalSecrets for now because repo already has Vault integration, but document external managed secrets as an acceptable future production alternative.

**Approval Question**: Should we proceed with Vault HA + ExternalSecrets Operator for production secrets management, or should we use an external managed secrets provider (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager)?

**Options**:
- A: Vault HA (self-managed) + ExternalSecrets Operator
- B: External managed secrets (AWS/Azure/GCP)
- C: Hybrid (Vault for dev/staging, external for production)

**Recommended Answer**: A

**Impact if Accepted**:
- Deploy Vault HA cluster (3+ nodes, Raft backend)
- Configure auto-unseal (AWS KMS, Azure Key Vault, or GCP KMS)
- Update ClusterSecretStore to point to production Vault
- Add Vault backup and restore procedures
- Estimated effort: 2-3 weeks

**Impact if Deferred**:
- Cannot proceed with Phase 1 security foundation
- Secrets remain in environment variables (security risk)
- Delays production readiness timeline

**Required Follow-up Implementation Ticket if Accepted**:
- [ ] Deploy Vault HA cluster with auto-unseal
- [ ] Configure ExternalSecrets Operator for production
- [ ] Migrate dev Vault secrets to production Vault
- [ ] Document Vault backup and restore procedures

**Status**: [ ] Approved  [ ] Rejected  [ ] Deferred  [ ] Needs more research

**Comments**: _______________________________

---

## DEC-002: API Gateway Role

**Recommended Default**: Do not make services/api a production ingress gateway yet. Prefer cloud-native ingress/Gateway API/NGINX/Istio for ingress, and treat services/api as either a shared API surface or internal gateway only after confirmation.

**Approval Question**: Should services/api be deployed as a production ingress gateway, kept as a shared library only, or used as an internal gateway for service-to-service routing?

**Options**:
- A: Deploy as production ingress gateway (nginx/Envoy)
- B: Keep as library only, use cloud-native ingress (Istio/Gateway API/NGINX)
- C: Internal gateway only (service-to-service routing)

**Recommended Answer**: B

**Impact if Accepted**:
- Document services/api as shared library
- Configure cloud-native ingress controller (Istio/Gateway API/NGINX)
- No additional service deployment
- Estimated effort: 1-2 weeks

**Impact if Deferred**:
- Cannot finalize ingress strategy
- Services/api role remains ambiguous
- May delay production networking configuration

**Required Follow-up Implementation Ticket if Accepted**:
- [ ] Document services/api usage patterns as shared library
- [ ] Select and configure cloud-native ingress controller
- [ ] Update K8s manifests for ingress configuration
- [ ] Remove services/api from production deployment plans

**Status**: [ ] Approved  [ ] Rejected  [ ] Deferred  [ ] Needs more research

**Comments**: _______________________________

---

## DEC-003: Layer 2.5 Signal Refinery Production Status

**Recommended Default**: Treat as architecturally intentional and production-candidate, but gate production inclusion on readiness checks, health endpoint, metrics, contract coverage, and dependency wiring.

**Approval Question**: Should Layer 2.5 Signal Refinery be included in the production stack, kept as experimental/dev-only, or decommissioned?

**Options**:
- A: Include in production stack after readiness checks
- B: Keep as experimental/dev-only
- C: Decommission (remove from codebase)

**Recommended Answer**: A (conditional on readiness checks)

**Impact if Accepted**:
- Add to docker-compose.full.yml and docker-compose.prod.yml
- Create K8s deployment manifests
- Generate OpenAPI spec
- Add health endpoint, metrics, and monitoring
- Validate dependencies (L1, L2, L3, L4 connectivity)
- Estimated effort: 2-3 weeks

**Impact if Deferred**:
- Layer 2.5 remains dev-only
- Signal refinement capability not available in production
- May require re-evaluation later

**Required Follow-up Implementation Ticket if Accepted**:
- [ ] Implement health endpoint for Layer 2.5
- [ ] Add metrics instrumentation
- [ ] Generate OpenAPI spec
- [ ] Validate dependencies and resource requirements
- [ ] Add to production compose files
- [ ] Create K8s deployment manifests

**Status**: [ ] Approved  [ ] Rejected  [ ] Deferred  [ ] Needs more research

**Comments**: _______________________________

---

## DEC-004: Auth Provider Strategy

**Recommended Default**: Use external managed IdP for production unless there is a strong reason to self-host Keycloak. Keep Keycloak for local/dev/integration testing.

**Approval Question**: Should we use an external managed IdP (Auth0, Okta, Azure AD, Google Identity) for production, or self-host Keycloak?

**Options**:
- A: External managed IdP (Auth0/Okta/Azure AD/Google)
- B: Self-hosted Keycloak for production
- C: Hybrid (Keycloak for dev/staging, external for production)

**Recommended Answer**: A

**Impact if Accepted**:
- Select IdP provider (Auth0, Okta, Azure AD, etc.)
- Configure OIDC application in IdP
- Update environment variables for production
- Configure JWT validation for IdP tokens
- Keep Keycloak for dev-only use
- Estimated effort: 1-2 weeks

**Impact if Deferred**:
- Cannot proceed with production auth configuration
- Keycloak dev mode may be used in production (security risk)
- Delays production readiness timeline

**Required Follow-up Implementation Ticket if Accepted**:
- [ ] Select and provision external IdP provider
- [ ] Configure OIDC application
- [ ] Update production environment variables
- [ ] Configure JWT validation for IdP tokens
- [ ] Update Keycloak for dev-only use
- [ ] Add IdP health monitoring

**Status**: [ ] Approved  [ ] Rejected  [ ] Deferred  [ ] Needs more research

**Comments**: _______________________________

---

## DEC-005: Object Storage Requirement

**Recommended Default**: Add S3-compatible abstraction. Use MinIO locally and S3-compatible managed storage in production if Layer 1 persists raw uploads or crawl artifacts.

**Approval Question**: Should we add S3-compatible object storage for raw file ingestion, and which implementation should we use?

**Options**:
- A: MinIO (self-hosted) for dev, S3 for production
- B: AWS S3 (managed) for production
- C: Azure Blob Storage (managed) for production
- D: GCS (managed) for production
- E: No object storage (use ephemeral storage or database BLOBs)

**Recommended Answer**: A

**Impact if Accepted**:
- Add S3-compatible storage abstraction layer
- Configure MinIO in dev compose
- Select production storage provider
- Update Layer 1 to use storage abstraction
- Add storage backup/restore procedures
- Estimated effort: 2-3 weeks

**Impact if Deferred**:
- Layer 1 raw file persistence may be limited
- No scalable storage for crawl artifacts
- May require re-architecture later if storage needs grow

**Required Follow-up Implementation Ticket if Accepted**:
- [ ] Validate Layer 1 raw file persistence requirements
- [ ] Implement S3-compatible storage abstraction
- [ ] Configure MinIO in dev compose
- [ ] Select production storage provider
- [ ] Update Layer 1 to use storage abstraction
- [ ] Add storage backup/restore procedures

**Status**: [ ] Approved  [ ] Rejected  [ ] Deferred  [ ] Needs more research

**Comments**: _______________________________

---

## Summary

**Total Decisions**: 5

**Approval Status**:
- Approved: ___/5
- Rejected: ___/5
- Deferred: ___/5
- Needs more research: ___/5

**Can Proceed to Phase 1?**: [ ] Yes  [ ] No

**Blocking Issues**: _______________________________

**Additional Comments**: _______________________________

---

## Sign-Off

**Reviewed By**: _______________________________  **Date**: _______________

**Approved By**: _______________________________  **Date**: _______________

**Architect Sign-Off**: _______________________________  **Date**: _______________

**Security Sign-Off**: _______________________________  **Date**: _______________
