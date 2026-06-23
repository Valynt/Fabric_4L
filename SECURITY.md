# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| Latest on `main` | ✅ |
| Tagged releases (last 2 minor versions) | ✅ |
| Older versions | ❌ |

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report security issues privately:

1. Go to the repository's **Security** tab → **Report a vulnerability**, or
2. Email the maintainer directly (see GitHub profile).

Please include:

- A description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept (if safe to share)
- Affected versions or components
- Any suggested mitigations (optional)

## Response timeline

| Stage | Target |
|-------|--------|
| Acknowledgement | Within 48 hours |
| Initial assessment | Within 5 business days |
| Patch or mitigation | Within 30 days for critical/high; 90 days for medium/low |
| Public disclosure | Coordinated with reporter after patch is available |

## Security design principles

- **No secrets in code.** All credentials use environment variables. See `value-fabric/.env.example`.
- **JWT secret policy is environment-aware.** `JWT_SECRET` may use a local fallback only in
  development/test-like environments (`ENVIRONMENT`/`APP_ENV` of `dev`, `development`,
  `local`, `test`, `testing`, or `ci`). In non-dev environments, startup hard-fails if
  `JWT_SECRET` is unset/empty or left as `changeme-in-production`.
- **API keys use HMAC-SHA256** (not bcrypt) for throughput; bcrypt is reserved for user passwords.
- **JWT tokens** are short-lived and signed with `JWT_SECRET`.
- **Audit logs** are append-only and protected by a database trigger that prevents UPDATE/DELETE.
- **RBAC** is enforced via `GovernanceMiddleware` in `value-fabric/shared/identity/`.
- **CI uses short-lived OIDC credentials** — no long-lived secrets stored in GitHub Actions.

## Dependency management

Dependabot is configured (`.github/dependabot.yml`) to automatically open PRs for
dependency updates across Python, Node, and GitHub Actions ecosystems. All dependency
updates go through the standard PR review and CI gate process.

## SBOM policy

- CI generates a **CycloneDX SBOM** for every service/frontend container build in
  `.github/workflows/security-gates.yml`.
- SBOM files are uploaded as GitHub Actions artifacts (`sbom-<layer>`).
- The pipeline is gated to fail if SBOM generation or artifact upload fails.

## Supply chain integrity

All container images are signed with **Cosign keyless signing** (Sigstore/Fulcio OIDC)
and receive **SLSA provenance attestations** via `actions/attest-build-provenance@v2`.

Before deployment, run the verification script to validate signatures and provenance:

```bash
./scripts/security/verify-artifact.sh ghcr.io/bmsull560/fabric_4l/<layer>:sha-<commit>
```

For the complete supply chain security architecture, including NIST SSDF alignment,
SLSA level details, and the full production readiness checklist, see:

- **[Supply Chain Security Architecture](docs/supply-chain/SUPPLY_CHAIN_SECURITY.md)**
- **[Production Readiness Checklist](docs/PRODUCTION_READINESS_CHECKLIST.md)**

## Static analysis (SAST)

- **CodeQL** scans Python and JavaScript/TypeScript on every PR and push to main
  (`.github/workflows/codeql-analysis.yml`).
- **Bandit** scans all Python layers for security anti-patterns
  (`.github/workflows/security-gates.yml`, `.github/workflows/pr-checks.yml`).
- **OWASP ZAP** runs baseline DAST scans against an ephemeral stack on every PR.

## Development Authentication Bypass

For local development, the following environment variables may be set to bypass authentication:
- `DEV_AUTH_BYPASS=true` - Bypasses JWT validation and injects dev tenant context
- `ALLOW_DEV_AUTH_BYPASS=I_UNDERSTAND_RISK` - Legacy explicit acknowledgement token
- `AUTH_BYPASS_ENABLED=true` - Global auth bypass flag
- `ALLOW_INSECURE_DEV_AUTH_BYPASS=true` - Allows insecure dev auth bypass

**CRITICAL:** These variables MUST NEVER be set in production, staging, or any production-like environment. The `ProductionSafetyValidator` will reject startup if any bypass flag is enabled in production-like environments.

**CI Enforcement:**
- PR checks scan docker-compose files for bypass flags (`.github/scripts/check-dev-auth-bypass.sh`)
- ProductionSafetyValidator validates at service startup
- Security tests verify bypass rejection in production-like environments (`tests/security/test_dev_bypass.py`)

**Local Development (only accepted path):**
- Keep bypass flags out of committed compose baselines (CI preflight enforces this).
- Put bypass flags only in a local uncommitted env file such as `.env.dev` and an uncommitted compose override (for example `docker-compose.override.yml`).
- Never copy local override env variables to shared, staging, or production environments.
