---
title: "ADR-038: Externalized Secret Management and Automated Secret Detection"
category: "security"
audience: "all"
last-reviewed: "2026-07-20"
freshness: "current"
related: ["../../explanations/adr/ADR-004-jwt-api-key-authentication-strategy", "../../explanations/adr/ADR-009-jwt-api-key-hybrid-authentication"]
---

# ADR-038: Externalized Secret Management and Automated Secret Detection

**Status:** Accepted — partially implemented

**Date:** 2026-07-20

**Deciders:** Security Team, Platform Engineering

---

## Context

Fabric 4L uses Infisical as its canonical secret manager, with secrets
organized by service path and environment (`docs/security/secrets-management.md`).
A secret leak incident response runbook exists
(`docs/runbooks/security/respond-to-secret-leak.md`) with SEV1-SEV4
classification and immediate revocation procedures. A manifest secret injection
policy (`docs/governance/manifest-secret-injection-policy.md`) prohibits inline
secrets in Kubernetes manifests with CI enforcement.

However, the architectural decision binding these together — that secrets are
externalized and commits are scanned — has never been formally documented as an
ADR. Pre-commit gitleaks hooks exist but are bypassable. CI-authoritative
secret scanning is not yet a required check. A repowise security scan
identified 52 potential secret findings across the codebase, demonstrating that
the current controls are insufficient.

This ADR establishes the durable architectural rule. Operational details
(incident response, rotation procedures, fixture formats) remain in existing
standards and runbooks.

## Decision

### Architectural Rule

Secrets are externalized to a managed secret store (Infisical) and never appear
in committed files. Automated secret detection runs in CI as an authoritative
control, with pre-commit hooks as a supplemental early-feedback mechanism.

### Canonical Runtime Secret Sources

Secrets enter the runtime only through approved injection paths:

1. **Infisical runtime injection** — local development, CI, and process-level
   injection (documented in `docs/security/secrets-management.md`)
2. **Kubernetes Secret references** — `valueFrom.secretKeyRef` in workload
   manifests, synced from ExternalSecret/ESO in production
3. **Workload identity** — cloud-native service-to-service authentication
4. **CI secret store** — pipeline-only credentials injected at job start

### Prohibited Secret Locations

Secrets must not appear in:

- Committed source files, test fixtures, documentation, or manifests
- Command-line arguments (visible in process listings)
- Logs, exception messages, or telemetry attributes
- Generated manifests, frontend bundles, or container layers
- Environment files that are not approved templates (per
  `docs/governance/manifest-secret-injection-policy.md`)

### Test Fixture Convention

Synthetic test fixtures that resemble real secret formats must:

- Use non-routable or sandbox account formats (e.g., `sk_test_dummy...`)
- Be centrally defined in a shared fixture module
- Be registered in a scanner allowlist with structured justification (path,
  owner, expiry, reason)
- Have tests proving they cannot authenticate against real services

A `test_` prefix alone is insufficient — scanner allowlists with justification
are required. Realistic synthetic fixtures may trigger scanners; the allowlist
ensures these are tracked and reviewed.

### Authoritative Controls

The authoritative secret detection controls are:

1. **Required CI secret scan** — gitleaks or equivalent, runs on every PR,
   blocks merge on finding. This is the authoritative gate.
2. **Server-side push protection** — GitHub push protection (where available)
   rejects pushes containing known secret patterns.
3. **Branch protection** — secret scan check is a required status check before
   merge.
4. **Pinned scanner version/configuration** — scanner rules and version are
   pinned to prevent regression in detection coverage.
5. **Scheduled full-repository scans** — periodic scan of full Git history and
   all branches to detect secrets introduced outside the PR flow.

Pre-commit hooks (`gitleaks` in `.pre-commit-config.yaml`) are a supplemental
developer convenience for early feedback. They are bypassable (`--no-verify`)
and must not be the sole control.

### Scanner Finding Classification

Scanner results are "potential secret findings" until classified. A finding
may be:

- A real active credential
- A revoked credential
- A synthetic fixture (allowlisted)
- An example or documentation placeholder
- A false positive

Only provider-side validation or ownership confirmation determines whether a
finding represents a "live" secret. Scanner output must not be equated with
confirmed credential exposure.

## Alternatives Considered

### Pre-commit hooks as sole control

- **Pros:** Simple setup; fast feedback; no CI infrastructure needed.
- **Cons:** Bypassable via `--no-verify`; no protection against direct pushes or history rewriting; no audit trail of scans.
- **Why rejected:** Not authoritative — a bypassable control cannot be the sole defense against credential exposure.

### Manual review only

