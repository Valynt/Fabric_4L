# Supply Chain Security Gate

This directory defines the production gate for SBOM, dependency, container, vulnerability, license, and artifact-signing controls.

The gate is intentionally split between:

- CI scanner workflows: `.github/workflows/security-gates.yml` and `.github/workflows/supply-chain.yml`
- Local deterministic checks: `python scripts/ci/supply_chain_gate.py`
- Policy regression tests: `tests/supply_chain/`

## Required Commands

Run these before a production-readiness handoff when dependency, Dockerfile, workflow, or release evidence behavior changes:

```bash
pnpm sbom
pnpm audit:ci
pnpm container:scan
pytest tests/supply_chain/
```

## Control Summary

| Control | Production Requirement | Evidence |
|---|---|---|
| SBOM | CycloneDX source SBOM on PRs; CycloneDX and SPDX image SBOMs on release builds | `*-sbom.cdx.json`, `*-sbom.spdx.json`, `sbom-summary.json` |
| Dependency lockfiles | Root and frontend pnpm lockfiles plus service uv lockfiles are committed and frozen | `pnpm-lock.yaml`, `apps/web/pnpm-lock.yaml`, `services/*/uv.lock` |
| Vulnerability gate | Critical and high findings block production promotion unless an approved exception exists | SARIF, audit JSON, `vulnerability-summary.json` |
| Containers | Production Dockerfiles use patch-pinned base image tags, non-root users, health checks, and CI scans | Dockerfiles, Trivy SARIF |
| Licenses | Forbidden reciprocal/network-copyleft licenses are blocked from production dependencies | `license-report-*` artifact |
| Signatures | Release images and SBOM/provenance artifacts are verified with Cosign and GitHub OIDC | provenance and signature artifacts |

## Standards Alignment

- NIST SSDF: protect software, produce well-secured software, and respond to vulnerabilities.
- OWASP SCVS: dependency inventory, software authenticity, secure build pipeline, vulnerability management, and artifact provenance controls.

