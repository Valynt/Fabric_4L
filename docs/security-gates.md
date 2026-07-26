# Security Gates: DAST + SBOM + Regression

This document explains the CI security gates enforced by `.github/workflows/security-gates.yml` and how to run equivalent checks locally.

## What is gated in CI

The `Security Gates` workflow now includes:

1. **DAST against an ephemeral stack**
   - Starts `docker-compose.full.yml` with local CI-safe environment values.
   - Waits for public health endpoints.
   - Runs OWASP ZAP baseline scans against:
     - `http://127.0.0.1:8001` (Layer 1 API)
     - `http://127.0.0.1:8002` (Layer 2 API)
     - `http://127.0.0.1:8003` (Layer 3 API)
     - `http://127.0.0.1:8004` (Layer 4 API)
     - `http://127.0.0.1:8005` (Layer 5 API)

2. **SBOM generation for each build image artifact**
   - Builds each layer image.
   - Generates a CycloneDX SBOM (`*-sbom.cdx.json`) using Trivy.

3. **SBOM vulnerability policy gate + artifact upload**
   - Scans each SBOM and fails on `HIGH,CRITICAL` vulnerabilities.
   - Uploads SBOM and vulnerability SARIF per artifact.

4. **Mandatory Security Regression Gate** (Sprint 4 enhancement)
   - Runs `scripts/ci/mandatory_security_regression_gate.sh`
   - Includes I-02 production fail-closed tests for Layer 2 and Layer 5
   - Includes tenant boundary, auth regression, and rate limit checks
   - Includes frontend contract guards and critical E2E skip-valve guards
   - Includes Kubernetes hardening checks
   - Fails closed if required suites are missing
   - Evidence written to `fabric_audit/` (repo-relative)
   - See [I-04 Evidence](fabric_audit/i04_mandatory_security_regression_gate_evidence.md)

5. **Release evidence bundle**
   - Collects DAST + SBOM + security scan artifacts.
   - Publishes `release-security-evidence-<sha>` for release/audit evidence.

6. **Semgrep CE full SAST scan** (`Semgrep CE Full Scan (SAST)`)
   - Uses the exact Semgrep version in the workflow-level `SEMGREP_VERSION`.
     Both Semgrep jobs consume this single reviewed pin.
   - Scans with the curated rules in `config/semgrep/registry/`, which are an
     intentionally narrowed subset of the rules formerly loaded at runtime from
     `p/security-audit`, `p/secrets`, `p/owasp-top-ten`, and the Python,
     TypeScript, React, Docker, Kubernetes, and GitHub Actions packs. This is
     not a full replacement of those packs. The remaining local `.semgrep/`
     rules continue to load alongside that snapshot.
   - Validates every checked-in Semgrep configuration and parses a generated
     SARIF document in a smoke step before the repository scan.
   - Writes both **JSON** (`semgrep-full.json`) and **SARIF**
     (`semgrep-full.sarif`) output so findings can be inspected independently of
     the GitHub upload.
   - Fails closed on ERROR-severity findings by reading Semgrep's own JSON
     `extra.severity` field (the SARIF `result.level` is not authoritative for
     Semgrep CE rules).
   - Uploads SARIF to the GitHub Security tab (category `semgrep-full-scan`).
   - Runs with `--metrics off` (Semgrep CE only, no platform token).
   - After the scan, `scripts/security/collect_scan_coverage.py` generates a
     deterministic coverage record and publishes a job summary, even when the
     scan fails or finds issues. The summary shows the Semgrep version, scan
     mode, candidate/eligible/scanned/skipped file counts, active rulesets, and
     the SARIF upload status.
   - **GitHub Tool Status limitation:** Semgrep CE SARIF does not populate
     `run.artifacts`, so GitHub Code Scanning cannot derive a scanned-files
     summary for this third-party tool. The repository-owned coverage evidence
     (`semgrep-scan-evidence-<sha>`) provides the independently verifiable
     scanned-file manifest instead.

7. **Trivy repository scan** (`Repository Scan (Trivy fs + IaC + secrets)`)
   - Filesystem scan of the repo: dependency vulnerabilities in
     lockfiles/requirements, secret detection, and IaC misconfiguration checks
     (Dockerfiles, Compose, Kubernetes manifests, Terraform).
   - Fails on `HIGH,CRITICAL` (unfixed vulnerabilities are ignored).
   - Complements the per-image `Container Scan (Trivy)` matrix job, which
     continues to scan each built layer image with `vuln,secret,config`
     scanners and per-layer SARIF categories.

