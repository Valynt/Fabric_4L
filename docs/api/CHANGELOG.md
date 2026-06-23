# Fabric_4L API Changelog

## 1.0.0 — Initial production API

Initial production OpenAPI documentation release for Fabric_4L client integrations and security testing.

### Added

- Published `contracts/openapi/fabric-4l-api.json` as the production unified API contract at version `1.0.0`.
- Added complete operation descriptions for all documented endpoints.
- Added Fabric layer tags for endpoint ownership: `L1-Ingestion`, `L2-Extraction`, `L3-Knowledge`, `L4-Agents`, `L5-Ground-Truth`, `L6-Benchmarks`, and `Platform`.
- Added parameter descriptions for all path, query, and cookie parameters.
- Added schema and schema-property descriptions for all component schemas.
- Added request and response examples for write operations with JSON request bodies.
- Added CI validation for OpenAPI JSON validity and documentation completeness.
- Added the human-readable API guide in `docs/api/README.md`, including endpoint inventory, authentication guidance, error codes, and rate-limit tiers.

### Breaking changes from previous versions

- No prior production API version was published from this repository. Version `1.0.0` is the baseline production contract.
- The documented contract version changed from pre-production `0.1.0` to production `1.0.0`.
- Endpoint response/request shapes were not intentionally changed in this release; changes are documentation, examples, tagging, and validation metadata only.
