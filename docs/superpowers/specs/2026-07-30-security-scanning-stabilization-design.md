# Security Scanning Stabilization Design

## Objective

Make scanner execution, findings, runtime failure, and evidence failure independently observable and fail closed without reducing any severity threshold or security control.

## Architecture

The repository retains specialized scanners but assigns one canonical owner to each overlapping control. `security-gates.yml` owns broad SAST, secret, Trivy, baseline DAST, and the PR security aggregator; `dependency-scan.yml` owns lockfile dependency scanning; `supply-chain-integrity.yml` owns SBOM, Grype, signature, and release evidence; `penetration-testing.yml` owns controlled full active DAST. Release `sbom.yml` is only a trigger adapter to the canonical reusable supply-chain workflow.

Machine-readable inventory and normalized findings live in `security/scanning/`. Workflow contract tests reject mutable CodeQL actions, manufactured DAST output, unconditional supply-chain success claims, and stale duplicate release SBOM implementations.

## Failure semantics

A scanner report is trusted only after the process runs, its exit is classified, its output exists, and its schema is validated. Finding exits remain distinct from runtime exits. Evidence is uploaded after findings when possible, but a final enforcement step fails on policy-blocking findings, scanner/runtime failures, malformed reports, missing reports, or unexpected skipped controls.

## Validation and completion

Static workflow tests and YAML parsing run locally. Heavy scanners, image builds, SARIF upload, artifact upload, required checks, merge, and post-merge verification require authenticated GitHub, Docker/registry access, and vulnerability databases. The certification remains explicitly blocked rather than representing absent evidence as success.