8. **OSV-Scanner** (Google official reusable workflows, pinned)
   - `OSV-Scanner (PR diff)`: on pull requests, scans base vs head against the
     OSV.dev database and fails only when the PR introduces *new* known
     vulnerabilities. SARIF is uploaded to code scanning.
   - `OSV-Scanner (full repository)`: on push and the weekly schedule, performs
     a full recursive scan and uploads SARIF (report-only).

9. **OpenSSF Scorecard** (`OpenSSF Scorecard`)
   - Runs on pushes to `main` and on the weekly schedule.
   - Evaluates repository supply-chain posture (branch protection, token
     permissions, pinned dependencies, SAST coverage, etc.).
   - Uploads SARIF to the Security tab (category `ossf-scorecard`) and
     publishes results to the OpenSSF REST API via OIDC (`publish_results:
     true`) so the Scorecard badge/API stay current. If the OpenSSF publisher
     rejects the multi-job workflow shape, set `publish_results: false` and
     rely on the SARIF/artifact outputs.

10. **Required merge gate check**
   - A dedicated PR job named **`Security Gates Required`** depends on:
     - `DAST (OWASP ZAP baseline)`
     - all matrix runs in `SBOM + Policy (...)`
     - `Route Auth Dependency Gate`
     - `mandatory-security-regression`

## Configure branch protection (required status check)

The canonical required context for the mandatory regression control is
**`mandatory-security-regression`**. Branch protection must restrict this
context to the GitHub Actions app and enforce it for administrators. See
`docs/governance/mandatory-security-regression-merge-policy.md` for the
governed contract and emergency exception process.

Recommended:
- Keep `Security Gates` workflow required for pull requests.
- Enable “Require branches to be up to date before merging”.

> Note: GitHub required status checks are repository settings and cannot be fully enforced only from workflow YAML.

## Local runbook for security gates

From repo root:

### 1) Start ephemeral stack

```bash
cd value-fabric
cat > .env << 'EOF'
OPENAI_API_KEY=dummy-key-for-local
ANTHROPIC_API_KEY=dummy-key-for-local
JWT_SECRET=local-jwt-secret
NEO4J_PASSWORD=valuefabric
EOF

docker compose up -d --build
```

### 2) Wait for API health

```bash
for target in \
  "http://localhost:8001/health" \
  "http://localhost:8002/health" \
  "http://localhost:8003/health" \
  "http://localhost:8004/health" \
  "http://localhost:8005/api/v1/health"; do
  until curl -fsS "$target" >/dev/null; do
    sleep 5
  done
  echo "Healthy: $target"
done
```

### 3) Run OWASP ZAP baseline DAST

```bash
mkdir -p ../zap-reports
for target in \
  "layer1:http://127.0.0.1:8001" \
  "layer2:http://127.0.0.1:8002" \
  "layer3:http://127.0.0.1:8003" \
  "layer4:http://127.0.0.1:8004" \
  "layer5:http://127.0.0.1:8005"; do
  name="${target%%:*}"
  url="${target#*:}"
  docker run --rm --network host \
    -v "${PWD}/../zap-reports:/zap/wrk:rw" \
    ghcr.io/zaproxy/zaproxy:stable \
    zap-baseline.py \
    -t "$url" \
    -J "${name}-zap-report.json" \
    -r "${name}-zap-report.html" \
    -w "${name}-zap-warnings.md" \
    -m 5
done
```

### 4) Build images and generate/scan SBOMs

```bash
cd ..
mkdir -p sbom-reports

for layer in \
  layer1-ingestion \
  layer2-extraction \
  layer3-knowledge \
  layer4-agents \
  layer5-ground-truth \
  layer6-benchmarks; do
  docker build -t "${layer}:local" "services/${layer}"

  trivy image --format cyclonedx --output "sbom-reports/${layer}-sbom.cdx.json" "${layer}:local"

  trivy sbom --exit-code 1 --ignore-unfixed \
    --severity HIGH,CRITICAL \
    --format sarif \
    --output "sbom-reports/${layer}-sbom-vuln.sarif" \
    "sbom-reports/${layer}-sbom.cdx.json"
done
```

### 5) Capture release evidence locally

