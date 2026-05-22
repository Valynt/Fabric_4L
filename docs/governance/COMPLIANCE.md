# Compliance

Value Fabric compliance posture and control mapping.

For full details, see:

- [Control Matrix](docs/compliance/control-matrix.md)
- [Governance Implementation Reference](docs/compliance/governance-implementation-reference.md)
- [Controls Mapping](docs/audit/controls-mapping-updated.md)
- [Evidence Index](docs/audit/evidence-index.md)
- [Contract Exception Policy](docs/governance/contract-exception-policy.md)

## Frameworks

- SOC 2 Type II alignment
- OWASP Top 10 coverage
- SLSA Build Level 2 provenance

## Test Integrity Policy

- Synthetic coverage inflation tests are prohibited.
- Do not add tests whose primary purpose is to execute lines without asserting user-facing behavior, contract guarantees, tenant isolation, or security outcomes.
- Coverage improvements must come from real tests that validate business logic, API contracts, failure modes, and hostile multi-tenant scenarios.
- CI and code review must reject placeholder tests that only boost percentage metrics.
