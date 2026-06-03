---
skill_id: pre-production-audit
name: pre-production-audit
version: 1.0.0
description: Conduct comprehensive pre-production audits of enterprise SaaS platforms. Use when preparing for production deployment, reviewing code quality, assessing security posture, validating compliance controls, or evaluating production readiness across multi-layer architectures.
side_effects: read
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# Pre-Production Audit Skill

This skill enables systematic pre-production auditing of enterprise agentic SaaS platforms, with focus on the Value Fabric multi-layer architecture.

## Audit Activation Criteria

Activate this skill when:
- Preparing for production deployment
- After major architectural changes (new layers, API changes, infrastructure updates)
- Pre-release candidate validation
- Compliance requirement triggers (SOC 2, GDPR audits)
- Security incident follow-up requiring full assessment
- Quarterly production readiness reviews

## Multi-Pass Analysis Framework

Execute audits in 5 sequential passes:

**Pass 1: Discovery**
- Map codebase structure across all layers
- Identify configuration files (k8s, Terraform, Docker)
- Catalog API contracts and OpenAPI specs
- Locate security-critical files (auth, secrets handling)

**Pass 2: Surface Analysis**
- Run automated scanners (security, dependencies, secrets)
- Identify obvious code smells and anti-patterns
- Flag TODO/FIXME/placeholder patterns
- Detect mock data vs real implementations

**Pass 3: Deep Analysis**
- Trace data flows through application layers
- Verify API contract alignment (frontend ↔ backend)
- Audit authentication/authorization flows end-to-end
- Review database query patterns and N+1 risks

**Pass 4: Cross-Reference**
- Check OpenAPI specs vs implementation
- Verify cross-layer data flow contracts (L2→L3→L4)
- Validate environment variable consistency
- Confirm monitoring coverage matches architecture

**Pass 5: Risk Assessment**
- Score findings by severity and impact
- Prioritize by compliance requirements
- Map to remediation timeline
- Generate executive summary

## Tier 1: Critical Audit Areas

### 1. Code Analysis & Review

**Static Code Analysis:**
```bash
# Run security-focused static analysis
semgrep --config=auto --severity=ERROR .
ruff check services/ --select=E,W,F,UP,B,C4,SIM
mypy services/ --ignore-missing-imports
```

**Key Checks:**
- Security vulnerabilities (injection risks, path traversal)
- Code smells and anti-patterns
- Type safety (TypeScript strict mode, Python type hints)
- Dead code detection (unused exports, unreachable code)
- TODO/FIXME/placeholder patterns requiring resolution before prod

**Multi-Language Focus:**
- **TypeScript/React**: Audit hooks, component architecture, state management
- **Python**: Audit API endpoints, business logic, async patterns
- **SQL**: Detect N+1 queries, missing indexes, injection risks

**Dependency Analysis:**
```bash
# JavaScript dependencies
npm audit --audit-level=high
pnpm audit --audit-level high

# Python dependencies
pip-audit --desc --format=markdown
safety check

# Container images
trivy image --severity HIGH,CRITICAL <image:tag>
```

**Value Fabric Specific:**
- Verify layer isolation (L1-L6 boundaries)
- Check cross-layer imports follow architecture rules
- Validate shared/ module usage across layers

### 2. Security Assessment

**OWASP Top 10 Coverage:**
- A01: Broken Access Control → Audit RouteGuard, RBAC implementation
- A02: Cryptographic Failures → Verify encryption, hashing, key management
- A03: Injection → SQL injection via SQLAlchemy, XSS via React escaping
- A04: Insecure Design → Multi-tenant isolation, secrets management
- A05: Security Misconfiguration → Default configs, error handling
- A07: Auth Failures → JWT/OAuth implementation, session management

**Authentication/Authorization Audit:**
```python
# Check for in layer4-agents/src/
- OIDC/OAuth flow implementation (tenants/api/routes/oidc.py)
- JWT validation and token refresh
- RBAC permission checks on all admin routes
- RouteGuard fail-open scenarios (frontend)
```

**Secrets Management:**
- Scan for hardcoded secrets: `gitleaks detect --source . -v`
- Verify `.env.example` completeness
- Check Kubernetes secret references (not values in Git)
- Validate Infisical or vault integration

**Container Security:**
```bash
# Dockerfile audit
trivy config k8s/
checkov --file k8s/
```

**Network Security:**
- Review k8s NetworkPolicies
- Verify ingress/egress rules
- Check TLS termination configuration

### 3. Enterprise SaaS Architecture

**Multi-Tenant Architecture:**
- Verify tenant isolation in all data access layers
- Check tenant_id filtering on all queries
- Validate cross-tenant access prevention
- Review tenant-aware caching strategies

**API Design Review:**
- REST contract consistency across all layers
- OpenAPI spec accuracy vs implementation
- API versioning strategy (v1 prefix verification)
- Error response format standardization

**Service Boundaries:**
- Clear separation between L1-L6 responsibilities
- Inter-service communication patterns
- Event-driven architecture implementation (if present)
- Message queue configuration and durability

**Scalability Assessment:**
- Stateless service design
- Horizontal scaling readiness (k8s HPA)
- Database connection pooling
- Caching strategy effectiveness

### 4. Compliance & Governance

**SOC 2 Type II Controls:**
| Control | Implementation Evidence | Status |
|---------|------------------------|--------|
| Access Control | RBAC in identity/, OIDC routes | Check |
| Change Management | Git history, PR reviews | Check |
| System Monitoring | Prometheus metrics, alerts | Check |
| Data Backup | Database backup procedures | Check |

