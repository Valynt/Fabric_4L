# Fabric_4L Game Day Schedule

| Field | Value |
|---|---|
| **Document ID** | GD-001 |
| **Version** | v1.2.0 |
| **Owner** | SRE Team Lead |
| **Review Cycle** | Quarterly |
| **Last Updated** | 2025-01-15 |

---

## 1. Overview

Game days are controlled chaos engineering exercises designed to validate
our disaster recovery runbooks, circuit breaker configurations, and team
response procedures in a realistic but safe environment.

**Objective:** Ensure the Fabric_4L platform and team can recover from
realistic failure scenarios within documented RTO/RPO targets.

**Scope:** All 6 layers (L1-L6), data stores (PostgreSQL, Neo4j, Redis),
and cross-region failover capabilities.

---

## 2. Annual Calendar (12 Months)

### Month 1: January — PostgreSQL Primary Failover

| Field | Details |
|---|---|
| **Scenario** | PostgreSQL primary database crash during peak ingestion |
| **Runbook** | DR-DB-001 |
| **RTO Target** | 5 minutes |
| **RPO Target** | 1 minute |

**Roles:**
| Role | Assigned To | Responsibilities |
|---|---|---|
| **Incident Commander (IC)** | SRE On-Call Lead | Decision authority, timeline tracking |
| **Communicator** | Customer Success Rep | Internal + external communications |
| **Resolver** | DBA Team Engineer | Execute failover procedure |
| **Observer** | Engineering Manager | Note process gaps, no intervention |

**Expected Outcomes:**
- [ ] Replica promoted within 5 minutes
- [ ] Zero data loss (sync replication)
- [ ] All layers report healthy within 10 minutes
- [ ] Communication timeline < 2 minutes from detection

**Procedure:**
1. Observer injects fault (kill PostgreSQL primary pod)
2. IC acknowledges alert and convenes response
3. Resolver follows DR-DB-001 runbook
4. Communicator sends status updates
5. Observer validates RTO/RPO targets

---

### Month 2: February — Neo4j Cluster Partition

| Field | Details |
|---|---|
| **Scenario** | Network partition isolates 2 of 3 Neo4j core servers |
| **Runbook** | DR-GRAPH-001 |
| **RTO Target** | 10 minutes |
| **RPO Target** | 0 |

**Roles:**
| Role | Assigned To |
|---|---|
| **IC** | Platform Team Lead |
| **Communicator** | SRE Team Member |
| **Resolver** | Knowledge Graph Engineer |
| **Observer** | Staff Engineer |

**Expected Outcomes:**
- [ ] Failed core identified within 3 minutes
- [ ] pgvector fallback activates automatically
- [ ] Cluster reformed within 10 minutes
- [ ] Knowledge graph consistency verified
- [ ] Zero customer-visible errors (fallback works)

---

### Month 3: March — Redis Cascade Prevention

| Field | Details |
|---|---|
| **Scenario** | Redis master fails + Sentinel misconfiguration |
| **Runbook** | DR-CACHE-001 |
| **RTO Target** | 3 minutes |
| **Focus** | Circuit breaker behavior during cache failure |

**Roles:**
| Role | Assigned To |
|---|---|
| **IC** | SRE On-Call |
| **Communicator** | Developer Relations |
| **Resolver** | SRE Team Member |
| **Observer** | Redis SME |

**Expected Outcomes:**
- [ ] Circuit breaker for Redis opens within 15 seconds
- [ ] All services continue operating (degraded latency)
- [ ] Sentinel failover or manual recovery within 3 minutes
- [ ] Cache warms back to > 70% hit rate within 10 minutes
- [ ] No 500 errors from any layer

---

### Month 4: April — Layer 4 Agent Degradation

| Field | Details |
|---|---|
| **Scenario** | LangGraph agent pods OOMKilled during complex reasoning task |
| **Runbook** | N/A — chaos experiment only |
| **Focus** | Graceful degradation of L4, L3 fallback behavior |

**Roles:**
| Role | Assigned To |
|---|---|
| **IC** | ML Platform Lead |
| **Communicator** | Product Manager |
| **Resolver** | Agent Team Engineer |
| **Observer** | SRE Team Lead |

