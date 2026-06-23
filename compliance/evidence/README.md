# Compliance Evidence Artifact Pipeline

This directory defines the lightweight compliance evidence pipeline used before formal SOC 2, ISO 27001, HIPAA, or GDPR audits. It standardizes how CI and local release preparation collect control evidence without running heavyweight tests or scans inside the collector itself.

## Commands

```bash
pnpm evidence:build
pnpm evidence:validate
```

`pnpm evidence:build` writes a timestamped bundle under `artifacts/compliance/evidence/`. The generated bundle directory is immutable by convention: the collector refuses to overwrite an existing bundle path and writes a `PUBLISHED.json` marker plus a `bundle-manifest.json` with SHA-256 hashes for every generated evidence file.

`pnpm evidence:validate` checks this source manifest, required templates, controls mapping, and the latest generated bundle if one exists.

## Evidence Sources

The collector summarizes already-produced repository and CI artifacts:

- test reports and JUnit files from `artifacts/`, coverage outputs, and Playwright results;
- security scan reports, SARIF files, vulnerability outputs, and security workflow definitions;
- SBOM files from CI artifacts or supply-chain workflow definitions;
- backup and restore verification outputs from recovery artifacts and runbooks;
- release metadata from Git state, package metadata, workflow files, and lockfile hashes.

Missing evidence is recorded as a gap in the generated bundle instead of being silently ignored.

## Publication Rules

- Publish only generated directories under `artifacts/compliance/evidence/<timestamp>-<sha>/`.
- Do not edit a published bundle in place.
- If evidence must be corrected, generate a new bundle and keep the prior bundle for audit history.
- Store long-lived evidence in the approved artifact repository or immutable object storage with retention matching `controls_mapping.md`.