**GDPR Requirements:**
- Data classification (PII handling in services/)
- Consent mechanism implementation
- Data deletion capabilities (right to erasure)
- Cross-border data transfer safeguards

**Audit Logging:**
```python
# Verify in shared/audit/
- All authentication events logged
- Data modification audit trails
- Administrative action logging
- Log retention policy compliance
```

**Data Retention:**
- Verify retention policies in code/config
- Check automated deletion implementations
- Review archive procedures

## Tier 2: High-Value Audit Areas

### 5. AI/ML & Agentic Systems

**LLM Integration Patterns:**
- Review layer2-extraction/src/layer2_extraction/extraction/llm_extractor.py
- Check prompt injection safeguards
- Verify output validation and sanitization
- Audit token usage and cost controls

**Prompt Engineering:**
- Review prompts in layer2-extraction/src/layer2_extraction/extraction/prompts/
- Check for prompt injection vulnerabilities
- Validate prompt versioning and A/B testing

**RAG Architecture:**
- Knowledge retrieval accuracy (L3 graph queries)
- Embedding generation and storage (pgvector)
- Retrieval relevance and latency

**Agent Orchestration:**
- LangGraph workflow validation (layer4-agents/)
- Multi-agent system boundaries
- Decision traceability and explanation

### 6. Observability & SRE

**Monitoring Coverage:**
```yaml
# Verify in monitoring/
prometheus:
  - Service metrics exported
  - Business metrics defined
  - Alert rules configured
grafana:
  - Dashboards for all layers
  - SLA/SLO visualizations
```

**Logging Standards:**
- Structured logging (JSON format)
- Correlation ID propagation
- Sensitive data redaction
- Log aggregation (ELK/Loki readiness)

**Distributed Tracing:**
- OpenTelemetry integration
- Cross-layer trace correlation
- Critical path latency analysis

**SLO/SLI Definition:**
- Availability targets defined
- Latency percentiles measured
- Error rate thresholds
- Alert quality (signal vs noise)

### 7. Performance Engineering

**Load Testing Strategy:**
```bash
# Example k6 script validation
cat scripts/load-test-k6.js | head -50
```

**Database Optimization:**
- Query execution plans for critical paths
- Index coverage analysis
- Connection pool sizing
- Query timeout configurations

**Caching Strategy:**
- Redis cache hit rates
- Cache invalidation correctness
- CDN configuration (if applicable)
- Browser caching headers

**Frontend Performance:**
- Bundle size analysis
- Code splitting implementation
- Core Web Vitals targets
- Lazy loading patterns

### 8. Infrastructure & DevOps

**Kubernetes Audit:**
```bash
# k8s/ manifests review
- Resource limits and requests
- Liveness/readiness probes
- Pod disruption budgets
- Network policies
- Security contexts
```

**Terraform/CloudFormation:**
- State management security
- Resource tagging compliance
- Cost optimization opportunities

**CI/CD Pipeline:**
- GitHub Actions workflows (.github/workflows/)
- Test automation coverage
- Deployment rollback procedures
- Environment parity verification

**Environment Management:**
- Dev/staging/prod consistency
- Feature flag configuration
- Database migration procedures

## Evidence-Based Reporting

Every finding must include:

```markdown
### FINDING-{ID}: [Title]
**Severity:** Critical | High | Medium | Low
**Category:** Security | Performance | Compliance | Architecture

**Evidence:**
- File: `services/layer4-agents/src/api/routes.py:42-58`
- Code:
  ```python
  # Vulnerable code snippet
  ```

**Standard Violated:**
- OWASP A07:2021 - Identification and Authentication Failures
- CIS Docker Benchmark 4.1

**Impact:**
Description of business/security impact

**Remediation:**
Specific steps to fix with code example

**Owner:** [Team/Individual]
**Timeline:** [Days to resolution]
```

## Deliverables

1. **Pre_Production_Audit_Report.md**
   - Executive summary (risks, readiness score)
   - Findings by severity
   - Compliance control mapping
   - Remediation roadmap

2. **Security_Assessment.md**
   - OWASP coverage matrix
   - Vulnerability details with CVSS scores
   - Secrets scan results
   - Container security report

3. **Compliance_Mapping.md**
   - SOC 2 control implementation evidence
   - GDPR requirement verification
   - Audit log completeness review

4. **Risk_Register.md**
   - Prioritized risk list
   - Risk owners and mitigation status
   - Residual risk acceptance decisions

## Required Tool Integrations

| Tool Type | Tools | Purpose | Command |
|-----------|-------|---------|---------|
| SAST | Semgrep, CodeQL, ruff | Static analysis | `semgrep --config=auto .` |
| SCA | Snyk, Trivy, pip-audit | Dependency scanning | `trivy fs --scanners vuln .` |
| Secrets | Gitleaks, TruffleHog | Secret detection | `gitleaks detect --source .` |
| Container | Trivy, Grype, Checkov | Image/IaC scanning | `trivy config k8s/` |
| Performance | k6, Locust | Load testing | `k6 run scripts/load-test.js` |

## Quality Gates

Before audit completion, verify:
- [ ] All critical and high findings have assigned owners
- [ ] Evidence includes precise file paths and line numbers
- [ ] Risk scores are justified with impact analysis
- [ ] Remediation guidance is actionable
- [ ] Compliance controls have implementation evidence
- [ ] Cross-layer data flows are documented
- [ ] Tool outputs are captured and referenced
