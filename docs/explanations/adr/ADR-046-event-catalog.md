# ADR-046: Event Catalog — Semantic Inventory of Record for Domain and Integration Events

## Status

Accepted

## Context

Fabric_4L publishes events across multiple layers and bounded contexts: Layer 1 ingests data and dispatches via transactional outbox, Layer 4 produces workflow replay envelopes, Layer 7 emits billing lifecycle events, and the API gateway projects state changes to the frontend. Over time, this has led to:

- No single source of truth for what events exist, what they mean, and who owns them.
- Consumers inventing their own event names for the same semantic fact, violating the single-source-of-truth principle.
- Raw provider webhooks (e.g., Stripe) being treated as domain events instead of being normalized through an anti-corruption layer.
- Difficulty answering operational questions: What is the partition key? What is the SLO? Who consumes this? What happens on replay?
- Audit records, verification evidence, and financial journal entries being conflated with domain events.

The Schema Registry (`contracts/jsonschema/`, `contracts/openapi/`) answers "Is this payload structurally valid?" It does not answer "Why does this event exist, who owns it, and how is it used?"

## Decision

We establish the **Event Catalog** as the authoritative, searchable, machine-readable semantic inventory of every canonical domain or integration event intentionally published by Fabric_4L.

### Repository structure

```
contracts/event-catalog/
  event-entry.schema.json         # JSON Schema that validates every catalog entry
  registry.yaml                   # Top-level aggregator of all domain catalogs
  domains/
    billing.yaml                  # Events owned by layer7-billing
    identity.yaml                 # Events owned by identity-team (stub)
    knowledge.yaml                # Events owned by layer3-knowledge (stub)
    agents.yaml                   # Events owned by layer4-agents (stub)
  consumers/
    api.yaml                      # API gateway subscriptions
    layer4-agents.yaml            # Agentic workflow engine subscriptions
    analytics.yaml                # Analytics pipeline subscriptions
  generated/
    ownership-matrix.json         # Event → owner (diffable in PRs)
    producer-consumer-graph.json  # Producer → consumers adjacency list
```

### Event classification

The catalog distinguishes four event classes and does not collapse them:

- **DOMAIN_EVENT** — A first-class semantic fact about the business, emitted by the owning bounded context. Example: `billing.subscription.activated.v1`.
- **INTEGRATION_EVENT** — A normalized event crossing a bounded context boundary, still owned by one context. Example: a normalized inter-layer event.
- **PROVIDER_OBSERVATION** — A normalized record of a third-party provider state change, stored in the durable webhook inbox and anti-corruption layer before causing domain events.

The following are **not** domain events and must remain in their own catalogs:

- **Audit records** — who did what and when (see audit log).
- **Verification evidence** — proof artifacts for truth objects.
- **Financial journal entries** — immutable ledger postings.

These may be cross-linked via correlation and causation identifiers, but they must not be advertised as interchangeable domain events.

### Event ownership rule

Only the owning bounded context may emit the canonical event. Consumers must not re-emit the same semantic event under a different name.

Allowed:
```
Layer 7 Subscription context
  -> billing.subscription.activated.v1
```

Not allowed:
```
Gateway
  -> gateway.subscription.enabled.v1

Layer 4
  -> agent.subscription.activated.v1
```

The gateway or Layer 4 may publish a separate event representing a fact they genuinely own, but they cannot restate Layer 7’s subscription truth.

### Delivery semantics

The architecture accepts **at-least-once** transport and obtains exactly-once domain or financial effect through:

- Stable event IDs (UUID v4 or ULID).
- Idempotent consumer handlers keyed by `consumer_effect_key` (typically `event.id`).
- Transactional outbox in the producer service.
- Unique constraints on consumer-side inbox tables or projection tables.
- Source-effect uniqueness: the same causation chain must not produce duplicate business effects.

### Status lifecycle

- **DRAFT** — Event is normatively defined but not yet wired in production.
- **ACTIVE** — Event is currently emitted by the producer.
- **DEPRECATED** — Event is scheduled for removal; migration path documented.
- **SUNSET** — Event is no longer emitted; consumers must have migrated.

### Machine-readable validation

A CI gate (`scripts/ci/validate-event-catalog.py`) enforces:

1. Every emitted event type has a catalog entry.
2. Every catalog entry has a registered envelope schema.
3. Every canonical event has a bounded-context owner.
4. No multiple producers claim authority for the same event.
5. Every active consumer declares support for the published version.
6. No removal of an event while active consumers remain.
7. No reuse of an existing event name for changed semantics.
8. Sensitive payload classification is consistent.
9. Every event documents topic, partition key, and replay behavior.
10. Every consumer subscription is present in the catalog.

## Consequences

### Positive

- Single semantic inventory for all domain and integration events.
- Clear ownership and consumer contracts reduce cross-team coordination cost.
- CI gate prevents orphaned events, duplicate producers, and untracked consumer drift.
- Generated views (ownership matrix, producer-consumer graph) are diffable in PRs.
- Foundation for future AsyncAPI generation, event search UI, and runtime discovery.

### Negative

- New events require a catalog entry and schema registration, adding overhead for fast experiments.
- Consumer teams must update their registry file when subscribing to a new event or version.
- Deprecation requires coordination with all active consumers; the gate enforces this.

### Neutral

- The catalog is not the broker, the runtime audit log, or the financial ledger. It is metadata about events, not the events themselves.
- AsyncAPI generation from the catalog is deferred to a follow-up PR.

## Related

- ADR-023: Billing Service Extraction — the billing domain is the first mature bounded context to adopt the catalog.
- `contracts/schema-index.json` — the canonical registry of all contract artifacts, now includes event-catalog schemas.
- `docs/governance/behavior-first-testing.md` — the readiness ladder applies to event-catalog gate behavior.

## References

- `contracts/event-catalog/event-entry.schema.json`
- `contracts/event-catalog/registry.yaml`
- `scripts/ci/validate-event-catalog.py`
