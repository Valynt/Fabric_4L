# Service Boundary Decision Scenarios

Real-world examples illustrating how to apply architecture clarity principles and draw effective service boundaries.

---

## Table of Contents

1. [Scenario 1: Splitting a Monolithic E-Commerce Service](#scenario-1-splitting-a-monolithic-e-commerce-service)
2. [Scenario 2: Value Fabric Layer Boundary Decisions](#scenario-2-value-fabric-layer-boundary-decisions)
3. [Scenario 3: Cross-Cutting Concern Placement](#scenario-3-cross-cutting-concern-placement)
4. [Scenario 4: Data Ownership Conflicts](#scenario-4-data-ownership-conflicts)
5. [Scenario 5: Team Structure Alignment](#scenario-5-team-structure-alignment)

---

## Scenario 1: Splitting a Monolithic E-Commerce Service

### Context

A growing e-commerce platform has a monolithic application handling:
- Product catalog and search
- Shopping cart and checkout
- Order management and fulfillment
- Payment processing
- User accounts and authentication
- Reviews and ratings
- Inventory management

**Pain Points:**
- Deployments require full regression testing (2+ hours)
- Inventory team blocked by checkout team changes
- Payment compliance changes require full redeployment
- Cannot scale checkout independently during flash sales
- New engineers take 3+ months to understand the codebase

### Decision Criteria

**Business Capability Analysis:**
- Catalog: Changes weekly (new products, pricing updates)
- Checkout: Changes rarely (core flow is stable)
- Payments: Changes quarterly (compliance, new providers)
- Inventory: Changes daily (stock levels, warehouse logic)
- Reviews: Changes monthly (moderation features)

**Team Structure:**
- Catalog team (3 engineers)
- Checkout team (2 engineers)
- Payments team (1 engineer + compliance officer)
- Inventory team (4 engineers)
- Platform team (auth, infrastructure)

**Data Ownership:**
- Products: Created by catalog team, read by checkout, search, reviews
- Orders: Created by checkout, read by fulfillment, analytics
- Payments: Created by checkout, owned by payments team
- Inventory: Owned by inventory team, read by catalog, checkout

### Boundary Decision Process

**Step 1: Identify Natural Boundaries**

Based on change rate and team structure, initial boundaries emerge:
```
Catalog Service   (changes weekly, catalog team)
Checkout Service  (changes rarely, checkout team)
Payments Service  (changes quarterly, payments team)
Inventory Service (changes daily, inventory team)
```

**Step 2: Analyze Data Coupling**

**Question:** Can these services own their data independently?

- **Products:** Catalog creates, but checkout needs real-time stock levels
- **Orders:** Checkout creates, but fulfillment needs order details
- **Payments:** Checkout initiates, but payments service owns transaction state

**Decision:** Use event-driven communication for state propagation

**Step 3: Define Communication Patterns**

**Synchronous (request/response):**
- Checkout → Inventory (check stock availability)
- Checkout → Payments (process payment)
- Catalog → Inventory (get stock levels for display)

**Asynchronous (events):**
- Inventory → Catalog (stock level changes)
- Checkout → Fulfillment (order created)
- Payments → Checkout (payment completed/failed)

**Step 4: Address Cross-Cutting Concerns**

**Authentication:** Extract to separate service (Platform team)
**Logging/Monitoring:** Infrastructure concern, not a service boundary
**Rate Limiting:** API Gateway responsibility

### Final Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Catalog    │    │   Checkout   │    │  Payments    │
│  - Products  │◄──►│  - Cart      │◄──►│  - Transactions│
│  - Search    │    │  - Orders    │    │  - Compliance │
└──────┬───────┘    └──────┬───────┘    └──────────────┘
       │                   │
       ▼                   ▼
┌──────────────┐    ┌──────────────┐
│  Inventory   │    │  Fulfillment │
│  - Stock     │    │  - Shipping  │
│  - Warehouses│    │  - Tracking  │
└──────────────┘    └──────────────┘
       │
       ▼
┌──────────────┐
│  Auth (Platform)│
│  - Identity   │
│  - Sessions  │
└──────────────┘
```

### Tradeoffs and Outcomes

**Benefits Achieved:**
- Checkout team can deploy independently (10 min vs 2 hours)
- Payments compliance updates don't affect checkout
- Inventory team can scale during warehouse operations
- New engineers can focus on one service (2 weeks vs 3 months)

**Costs Incurred:**
- Eventual consistency between inventory and catalog (1-2 second delay)
- Additional operational complexity (5 services vs 1)
- Need for distributed tracing to debug issues
- Contract testing overhead

**Mitigation Strategies:**
- Use read-through caching for inventory data in catalog
- Implement service mesh for observability
- Automated contract testing in CI/CD
- Platform team provides deployment tooling

### Lessons Learned

1. **Start with team structure** - Boundaries that align with teams reduce coordination
2. **Accept eventual consistency** - Not everything needs strong consistency
3. **Invest in observability** - Distributed systems need better monitoring
4. **Platform team is critical** - Cross-cutting concerns need dedicated ownership
5. **Evolution is ongoing** - Initial boundaries may need adjustment

---

## Scenario 2: Value Fabric Layer Boundary Decisions

### Context

Value Fabric is a six-layer pipeline for AI-powered business intelligence:
- Layer 1: Data ingestion (crawling, jobs)
- Layer 2: Extraction (LLM processing, RDF/OWL)
- Layer 3: Knowledge graph (Neo4j, GraphRAG)
- Layer 4: Agent workflows (LangGraph, ROI calculator)
- Layer 5: Ground truth validation
- Layer 6: Benchmarks and comparison

**Initial Design Question:** Should these be separate services or modules within one service?

### Decision Criteria

**Business Capability Analysis:**
- L1: Ingestion - I/O heavy, scales with data volume
- L2: Extraction - CPU heavy, scales with LLM usage
- L3: Knowledge - Memory heavy, scales with graph size
- L4: Agents - Complex workflows, scales with user activity
- L5: Validation - CPU/memory mixed, scales with evidence volume
- L6: Benchmarks - CPU heavy, scales with comparison requests

**Team Structure:**
- Ingestion team (L1)
- Extraction team (L2)
- Knowledge team (L3)
- Agents team (L4)
- Validation team (L5)
- Benchmarks team (L6)

**Change Rate:**
- L1: Changes frequently (new data sources, crawling logic)
- L2: Changes occasionally (new extraction patterns, LLM models)
- L3: Changes rarely (graph schema is stable)
- L4: Changes frequently (new agent workflows, tools)
- L5: Changes occasionally (new validation rules)
- L6: Changes occasionally (new benchmarks)

### Boundary Decision Process

**Step 1: Evaluate Service vs Module Boundaries**

**Question:** Should each layer be a separate service?

**Analysis:**
- **Pros of separate services:** Independent scaling, deployment, team autonomy
- **Cons:** Network latency, operational complexity, data transfer overhead

**Decision:** Each layer is a separate service because:
- Different scaling characteristics (I/O vs CPU vs memory)
- Different change rates enable independent deployment
- Team autonomy is critical for velocity
- Pipeline nature allows batch processing to mitigate latency

**Step 2: Define Data Flow Boundaries**

**Question:** How does data flow between layers?

**Analysis:**
- L1 → L2: Raw content → Structured entities
- L2 → L3: Entities → Graph relationships
- L3 → L4: Graph queries → Agent context
- L4 → L5: Agent outputs → Validation
- L5 → L6: Validated claims → Benchmark comparison

**Decision:** Unidirectional pipeline with message queues between layers
- Enables backpressure handling
- Allows batch processing for efficiency
- Supports replay/reprocessing if needed

**Step 3: Address Cross-Cutting Concerns**

**Tenant Context:**
- **Problem:** Every layer needs tenant_id for isolation
- **Anti-pattern:** Pass tenant_id as parameter through all layers
- **Solution:** AsyncLocalStorage with middleware injection (canonical contract)

**Tool Registry:**
- **Problem:** Agents need tools, but tools should be framework-agnostic
- **Anti-pattern:** Define tools separately for LangChain, CrewAI, etc.
- **Solution:** Schema-first tool registry with generated bindings

**Agent Output Shape:**
- **Problem:** Different agents produce different output formats
- **Anti-pattern:** Parse JSON from LLM responses
- **Solution:** Structured generation with Pydantic schema enforcement

### Final Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Layer 1    │    │   Layer 2    │    │   Layer 3    │
│  Ingestion   │───►│  Extraction  │───►│  Knowledge   │
│  Port: 8001  │    │  Port: 8002  │    │  Port: 8003  │
└──────────────┘    └──────────────┘    └──────────────┘
       │                  │                  │
       └──────────────────┴──────────────────┘
                    Message Queues
                    (Redis, Celery)
                    Tenant Context
                    (AsyncLocalStorage)

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Layer 4    │    │   Layer 5    │    │   Layer 6    │
│   Agents     │───►│  Validation  │───►│  Benchmarks  │
│  Port: 8004  │    │  Port: 8005  │    │  Port: 8006  │
└──────────────┘    └──────────────┘    └──────────────┘
       │
       ▼
┌──────────────┐
│  Tool Registry│
│  (Schema-First)│
└──────────────┘
```

### Tradeoffs and Outcomes

**Benefits Achieved:**
- Each layer scales independently (L1 for I/O, L2 for CPU, L3 for memory)
- Teams can deploy without coordination (L4 changes don't affect L1)
- Clear contracts between layers (OpenAPI, JSON Schema)
- Tenant context propagation is automatic and type-safe

**Costs Incurred:**
- Network latency between layers (mitigated by batch processing)
- Operational complexity (6 services to monitor)
- Message queue management (Redis, Celery)
- Need for distributed tracing

**Mitigation Strategies:**
- Batch processing to amortize network overhead
- Centralized observability (OpenTelemetry, Prometheus)
- Platform team provides infrastructure tooling
- Contract tests prevent breaking changes

### Lessons Learned

1. **Pipeline architecture works well** - Unidirectional flow simplifies boundaries
2. **Canonical contracts are critical** - Prevent drift between layers
3. **Cross-cutting concerns need special handling** - Tenant context, tools, outputs
4. **Platform team enables autonomy** - Infrastructure as a service
5. **Evolution is built-in** - Layers can be added/removed without affecting others

---

## Scenario 3: Cross-Cutting Concern Placement

### Context

A SaaS platform needs to implement:
- Authentication and authorization
- Logging and monitoring
- Rate limiting
- Audit logging
- Feature flags

**Question:** Where should these cross-cutting concerns live?

### Decision Criteria

**Characteristics of Cross-Cutting Concerns:**
- Required by multiple services
- Often have strict compliance requirements
- Need consistent implementation across services
- May change independently of business logic

### Boundary Decision Process

**Step 1: Categorize by Deployment Location**

**Infrastructure-Level (not service boundaries):**
- Logging: Sidecar or infrastructure
- Monitoring: Prometheus exporters, OpenTelemetry agents
- Tracing: OpenTelemetry SDKs in each service

**Gateway-Level (API Gateway responsibility):**
- Rate limiting: Per-endpoint, per-tenant
- Authentication: Token validation, OIDC flows
- Basic authorization: Role-based access control

**Service-Level (each service implements):**
- Business authorization: Domain-specific access rules
- Audit logging: Domain-specific events
- Feature flags: Domain-specific feature toggles

**Central Service (dedicated service):**
- User identity and profile management
- Permission management
- Audit log aggregation and querying

**Step 2: Define Communication Patterns**

**Authentication Flow:**
```
Client → API Gateway (validate token) → Service (receive tenant context)
```

**Authorization Flow:**
```
Service → Auth Service (check permissions) → Service (enforce decision)
```

**Audit Logging Flow:**
```
Service → Audit Service (async event) → Audit Service (store/query)
```

**Step 3: Address Edge Cases**

**Question:** What if a service needs custom rate limiting?

**Decision:** API Gateway provides default rate limiting, but services can implement additional limits if needed (e.g., expensive operations)

**Question:** What if audit logging needs to be synchronous?

**Decision:** Use a hybrid approach - critical events logged synchronously, informational events logged asynchronously

### Final Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                           │
│  - Authentication (token validation)                     │
│  - Rate limiting (per-tenant, per-endpoint)              │
│  - Request routing                                       │
│  - Basic authorization (role-based)                      │
└───────────────────┬─────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Service A   │ │  Service B   │ │  Service C   │
│  - Business  │ │  - Business  │ │  - Business  │
│    authz     │ │    authz     │ │    authz     │
│  - Audit     │ │  - Audit     │ │  - Audit     │
│    events    │ │    events    │ │    events    │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        ▼
                ┌──────────────┐
                │ Auth Service │
                │  - Identity  │
                │  - Permissions│
                │  - Audit log │
                └──────────────┘
```

### Tradeoffs and Outcomes

**Benefits Achieved:**
- Consistent authentication across all services
- Centralized rate limiting configuration
- Services focus on business logic, not infrastructure
- Audit logs are queryable in one place

**Costs Incurred:**
- API Gateway becomes critical infrastructure
- Auth service is a single point of failure (need HA)
- Services still need some auth logic (business authorization)
- Complexity in distributed auth flows

**Mitigation Strategies:**
- API Gateway high availability (multi-region, load balanced)
- Auth service with caching and fallback mechanisms
- Clear documentation of what each layer handles
- Contract tests for auth flows

### Lessons Learned

1. **Not all cross-cutting concerns are the same** - Some belong in infrastructure, some in gateway, some in services
2. **Layered auth is necessary** - Gateway handles identity, services handle business rules
3. **Centralized services need HA** - Auth service failure affects everything
4. **Clear boundaries reduce confusion** - Document who handles what
5. **Asynchronous for non-critical paths** - Audit logging can be async, auth cannot

---

## Scenario 4: Data Ownership Conflicts

### Context

Two teams need access to the same data:
- **Team A (Catalog):** Manages product information, pricing, descriptions
- **Team B (Analytics):** Needs product data for reporting, recommendations

**Question:** Who owns the product data, and how does Team B access it?

### Decision Criteria

**Data Ownership Principles:**
- The team that creates the data should own it
- The team that changes the data most frequently should own it
- Data should be accessed via APIs, not direct database access
- Accept duplication if it enables autonomy

### Boundary Decision Process

**Step 1: Determine Source of Truth**

**Analysis:**
- Team A creates product data (new products, updates)
- Team A changes product data frequently (pricing, descriptions)
- Team B only reads product data (never writes)

**Decision:** Team A owns product data as source of truth

**Step 2: Define Access Pattern**

**Option 1: Direct Database Access**
- Team B reads directly from Team A's database
- **Pros:** Fast, real-time
- **Cons:** Tight coupling, schema changes break Team B, bypasses business logic

**Option 2: API Access**
- Team B calls Team A's API for product data
- **Pros:** Loose coupling, Team A controls access, business logic enforced
- **Cons:** Network latency, potential performance issues

**Option 3: Data Replication**
- Team B maintains a copy of product data, updated via events
- **Pros:** Team B has autonomy, fast queries, no dependency on Team A's availability
- **Cons:** Eventual consistency, replication complexity

**Decision:** Option 3 (data replication) because:
- Team B needs to run complex analytics queries that would impact Team A's database
- Team B needs to augment product data with analytics-specific fields
- Team A's change rate is high, Team B needs stable data for reporting

**Step 3: Define Synchronization Strategy**

**Event-Based Replication:**
- Team A emits "ProductUpdated" events when data changes
- Team B consumes events and updates its replica
- Team B can request full sync if it falls behind

**Conflict Resolution:**
- Team A is always source of truth
- Team B's replica is read-only for analytics
- No conflicts because Team B never writes to product data

### Final Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Team A (Catalog)                      │
│  ┌──────────────┐    ┌──────────────┐                  │
│  │  Product API │◄──►│ Product DB   │                  │
│  └──────┬───────┘    └──────┬───────┘                  │
│         │                   │                            │
│         └─────────┬─────────┘                            │
│                   │                                      │
│            ProductUpdated events                         │
│                   │                                      │
└───────────────────┼──────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│                    Team B (Analytics)                     │
│  ┌──────────────┐    ┌──────────────┐                  │
│  │  Analytics   │◄──►│ Analytics DB │                  │
│  │  Engine      │    │ (replica)    │                  │
│  └──────────────┘    └──────────────┘                  │
│         ▲                                                   │
│         │                                                   │
│    Event consumer                                          │
└─────────────────────────────────────────────────────────┘
```

### Tradeoffs and Outcomes

**Benefits Achieved:**
- Team A can change database schema without affecting Team B
- Team B can run heavy analytics queries without impacting Team A
- Team B can augment data with analytics-specific fields
- Both teams have deployment autonomy

**Costs Incurred:**
- Eventual consistency (analytics data may be seconds/minutes behind)
- Replication complexity (event handling, error recovery)
- Storage costs (duplicate data)
- Need for sync monitoring

**Mitigation Strategies:**
- Team B can request real-time data via API for critical queries
- Event consumer with dead letter queue for error handling
- Monitoring for replication lag
- Regular full sync to handle missed events

### Lessons Learned

1. **Data ownership should follow creation and change frequency** - The team that creates and changes data owns it
2. **Replication is often better than shared databases** - Enables autonomy despite duplication
3. **Eventual consistency is acceptable for many use cases** - Analytics doesn't need real-time data
4. **Monitoring is critical for replication** - Need to know if sync is broken
5. **API fallback for critical paths** - Sometimes you need real-time data despite replication

---

## Scenario 5: Team Structure Alignment

### Context

A company has reorganized its teams:
- Old structure: Functional teams (frontend, backend, database, DevOps)
- New structure: Product teams (checkout, payments, catalog, user experience)

**Question:** How should service boundaries change to align with the new team structure?

### Decision Criteria

**Conway's Law:** Systems are constrained to produce designs that copy the communication structures of the organization.

**Goal:** Align technical boundaries with team structure to minimize coordination overhead.

### Boundary Decision Process

**Step 1: Map Old Boundaries to New Teams**

**Old Architecture:**
```
Frontend Service (frontend team)
Backend Service (backend team)
Database Service (database team)
DevOps Service (DevOps team)
```

**Problem:** Every feature requires coordination across 4 teams

**Step 2: Identify Natural Boundaries for New Teams**

**New Team Structure:**
- Checkout team (owns checkout flow end-to-end)
- Payments team (owns payment processing)
- Catalog team (owns product catalog)
- User Experience team (owns user accounts, UI)

**New Architecture:**
```
Checkout Service (checkout team)
Payments Service (payments team)
Catalog Service (catalog team)
User Service (user experience team)
```

**Step 3: Address Cross-Cutting Concerns**

**Question:** Who handles DevOps, database, infrastructure?

**Decision:** Create a Platform team that provides:
- Infrastructure as code
- Deployment pipelines
- Database as a service
- Monitoring and observability tools

**Step 4: Define Communication Between Product Teams**

**Question:** How do checkout, payments, and catalog teams coordinate?

**Decision:**
- Contract-first API design
- Regular cross-team sync meetings
- Shared API gateway for routing
- Event-driven communication for async updates

### Final Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Platform Team                         │
│  - Infrastructure                                        │
│  - Deployment pipelines                                  │
│  - Database as a service                                 │
│  - Monitoring tools                                      │
└───────────────────┬─────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Checkout    │ │  Payments    │ │  Catalog     │
│  (checkout   │ │  (payments   │ │  (catalog    │
│   team)      │ │   team)      │ │   team)      │
└──────────────┘ └──────────────┘ └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         ▼
                ┌──────────────┐
                │  User Service│
                │  (UX team)   │
                └──────────────┘
```

### Tradeoffs and Outcomes

**Benefits Achieved:**
- Each product team can deploy independently
- Reduced coordination overhead (feature changes don't require DevOps approval)
- Faster development (teams own their stack end-to-end)
- Clearer ownership and accountability

**Costs Incurred:**
- Platform team becomes critical infrastructure
- Need for strong contract governance (to prevent breaking changes)
- Potential duplication of effort (each team implements similar patterns)
- Onboarding complexity (new engineers need to learn platform tools)

**Mitigation Strategies:**
- Platform team provides golden path templates
- Automated contract testing in CI/CD
- Regular cross-team architecture reviews
- Shared libraries for common patterns

### Lessons Learned

1. **Align boundaries with team structure** - Conway's Law is real, embrace it
2. **Platform team is essential** - Cross-cutting concerns need dedicated ownership
3. **Contract governance becomes critical** - Autonomous teams need strong interfaces
4. **Golden paths reduce duplication** - Provide templates for common patterns
5. **Regular communication is still necessary** - Autonomous doesn't mean isolated

---

## Summary of Decision Heuristics

Across all scenarios, common decision patterns emerge:

**When to Draw a Boundary:**
- Different change rates
- Different team ownership
- Different scaling requirements
- Different compliance requirements
- Different failure domains

**When to Keep Together:**
- Always changes together
- Same team ownership
- Strong consistency required
- Shared database transactions
- Simple deployment is acceptable

**Communication Pattern Selection:**
- **Synchronous:** When immediate response is required
- **Asynchronous:** When eventual consistency is acceptable
- **Batch:** When high throughput is needed
- **Event-driven:** When multiple consumers need state changes

**Data Ownership Principles:**
- Creator owns the data
- Most frequent changer owns the data
- Access via APIs, not direct database
- Accept duplication for autonomy

**Cross-Cutting Concerns:**
- Infrastructure: Sidecars, agents
- Gateway: Auth, rate limiting, routing
- Service: Business logic, domain-specific concerns
- Central service: Identity, permissions, audit

Remember: **The right boundary is the one that solves your actual problems, not an ideal one from a textbook.**