**Expected Outcomes:**
- [ ] L3 serves cached responses when L4 is unreachable
- [ ] L2 queues extraction tasks without dropping
- [ ] Circuit breaker for L4 transitions: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
- [ ] Metrics show all state transitions
- [ ] Recovery within 5 minutes of pod restart

---

### Month 5: May — Full Region Failover

| Field | Details |
|---|---|
| **Scenario** | Primary AWS region network backbone failure |
| **Runbook** | DR-REGION-001 |
| **RTO Target** | 15 minutes |
| **RPO Target** | 5 minutes |
| **Environment** | Staging (with production-like data) |

**Roles:**
| Role | Assigned To |
|---|---|
| **IC** | Director of Engineering |
| **Communicator** | VP of Engineering (internal), Customer Success (external) |
| **Resolver** | SRE Team (2 members) + DBA |
| **Observer** | CTO |
| **Scribe** | Engineering Program Manager |

**Expected Outcomes:**
- [ ] DR Coordinator convened within 2 minutes
- [ ] Standby database promoted within 5 minutes
- [ ] DNS cutover completed within 10 minutes
- [ ] End-to-end ingestion test passes in standby
- [ ] Degraded mode banner shown for unavailable features
- [ ] Communication sent to customers within 5 minutes of cutover

**⚠️ This is a HIGH-EFFORT game day. Schedule on Thursday, avoid deploy weeks.**

---

### Month 6: June — Corrupted Tenant Data

| Field | Details |
|---|---|
| **Scenario** | Bug in ingestion pipeline corrupts data for single tenant |
| **Runbook** | DR-TENANT-001 |
| **RTO Target** | 30 minutes |
| **Focus** | Tenant isolation, PITR, audit trail |

**Roles:**
| Role | Assigned To |
|---|---|
| **IC** | DBA Team Lead |
| **Communicator** | Customer Success Manager (affected tenant) |
| **Resolver** | DBA + L1 Engineer |
| **Observer** | Security/Compliance Officer |

**Expected Outcomes:**
- [ ] Tenant isolated (maintenance mode) within 3 minutes
- [ ] Corruption scope identified within 8 minutes
- [ ] PITR recovery initiated within 15 minutes
- [ ] Integrity checks pass post-recovery
- [ ] Audit trail generated and uploaded
- [ ] Customer notified of resolution

---

### Month 7: July — Cascading Failure Simulation

| Field | Details |
|---|---|
| **Scenario** | Kill one pod per layer sequentially (domino effect) |
| **Runbook** | N/A — chaos experiment |
| **Focus** | Verify no cascading failures, circuit breakers isolate |

**Roles:**
| Role | Assigned To |
|---|---|
| **IC** | SRE On-Call |
| **Communicator** | Team Slack bot (automated) |
| **Resolver** | Kubernetes operator (automated + manual oversight) |
| **Observer** | Platform Architect |

**Expected Outcomes:**
- [ ] Each layer recovers independently
- [ ] Circuit breakers prevent cross-layer impact
- [ ] All health checks pass within 2 minutes per layer
- [ ] No manual intervention required

---

### Month 8: August — PostgreSQL Connection Pool Exhaustion

| Field | Details |
|---|---|
| **Scenario** | Connection leak causes pool exhaustion |
| **Runbook** | DR-DB-001 (adapted) |
| **Focus** | Connection pool behavior, queueing, recovery |

**Roles:**
| Role | Assigned To |
|---|---|
| **IC** | SRE Team Member |
| **Communicator** | Engineering Manager |
| **Resolver** | Backend Engineer |
| **Observer** | DBA |

**Expected Outcomes:**
- [ ] Pool exhaustion detected via metrics
- [ ] Queueing activated (no request drops)
- [ ] Auto-recovery when connections released
- [ ] PgBouncer failover works if configured

---

### Month 9: September — Chaos Monkey (Randomized)

| Field | Details |
|---|---|
| **Scenario** | Random pod kills across all namespaces for 1 hour |
| **Runbook** | N/A — Chaos Mesh experiment |
| **Focus** | Kubernetes self-healing, PDB effectiveness |

