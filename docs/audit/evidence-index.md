# Audit Evidence Index

Quick reference for auditors reviewing Value Fabric compliance evidence.

## Evidence Bundle Quick Access

| Control Type | Primary Evidence | Location | Format |
|--------------|----------------|----------|--------|
| **Identity & Access** | RBAC config | `shared/identity/` | Python/YAML |
| **Change Management** | Git history | `.github/` | Git/YAML |
| **Security Testing** | Penetration tests | `tests/penetration/` | Python/Shell |
| **Vulnerability Mgmt** | Scan results | `.github/workflows/` | SARIF/JSON |
| **Resilience** | Chaos tests | `k8s/chaos/` | YAML |
| **Incident Response** | Runbooks | `docs/operations/` | Markdown |

## SOC 2 Type II Evidence

### CC6.1 - Logical Access Security
- **CODEOWNERS** - Mandatory reviewers by path
- **RBAC tests** - `tests/security/test_rbac.py`
- **JWT middleware** - `shared/identity/jwt_middleware.py`

### CC6.2 - Access Removal
- **Offboarding checklist** - `docs/operations/` (HR process)
- **Token blacklisting** - Redis configuration

### CC6.3 - Access Control Changes
- **Pre-commit hooks** - `.pre-commit-config.yaml`
- **Git history** - `git log --all --since="90 days ago"`
- **PR approvals** - GitHub branch protection settings

### CC7.1 - Security Operations
- **Security gates workflow** - `.github/workflows/security-gates.yml`
- **Trivy scans** - Weekly scheduled container scans
- **Penetration tests** - `tests/penetration/zap-full-scan.py`

### CC7.2 - Incident Detection
- **PagerDuty integration** - Alert routing configuration
- **Runbook** - `RUNBOOK.md`
- **Postmortems** - `docs/incidents/`

## ISO 27001:2022 Evidence

### A.9 - Access Control
- **Network policies** - `k8s/base/network-policies.yaml`
- **Tenant isolation tests** - `tests/chaos/tenant-isolation-loadtest.py`
- **Service accounts** - K8s manifests with minimal privileges

### A.12 - Operations Security
- **GitOps configuration** - `k8s/gitops/`
- **Change management** - ArgoCD Application manifests
- **Capacity management** - HPA configs + Chaos tests

### A.16 - Incident Management
- **Escalation policy** - `docs/operations/escalation-policy-and-drills.md`
- **MTTA/MTTR metrics** - `docs/operations/mtta-mttr-reporting.md`
- **Drill records** - Quarterly incident response drills

### A.17 - Business Continuity
- **DR policy** - `docs/reliability/dr-policy.md`
- **Chaos experiments** - `k8s/chaos/litmus-experiments/`
- **Recovery procedures** - Layer-specific runbooks

## Phase 5: New Evidence

### Penetration Testing
- **ZAP full scan** - `tests/penetration/zap-full-scan.py`
- **Nikto scan** - `tests/penetration/nikto-scan.sh`
- **Scheduled runs** - `.github/workflows/penetration-testing.yml`

### Chaos Engineering
- **Pod delete** - `k8s/chaos/litmus-experiments/pod-delete-all-layers.yaml`
- **Network partition** - `network-partition-l3-l4.yaml`
- **CPU stress** - `cpu-stress-l4.yaml`
- **Memory stress** - `memory-stress-l2.yaml`
- **Auto-scaler** - `pod-autoscaler-l1.yaml`

### Tenant Isolation
- **Realistic workloads** - `tests/chaos/tenant-isolation-loadtest.py`
- **Race conditions** - `tests/chaos/tenant-race-condition-test.py`

## Automated Evidence Collection

Generate the release/audit evidence bundle used for release-candidate review:

```bash
pnpm evidence:bundle
tar -tf artifacts/evidence/*.tar.gz
```

PowerShell reviewers should pass the resolved archive path because Windows
`tar.exe` does not expand `*.tar.gz`:

```powershell
tar -tf (Get-ChildItem artifacts/evidence/*.tar.gz | Select-Object -First 1).FullName
```

The generated archive is written to `artifacts/evidence/value-fabric-evidence-<sha>.tar.gz`.
Open `manifest.json` inside the archive first. It records the release candidate
SHA, input sources, evidence gaps, file sizes, and SHA-256 checksums for bundled
evidence files.

Auditor verification flow:

1. Confirm `manifest.json.git_sha` matches the reviewed release candidate.
2. Recompute SHA-256 for each listed `manifest.files[*].archive_path`.
3. Compare the digest with `manifest.files[*].sha256`.
4. Review `manifest.evidence_gaps`; these are not hidden failures. They identify
   missing live, heavyweight, or environment-dependent evidence that must be
   attached before treating the bundle as complete production release evidence.

The legacy SOC2/ISO collection script can still generate quarterly control
evidence:

```bash
./scripts/audit/generate-evidence-bundle.sh \
  --output-dir ./audit-evidence-$(date +%Y%m%d) \
  --include-historical
```

Output structure:
```
audit-evidence-YYYYMMDD/
├── access-control/
├── change-management/
├── security-operations/
├── availability/
├── incident-response/
├── policies/
└── evidence-index/
    ├── index.json
    └── README.md
```

## Evidence Retention

| Evidence Type | Retention Period | Storage |
|---------------|------------------|---------|
| Security scans | 90 days | GitHub Actions artifacts |
| Penetration tests | 1 year | Evidence bundle archive |
| Chaos test results | 90 days | Kubernetes events + Prometheus |
| Access reviews | 3 years | Git history |
| Incident logs | 3 years | PagerDuty + audit logs |
| Policy documents | Permanent | Git repository |

## Auditor Verification Commands

```bash
# Verify RBAC tests pass
pytest tests/security/test_rbac.py -v

# Verify tenant isolation
python tests/chaos/tenant-isolation-loadtest.py --mode realistic --duration 60

# Verify chaos experiments exist
kubectl get chaosresults -n value-fabric-prod

# Generate evidence bundle
./scripts/audit/generate-evidence-bundle.sh
```

## Contact Information

For audit-related questions:
- **Security Team:** security@value-fabric.local
- **Compliance Lead:** compliance@value-fabric.local
- **Infrastructure:** platform@value-fabric.local

---
*Last Updated: Phase 5 Completion*