- **Pros:** Human judgment can distinguish real secrets from fixtures; no tooling needed.
- **Cons:** Human review cannot reliably detect secrets in diffs at scale; fatigue leads to missed findings; no automated regression prevention.
- **Why rejected:** Scale makes it infeasible; automated detection is necessary for consistent enforcement.

### No test fixture allowlists

- **Pros:** Simpler scanner configuration; no allowlist maintenance.
- **Cons:** Realistic synthetic fixtures trigger scanner false positives, blocking CI; without allowlists, either false positives block development or real secrets slip through when scanning is disabled.
- **Why rejected:** Allowlists with structured justification are necessary to balance detection sensitivity with development velocity.

### HashiCorp Vault instead of Infisical

- **Pros:** Equally capable secret management; widely adopted; mature ecosystem.
- **Cons:** Infisical already deployed and integrated across the platform; migration cost not justified at current scale; no functional advantage for current requirements.
- **Why rejected:** Migration cost exceeds benefit. Revisit if Infisical becomes unsupported or if requirements exceed its capabilities.

### Conditions for revisiting

- If Infisical becomes unsupported or loses critical features, revisit the secret manager selection.
- If the platform adopts a CI provider with native secret scanning (e.g., GitHub Advanced Security), evaluate replacing gitleaks with the native scanner.
- If full-history scans become computationally infeasible due to repository size, revisit the scan strategy.

## Consequences

### Positive

- **Zero committed secrets** eliminates accidental credential exposure through
  repository access, forks, or CI artifact leaks.
- **CI-authoritative scanning** prevents regression at merge time — a
  bypassable pre-commit hook is no longer the sole control.
- **Clear fixture convention** enables realistic tests without false positives
  blocking development.
- **Existing runbook coverage** — incident response, rotation, and revocation
  procedures are already documented in
  `docs/runbooks/security/respond-to-secret-leak.md`.

### Negative

- **Scanner false positives** require triage and allowlist maintenance.
- **Full-history scans** are computationally expensive for large repositories;
  may require scheduled execution rather than per-PR.
- **Fixture allowlist review** — allowlists require periodic review to prevent
  stale entries from masking real secrets.

## Compliance and Migration

### Existing noncompliant paths

52 potential secret findings identified by repowise security scan. These are
potential findings pending classification — not confirmed live secrets.
Remediation of individual findings is tracked in sprint issues, not in this ADR.

### Migration owner

Security Team

### Enforcement mechanism

- **Pre-commit:** gitleaks hook in `.pre-commit-config.yaml` (exists, supplemental)
- **CI:** gitleaks or equivalent as required check (planned, authoritative)
- **Server-side:** GitHub push protection (planned)
- **Manifest hygiene:** `scripts/ci/check_manifest_secret_hygiene.py` (exists)
- **Path/env hygiene:** `scripts/ci/check_path_and_env_hygiene.py` (exists)

### Exception process

Scanner allowlist entries with structured justification (path, owner, expiry,
reason) serve as documented exceptions. Allowlist entries expire and require
renewal.

### Rollback strategy

CI secret scan can be temporarily set to advisory (non-blocking) during
migration. Pre-commit hooks remain active. Rollback to pre-commit-only is
possible but reduces the control posture.

### Evidence required to transition to Accepted (fully implemented)

- CI-authoritative gitleaks scan is a required status check
- GitHub push protection enabled at repository level
- Scanner allowlist file with structured justification entries
- Scheduled full-repository scan configured (monthly)
- Zero unallowlisted potential secret findings in CI scan

## Current Enforcement (Exists)

- `docs/security/secrets-management.md` — Infisical architecture and path structure
- `docs/runbooks/security/respond-to-secret-leak.md` — SEV1-SEV4 incident response runbook
- `docs/governance/manifest-secret-injection-policy.md` — K8s secret injection policy with CI enforcement
- `scripts/ci/check_manifest_secret_hygiene.py` — manifest secret hygiene CI check
- `scripts/ci/check_path_and_env_hygiene.py` — path and env template hygiene CI check
- Pre-commit gitleaks hook in `.pre-commit-config.yaml` (supplemental, bypassable)

## Planned Enforcement (Not Yet Existing)

- CI-authoritative gitleaks scan as required status check
- GitHub push protection enabled at repository level
- Scanner allowlist file with structured justification entries
- Scheduled full-repository scan (monthly)

## References

- `docs/security/secrets-management.md` — Infisical architecture and path structure
- `docs/runbooks/security/respond-to-secret-leak.md` — Incident response runbook
- `docs/governance/manifest-secret-injection-policy.md` — K8s secret injection policy
- ADR-004: JWT + API Key Authentication Strategy
- ADR-009: JWT + API Key Hybrid Authentication
- `.pre-commit-config.yaml` — gitleaks hook configuration