**Roles:**
| Role | Assigned To |
|---|---|
| **IC** | Automated (PagerDuty orchestration) |
| **Communicator** | Automated (Slack bot) |
| **Resolver** | Automated (Kubernetes) |
| **Observer** | SRE Team (monitors dashboards) |

**Expected Outcomes:**
- [ ] < 0.1% error rate during 1-hour chaos period
- [ ] All PDBs respected (no full outages)
- [ ] Pod restart time < 60 seconds
- [ ] HorizontalPodAutoscaler responds correctly

---

### Month 10: October — IO Latency Injection

| Field | Details |
|---|---|
| **Scenario** | 200ms disk IO latency on PostgreSQL primary |
| **Runbook** | DR-DB-001 (adapted) |
| **Focus** | Query timeout behavior, read replica promotion |

**Roles:**
| Role | Assigned To |
|---|---|
| **IC** | SRE On-Call |
| **Communicator** | Team Lead |
| **Resolver** | DBA + Storage Team |
| **Observer** | Performance Engineer |

**Expected Outcomes:**
- [ ] Slow queries identified via pg_stat_statements
- [ ] Read replica serves reads (if read-splitting enabled)
- [ ] Write latency acceptable or failover triggered
- [ ] IO chaos removed, performance returns to baseline

---

### Month 11: November — Multi-Service Degradation

| Field | Details |
|---|---|
| **Scenario** | L3 + L4 simultaneously degraded (complex query + agent OOM) |
| **Runbook** | Multiple (DR-GRAPH-001 + chaos) |
| **Focus** | Multiple fallback layers, user experience |

**Roles:**
| Role | Assigned To |
|---|---|
| **IC** | Staff SRE |
| **Communicator** | Product Manager |
| **Resolver** | L3 + L4 Engineers |
| **Observer** | UX Researcher |

**Expected Outcomes:**
- [ ] Both circuit breakers open independently
- [ ] L1/L2/L5/L6 unaffected
- [ ] User gets degraded experience (not errors)
- [ ] Both services recover independently

---

### Month 12: December — Year-End DR Drill

| Field | Details |
|---|---|
| **Scenario** | Full DR validation: primary region failure + data corruption |
| **Runbook** | DR-REGION-001 + DR-TENANT-001 |
| **Focus** | Comprehensive validation of all DR capabilities |

**Roles:**
| Role | Assigned To |
|---|---|
| **IC** | Director of Engineering |
| **Communicator** | VP Engineering + Customer Success |
| **Resolver** | Full SRE + DBA team |
| **Observer** | CTO + Security Officer |
| **Scribe** | Engineering Program Manager |

**Expected Outcomes:**
- [ ] All DR runbooks executed successfully
- [ ] All RTO/RPO targets met
- [ ] Audit trail complete
- [ ] Improvement items documented
- [ ] Board-level summary prepared

---

## 3. Post-Game-Day Review Template

Complete this template within 48 hours of each game day.

### Basic Information
| Field | Value |
|---|---|
| Game Day Date | |
| Scenario | |
| Runbook(s) Used | |
| Participants | |
| Duration | |

### Scorecard

| Metric | Target | Actual | Pass/Fail |
|---|---|---|---|
| Detection Time | < 2 min | | |
| Acknowledgment Time | < 2 min | | |
| Resolution Time (RTO) | Per runbook | | |
| Data Loss (RPO) | Per runbook | | |
| Communication Time | < 5 min | | |
| Error Rate During Event | < 1% | | |
| Customer Impact | None | | |

### Runbook Quality

| Question | Rating (1-5) |
|---|---|
| Were steps clear and unambiguous? | |
| Were prerequisites complete? | |
| Were verification steps sufficient? | |
| Was rollback procedure clear? | |
| Would this work in production at 3 AM? | |

### What Went Well
1.
2.
3.

### What Needs Improvement
1.
2.
3.

### Action Items
| ID | Action | Owner | Due Date | Priority | Status |
|---|---|---|---|---|---|
| GD-YYYY-MM-001 | | | | | |
| GD-YYYY-MM-002 | | | | | |
| GD-YYYY-MM-003 | | | | | |

