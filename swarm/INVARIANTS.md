# Invariant Contracts (Frozen Anchor for Swarm Workers)

Adopted verbatim from release/v1/launch-contract.yaml non_negotiable_invariants + task invariants. Workers MUST NOT violate:

1. No parallel gate/readiness/risk/evidence system; compose existing canonical gates.
2. Tenant identity resolved/enforced by trusted backend code; missing/invalid/conflicting tenant context fails closed.
3. Durable business data only in approved authoritative stores; cache/queue/graph/search/object-storage/telemetry tenant-scoped.
4. Generated contracts regenerated from source of truth, never hand-edited.
5. Tests, coverage thresholds, security checks, type checks may not be weakened; no blanket ignores.
6. Queue payload tenant IDs must not override authenticated tenant context.
7. Signed URLs embed tenant scope + expiry; neither client-controllable; 404-vs-403 must not reveal cross-tenant existence.
8. Graph queries/vector searches always carry tenant filters; unauthorized tool invocations rejected + audited.
9. No commits/pushes/merges/tags/deploys by workers; Publisher only, after independent review.
10. No compatibility layers for unreleased behavior; no modifying unrelated files.
11. Type-escape ratchet: no net-new Any / type: ignore beyond approved baseline.
12. Secure error envelope: no str(exc) in HTTP responses; structured domain-safe messages only.
