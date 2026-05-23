# Service Boundary Checklist

Actionable checklists for teams to use when clarifying architecture and defining service boundaries.

---

## Table of Contents

1. [Pre-Design Checklist](#1-pre-design-checklist)
2. [Boundary Definition Checklist](#2-boundary-definition-checklist)
3. [Validation Checklist](#3-validation-checklist)
4. [Evolution Checklist](#4-evolution-checklist)
5. [Operational Readiness Checklist](#5-operational-readiness-checklist)

---

## 1. Pre-Design Checklist

Use this checklist before drawing service boundaries to ensure you have the necessary context.

### Business Context

- [ ] **Business capabilities mapped**
  - List all distinct business capabilities in the system
  - Identify which capabilities change together
  - Note which capabilities have different stakeholders
  - Document success metrics for each capability

- [ ] **Change rate analysis completed**
  - Track how frequently each capability changes
  - Identify capabilities that change weekly vs monthly vs quarterly
  - Note which capabilities have strict compliance requirements
  - Document seasonal or event-driven change patterns

- [ ] **Team structure understood**
  - Map current team ownership of capabilities
  - Identify which teams are blocked by others
  - Note communication patterns between teams
  - Document team size and expertise distribution

### Technical Context

- [ ] **Current architecture documented**
  - Create dependency graph of existing components
  - Identify tight coupling points
  - Note data ownership and access patterns
  - Document current communication patterns

- [ ] **Data inventory completed**
  - List all data entities and their lifecycle
  - Identify which services create vs read vs update each entity
  - Note data consistency requirements (strong vs eventual)
  - Document data access patterns (direct DB vs API)

- [ ] **Performance requirements known**
  - Identify latency requirements for each capability
  - Note throughput requirements (requests per second)
  - Document scaling requirements (vertical vs horizontal)
  - Identify performance bottlenecks in current system

### Constraints and Requirements

- [ ] **Compliance requirements identified**
  - List regulatory requirements per capability (e.g., PCI, HIPAA, GDPR)
  - Note data residency requirements
  - Document audit logging requirements
  - Identify security classification per data type

- [ ] **Non-functional requirements documented**
  - Availability targets (e.g., 99.9% uptime)
  - Disaster recovery requirements (RTO, RPO)
  - Monitoring and observability requirements
  - Deployment frequency targets

- [ ] **Technical constraints known**
  - Budget constraints (infrastructure costs)
  - Team skill constraints (expertise available)
  - Legacy system dependencies
  - Third-party service limitations

---

## 2. Boundary Definition Checklist

Use this checklist when drawing service boundaries to ensure they are well-designed.

### Business Capability Alignment

- [ ] **Boundary aligns with business capability**
  - Service has a single, well-defined business purpose
  - Service name clearly describes its capability
  - Service responsibilities are cohesive (related functionality grouped)
  - Service scope is neither too broad nor too narrow

- [ ] **Change rate considered**
  - Service groups functionality that changes at similar rates
  - Service can be deployed independently of other services
  - Service changes don't require coordinated deployments
  - Service has a predictable release cadence

- [ ] **Team ownership clear**
  - One team owns the service end-to-end
  - Team has expertise to maintain the service
  - Team size is appropriate for service complexity
  - Team is not constantly blocked by other teams

### Data Ownership

- [ ] **Data ownership explicit**
  - Service owns its core data (source of truth)
  - Service controls write access to its data
  - Other services access data via defined APIs only
  - Data schema changes are controlled by owning team

- [ ] **Consistency model appropriate**
  - Strong consistency used where required (e.g., financial transactions)
  - Eventual consistency accepted where appropriate (e.g., analytics)
  - Consistency model documented and understood
  - Conflict resolution strategy defined

- [ ] **Data access patterns defined**
  - Read/write permissions documented
  - API contracts defined for data access
  - Caching strategy documented
  - Data retention policies defined

### Communication Patterns

- [ ] **Communication pattern appropriate**
  - Synchronous communication used for immediate responses
  - Asynchronous communication used for non-critical updates
  - Batch processing used for high-throughput scenarios
  - Event-driven communication used for state changes

- [ ] **Interface contracts defined**
  - API contracts documented (OpenAPI, GraphQL schema, etc.)
  - Request/response schemas defined
  - Error responses follow canonical shape
  - API versioning strategy defined

- [ ] **Coupling minimized**
  - Service doesn't know internal details of other services
  - Service doesn't make chatty calls to other services
  - Service can be tested in isolation
  - Service can be deployed independently

### Cross-Cutting Concerns

- [ ] **Authentication handled appropriately**
  - Authentication is not implemented in each service
  - Tenant context propagated via middleware
  - Service receives authenticated context from gateway
  - Service doesn't re-implement auth logic

- [ ] **Logging and monitoring defined**
  - Structured logging with correlation IDs
  - Metrics exposed for health and performance
  - Distributed tracing implemented
  - Alerting rules defined

- [ ] **Error handling consistent**
  - Errors follow canonical error shape
  - Errors are logged with sufficient context
  - Errors don't expose sensitive information
  - Error recovery strategies defined

---

## 3. Validation Checklist

Use this checklist before implementing to validate that boundaries are sound.

### Contract Validation

- [ ] **API contracts defined**
  - OpenAPI spec exists for all HTTP endpoints
  - GraphQL schema exists for GraphQL endpoints
  - Protobuf schemas exist for gRPC endpoints
  - AsyncAPI spec exists for event-driven endpoints

- [ ] **Contract tests written**
  - Provider tests verify service meets its contract
  - Consumer tests verify service can be used as expected
  - Contract tests run in CI/CD pipeline
  - Contract tests prevent breaking changes

- [ ] **Type safety ensured**
  - TypeScript types generated from contracts (frontend)
  - Client SDKs generated from contracts
  - Input validation enforced at boundaries
  - Output validation enforced at boundaries

### Dependency Validation

- [ ] **Dependency graph analyzed**
  - Dependency graph created for all services
  - Circular dependencies identified and resolved
  - Unexpected dependencies reviewed
  - Critical dependencies identified

- [ ] **Coupling measured**
  - Number of dependencies per service is reasonable (< 10)
  - No service depends on more than 3 layers of services
  - No service has a single point of failure dependency
  - Service can be tested without all dependencies running

- [ ] **Data flow validated**
  - Data flow diagram created
  - No direct database access across service boundaries
  - Data ownership is clear for all entities
  - Data synchronization strategy defined

### Testing Validation

- [ ] **Unit tests cover business logic**
  - Unit tests exist for all business logic
  - Unit tests can run without external dependencies
  - Unit tests achieve > 80% code coverage
  - Unit tests run quickly (< 5 minutes)

- [ ] **Integration tests cover boundaries**
  - Integration tests exist for all service boundaries
  - Integration tests use test doubles for external services
  - Integration tests verify contract compliance
  - Integration tests run in CI/CD pipeline

- [ ] **Contract tests prevent drift**
  - Consumer tests exist for all service consumers
  - Provider tests exist for all service providers
  - Contract tests run on every commit
  - Contract tests block PRs that break contracts

### Security Validation

- [ ] **Authentication tested**
  - Unauthenticated requests are rejected
  - Invalid tokens are rejected
  - Expired tokens are rejected
  - Tenant context is correctly extracted

- [ ] **Authorization tested**
  - Unauthorized requests are rejected
  - Role-based access control enforced
  - Resource-based access control enforced
  - Authorization bypass attempts are blocked

- [ ] **Data isolation tested**
  - Tenant A cannot read Tenant B data
  - Tenant A cannot write Tenant B data
  - Missing tenant context fails closed
  - Cross-tenant queries require explicit authorization

---

## 4. Evolution Checklist

Use this checklist when changing existing service boundaries.

### Pre-Evolution Analysis

- [ ] **Current pain points documented**
  - List specific problems with current boundaries
  - Measure impact of problems (e.g., deployment time, coordination overhead)
  - Identify stakeholders affected by problems
  - Quantify cost of current state

- [ ] **Proposed solution designed**
  - New boundary design documented
  - Migration strategy defined
  - Rollback strategy defined
  - Success criteria defined

- [ ] **Impact analysis completed**
  - All affected services identified
  - All affected teams identified
  - Data migration requirements documented
  - Client impact documented

### Migration Planning

- [ ] **Migration strategy chosen**
  - Strangler fig pattern for gradual migration
  - Parallel operation during transition
  - Feature flags for incremental rollout
  - Canary deployment for validation

- [ ] **Data migration planned**
  - Data migration script written
  - Data validation script written
  - Rollback plan for data migration
  - Data migration tested in staging

- [ ] **Client migration planned**
  - Client communication plan defined
  - Client deprecation timeline defined
  - Client migration guide written
  - Client support during migration defined

### Execution Monitoring

- [ ] **Monitoring in place**
  - Metrics for migration progress defined
  - Alerts for migration failures defined
  - Dashboards for migration visibility created
  - Log aggregation for migration debugging configured

- [ ] **Rollback triggers defined**
  - Clear criteria for when to rollback
  - Rollback procedure documented
  - Rollback tested in staging
  - Rollback communication plan defined

- [ ] **Stakeholder communication**
  - All affected teams notified
  - Migration timeline communicated
  - Support channels defined
  - Regular status updates scheduled

### Post-Evolution Validation

- [ ] **Success criteria met**
  - Original pain points resolved
  - Metrics show improvement
  - No new problems introduced
  - Stakeholders satisfied

- [ ] **Documentation updated**
  - Architecture diagrams updated
  - API documentation updated
  - Runbooks updated
  - Team ownership updated

- [ ] **Old boundaries decommissioned**
  - Old services decommissioned
  - Old APIs removed
  - Old data cleaned up
  - Old monitoring removed

- [ ] **Retrospective conducted**
  - What went well documented
  - What didn't go well documented
  - Lessons learned captured
  - Process improvements identified

---

## 5. Operational Readiness Checklist

Use this checklist before deploying a new service boundary to production.

### Infrastructure Readiness

- [ ] **Deployment pipeline configured**
  - CI/CD pipeline builds and tests service
  - Deployment to staging environment automated
  - Deployment to production environment automated
  - Rollback procedure automated

- [ ] **Infrastructure provisioned**
  - Compute resources allocated and sized appropriately
  - Database provisioned and configured
  - Caching layer provisioned if needed
  - Message queues provisioned if needed

- [ ] **Networking configured**
  - Service discovery configured
  - Load balancing configured
  - Network policies configured
  - DNS records configured

### Observability Readiness

- [ ] **Logging configured**
  - Structured logging implemented
  - Log aggregation configured
  - Log retention policy defined
  - Sensitive data excluded from logs

- [ ] **Metrics configured**
  - Business metrics defined and tracked
  - Technical metrics (latency, error rate, throughput) defined
  - Resource metrics (CPU, memory, disk) defined
  - Metrics dashboards created

- [ ] **Tracing configured**
  - Distributed tracing implemented
  - Trace propagation across boundaries
  - Trace sampling configured
  - Trace retention policy defined

- [ ] **Alerting configured**
  - Alert rules defined for critical metrics
  - Alert routing configured (who gets paged)
  - Alert escalation rules defined
  - Alert runbooks written

### Security Readiness

- [ ] **Authentication configured**
  - Authentication mechanism configured
  - Token validation configured
  - Token refresh configured
  - Authentication testing completed

- [ ] **Authorization configured**
  - Authorization rules configured
  - Role-based access control configured
  - Resource-based access control configured
  - Authorization testing completed

- [ ] **Network security configured**
  - TLS/SSL configured
  - Network segmentation configured
  - Firewall rules configured
  - DDoS protection configured

- [ ] **Secrets management configured**
  - Secrets stored in secure vault
  - Secrets rotation policy defined
  - Secrets access audited
  - No secrets in code or config

### Disaster Recovery Readiness

- [ ] **Backup strategy defined**
  - Database backup strategy defined
  - Backup retention policy defined
  - Backup restoration tested
  - Backup monitoring configured

- [ ] **High availability configured**
  - Multi-AZ deployment configured
  - Load balancing configured
  - Health checks configured
  - Auto-scaling configured

- [ ] **Disaster recovery tested**
  - Failover procedure tested
  - Recovery time objective (RTO) validated
  - Recovery point objective (RPO) validated
  - Disaster recovery runbook written

### Documentation Readiness

- [ ] **Architecture documented**
  - Service architecture diagram created
  - Data flow diagram created
  - Dependency diagram created
  - Architecture decision records (ADRs) written

- [ ] **API documented**
  - API documentation complete
  - API examples provided
  - Error response documentation complete
  - API versioning documented

- [ ] **Runbooks written**
  - Deployment runbook written
  - Troubleshooting runbook written
  - Incident response runbook written
  - Rollback runbook written

- [ ] **Onboarding guide written**
  - New engineer onboarding guide written
  - Development setup guide written
  - Testing guide written
  - Contribution guide written

---

## Quick Reference: Boundary Decision Heuristics

### When to Draw a Boundary

✅ **Draw a boundary when:**
- Capabilities change at different rates
- Different teams own the functionality
- Different scaling requirements exist
- Different compliance requirements exist
- Different failure domains are needed
- Strong consistency is not required across the boundary

### When to Keep Together

✅ **Keep together when:**
- Functionality always changes together
- Same team owns the functionality
- Strong consistency is required
- Shared database transactions are needed
- Deployment complexity would outweigh benefits

### Communication Pattern Selection

✅ **Use synchronous when:**
- Immediate response is required
- Caller needs to handle errors immediately
- Data freshness is critical
- Simple request/response pattern

✅ **Use asynchronous when:**
- Eventual consistency is acceptable
- Multiple consumers need the data
- High throughput is needed
- Caller doesn't need immediate response

✅ **Use events when:**
- State change needs to be communicated
- Multiple consumers need to react
- Decoupling is important
- Audit trail is needed

### Data Ownership Principles

✅ **Data ownership rules:**
- The team that creates data owns it
- The team that changes data most frequently owns it
- Access data via APIs, not direct database
- Accept duplication to enable autonomy
- Source of truth is always the owning service

---

## Summary

These checklists provide a structured approach to:

1. **Pre-Design:** Gather necessary context before drawing boundaries
2. **Boundary Definition:** Ensure boundaries are well-designed
3. **Validation:** Verify boundaries before implementation
4. **Evolution:** Safely change boundaries over time
5. **Operational Readiness:** Ensure boundaries are production-ready

Use these checklists iteratively as your system evolves. Architecture clarity is not a one-time achievement but an ongoing practice.