```bash
mkdir -p release-security-evidence
cp -r zap-reports release-security-evidence/
cp -r sbom-reports release-security-evidence/

echo "Security evidence generated at $(date -u +"%Y-%m-%dT%H:%M:%SZ")" > release-security-evidence/SECURITY_EVIDENCE_MANIFEST.md
```

### 6) Run the static scanners locally

```bash
# Semgrep CE (same reviewed binary and rules as CI; read the current pin from
# .github/workflows/security-gates.yml env.SEMGREP_VERSION before running)
# Use sed for reliable extraction regardless of YAML whitespace/quoting:
SEMGREP_VERSION=$(sed -n "s/.*SEMGREP_VERSION:[[:space:]]*['\"]\\?\\([^'\" ]*\\)['\"]\\?.*/\\1/p" \
  .github/workflows/security-gates.yml | head -1)
pip install "semgrep==${SEMGREP_VERSION}"
semgrep scan \
  --config config/semgrep/registry/ --config .semgrep/ \
  --metrics off --exclude 'archive/**' --exclude 'docs/archive/**'

# Trivy repository scan (vuln + secret + IaC misconfig)
trivy fs --scanners vuln,secret,misconfig \
  --severity HIGH,CRITICAL --ignore-unfixed \
  --skip-dirs archive,docs/archive,node_modules .

# OSV-Scanner full recursive scan
osv-scanner scan -r .

# OpenSSF Scorecard (read-only GitHub token required; source it from a
# secure credential store rather than typing it inline)
export GITHUB_AUTH_TOKEN="$(<path-to-secure-token-source>)"
scorecard --repo=github.com/bmsull560/Fabric_4L
```

### 6a) Generate Semgrep scan coverage evidence locally

The CI job emits both JSON and SARIF. To produce the same repository-owned
coverage evidence locally, run the same Semgrep command CI uses and then call
the reporting utility:

```bash
semgrep scan \
  --config config/semgrep/registry/ --config .semgrep/ \
  --metrics off \
  --exclude 'archive/**' --exclude 'docs/archive/**' \
  --verbose \
  --json-output semgrep-full.json \
  --sarif-output semgrep-full.sarif

python3 scripts/security/collect_scan_coverage.py \
  --json-path semgrep-full.json \
  --sarif-path semgrep-full.sarif \
  --output-dir artifacts/security/semgrep \
  --scan-root . \
  --exclude 'archive/**' --exclude 'docs/archive/**' \
  --scan-mode full \
  --setup-type python-package \
  --configuration "config/semgrep/registry/" \
  --configuration ".semgrep/"
```

This writes:

- `artifacts/security/semgrep/scan-coverage.json` — machine-readable evidence
  record.
- `artifacts/security/semgrep/scanned-files.txt` — deterministic, sorted
  repository-relative manifest of files Semgrep processed.
- `artifacts/security/semgrep/skipped-files.json` — skipped files with reasons
  from Semgrep's own verbose output.
- `artifacts/security/semgrep/job-summary.md` — markdown table suitable for
  GitHub Actions step summaries.

The evidence record intentionally reports `null` or `unavailable` for any
field that cannot be derived from the Semgrep output, and lists the reason in
`reporting_limitations`. One expected limitation is that Semgrep CE SARIF does
not include `run.artifacts`, so GitHub Code Scanning cannot show a scanned-files
summary for this third-party tool; the repository-owned evidence provides that
manifest instead.

### 7) Teardown

```bash
cd value-fabric
docker compose down -v
```

## Artifacts produced in CI

- `dast-zap-reports` (ZAP JSON/HTML/markdown + compose logs)
- `sbom-<layer>` (CycloneDX SBOM + SBOM vulnerability SARIF)
- `semgrep-full-scan-<sha>` (Semgrep CE SARIF)
- `semgrep-scan-evidence-<sha>` (Semgrep JSON, `scan-coverage.json`, `scanned-files.txt`, `skipped-files.json`, and `job-summary.md`)
- `trivy-repo-scan-<sha>` (Trivy filesystem/IaC/secret SARIF)
- `OSV Scanner SARIF file` (uploaded by the OSV-Scanner reusable workflows)
- `openssf-scorecard-<sha>` (Scorecard SARIF)
- `release-security-evidence-<sha>` (aggregate evidence bundle)

These artifacts are suitable to attach to release records and security audit evidence.