### Runbook Updates Required
- [ ] DR-DB-001
- [ ] DR-GRAPH-001
- [ ] DR-CACHE-001
- [ ] DR-REGION-001
- [ ] DR-TENANT-001
- [ ] Chaos test updates
- [ ] Circuit breaker config updates

---

## 4. Improvement Tracking Table

Track all improvements identified from game days:

| ID | Game Day | Finding | Action | Owner | Due Date | Status | Verification |
|---|---|---|---|---|---|---|---|
| IMP-001 | Jan 2025 | Replica promotion took 8 min | Add Patroni pre-check script | @sre-alice | 2025-02-01 | Done | Feb GD validated |
| IMP-002 | Jan 2025 | Connection strings not updated | Automate via operator | @sre-bob | 2025-03-01 | In Progress | |
| IMP-003 | Feb 2025 | pgvector fallback latency too high | Add pgvector connection pool | @plat-charlie | 2025-03-15 | Pending | |
| IMP-004 | Feb 2025 | Neo4j consistency check missing | Add automated check script | @dba-dana | 2025-02-28 | Done | |
| IMP-005 | Mar 2025 | Redis circuit breaker too slow | Reduce failure_threshold to 3 | @sre-alice | 2025-04-01 | Pending | |
| | | | | | | | |

**Status Definitions:**
- **Pending** — Not started
- **In Progress** — Owner actively working
- **Done** — Completed and verified
- **Won't Fix** — Accepted risk, documented

---

## 5. Escalation Procedures

### If Game Day Reveals Critical Gap

**Immediate (during game day):**
1. IC calls emergency stop if safety concerns
2. Document the gap with timestamp and evidence
3. Continue game day with adapted scenario if safe

**Within 24 hours:**
1. File P1 ticket with game day evidence
2. Page relevant team leads
3. Schedule emergency fix session

**Within 1 week:**
1. Fix implemented and tested
2. Re-run specific game day scenario to validate
3. Update runbooks

### Severity Classification of Gaps

| Severity | Criteria | Response |
|---|---|---|
| **Critical** | Would cause data loss in production | Stop current work, fix immediately |
| **High** | Would exceed RTO/RPO in production | P1 ticket, fix within 1 week |
| **Medium** | Runbook unclear, would slow response | P2 ticket, fix within 1 month |
| **Low** | Documentation improvement | P3 ticket, next sprint |

---

## 6. Roles & Responsibilities

### Incident Commander (IC)
- Single decision authority during game day
- Tracks timeline against RTO targets
- Calls go/no-go for risky steps
- Does NOT execute technical steps

### Communicator
- All internal communications (Slack, email)
- Status page updates (if external communication needed)
- Timeline documentation
- Stakeholder notifications

### Resolver
- Executes technical recovery steps
- Follows runbook procedures
- Reports status to IC every 2 minutes
- Escalates to IC if runbook doesn't cover situation

### Observer
- Takes notes on process gaps
- Does NOT intervene or help
- Validates RTO/RPO measurements
- Leads post-game-day review

---

## 7. Scheduling Guidelines

### When to Schedule
- **Preferred:** Tuesday-Thursday, 10 AM - 2 PM local time
- **Avoid:** Deploy days (Monday/Friday), holidays, quarter-end
- **Full Region Failover:** Schedule during low-traffic period
- **Duration:** 2-4 hours including post-mortem

### Notification Timeline
| Before | Action |
|---|---|
| 2 weeks | Calendar invite to all participants |
| 1 week | Share scenario overview (not details) |
| 1 day | Confirm environment ready, runbooks printed |
| 1 hour | Pre-game briefing (roles, comms channels) |
| 0 | Go/no-go decision from IC |

---

## 8. Compliance & Audit

All game days are audited for:
- SOC 2 Type II: DR testing requirement (CC7.4)
- ISO 27001: Business continuity testing (A.17.1.3)
- Customer contracts: DR validation commitments

**Required artifacts:**
- [ ] Completed post-game-day review
- [ ] RTO/RPO measurement evidence
- [ ] Improvement tracking table updated
- [ ] Runbook update tickets created
- [ ] Executive summary (for Critical/High findings)

**Storage:** All artifacts stored in `s3://fabric4l-compliance/game-days/YYYY/`
