# Reference Implementation Checklist: Clerk-Compliant Service Standard

Any new internal service, client package, or autonomous agent module in the Fabric 4L platform MUST comply with the following architectural and security standards to be certified **"Clerk-Compliant"**.

---

## 1. Architectural Boundary & Envelope Verification

- [ ] **No Direct Clerk JWT Parsing in Downstream Services**: Downstream services (L1–L6) must NEVER parse client-supplied Bearer tokens directly or contact Clerk JWKS endpoints over the public internet.
- [ ] **Ed25519 `AuthContext` Required**: Every internal HTTP/RPC endpoint must require and verify the `X-Fabric-Auth` header using the shared Ed25519 public key.
- [ ] **Strip Client Ingress Headers**: API Gateways must unconditionally strip incoming `X-Fabric-Auth` headers from external clients to prevent envelope spoofing.
- [ ] **Multi-Key ID (`kid`) Support**: Signature verification must inspect envelope `kid` header and support multi-key verification during rotation periods.

---

## 2. Multi-Tenant Isolation & RLS

- [ ] **Authenticate Context over Request Payloads**: `tenant_id` must be extracted exclusively from the verified `AuthContext` claim, never from request bodies or URL path parameters.
- [ ] **Non-Bypassable RLS Execution**: Every database session must invoke `SET LOCAL app.tenant_id = '<tenant_id>'` before executing tenant-scoped queries.
- [ ] **Graph & Vector Query Parameterization**: All Neo4j Cypher and vector similarity searches must include `$tenant_id` filters.
- [ ] **Hostile Cross-Tenant Test Coverage**: Services must include automated adversarial tests asserting that Tenant A cannot access Tenant B records (returning HTTP 403 or empty sets).

---

## 3. Webhook Integration & Event Consistency

- [ ] **Svix Signature Verification**: All webhook ingestion endpoints must verify `svix-signature` using HMAC-SHA256 with timestamp tolerance ($\le 300\text{s}$).
- [ ] **Idempotent Processing**: Webhook handlers must track `svix-id` to discard duplicate and replayed events safely.
- [ ] **Ordering Conflict Resilience**: Membership events arriving before organization or user creation must respond with HTTP 409 to trigger safe backoff retries.
- [ ] **DLQ Routing**: Failed webhook events must be routed to `WebhookDLQ` with structured logging.

---

## 4. Frontend & Client Governance

- [ ] **Single Token Bridge**: Web and mobile clients must route all token acquisition through the centralized `ClerkAuthBridge`.
- [ ] **Standardized UI Controls**: UI surfaces must use `<FabricUserButton />`, `<FabricOrganizationSwitcher />`, and `<FabricSignIn />` themed components conforming to `DESIGN.md`.
- [ ] **Canonical Scope Authority**: Frontend authorization decisions must rely on `/auth/authorization-snapshot` claims rather than locally calculated permissions.
- [ ] **Instant Revocation Handling**: Frontend clients must listen to 401 response codes and trigger session revalidation upon remote session termination.

---

## 5. Security & Dev DX

- [ ] **No Secrets in Source**: No Clerk API keys (`sk_...`, `whsec_...`) or Ed25519 private keys committed to repositories.
- [ ] **Zero Dev Bypass in Production**: `ProductionSafetyValidator` must fail service startup if `DEV_AUTH_BYPASS` or insecure flags are enabled in production environments.
- [ ] **One-Command Dev Setup**: Local development environments must boot reliably using `make auth-dev` or `pnpm auth:dev`.
- [ ] **Structured Observability**: All verification paths must emit Prometheus metrics (`auth_verifications_total`, `auth_verification_duration_seconds`).
