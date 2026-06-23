# Critical-Path End-to-End Gate Matrix

This matrix lists the real production paths that must be exercised before a release is authorized.

| # | Path | Evidence source | Owner |
|---|---|---|---|
| 1 | Notes ingestion | `apps/web/e2e/behaviors/j1-ingestion.behavior.spec.ts` | frontend-leads |
| 2 | Web/Search ingestion | `services/layer1-ingestion/tests/test_web_search.py` | layer1 |
| 3 | Audio transcription and ingestion | `services/layer1-ingestion/tests/test_audio.py` | layer1 |
| 4 | CRM import | `tests/integration/test_crm_import.py` | layer2 |
| 5 | PDF parsing with page-level provenance | `services/layer2-extraction/tests/test_pdf_provenance.py` | layer2 |
| 6 | Meeting transcript ingestion | `services/layer1-ingestion/tests/test_meeting.py` | layer1 |
| 7 | Duplicate submission and idempotency | `tests/integration/test_idempotency.py` | layer1 |
| 8 | Source version creation | `services/layer1-ingestion/tests/test_source_version.py` | layer1 |
| 9 | Normalization | `services/layer2-extraction/tests/test_normalization.py` | layer2 |
| 10 | Chunking and source anchoring | `services/layer2-extraction/tests/test_chunking.py` | layer2 |
| 11 | Signal extraction | `services/layer2-extraction/tests/test_signal_extraction.py` | layer2 |
| 12 | Entity resolution | `services/layer3-knowledge/tests/test_entity_resolution.py` | layer3 |
| 13 | Stakeholder classification | `services/layer3-knowledge/tests/test_stakeholder_classification.py` | layer3 |
| 14 | Pain-point detection | `services/layer4-agents/tests/test_pain_point_detection.py` | layer4 |
| 15 | Value-lever matching | `services/layer4-agents/tests/test_value_lever_matching.py` | layer4 |
| 16 | Claim generation | `services/layer4-agents/tests/test_claim_generation.py` | layer4 |
| 17 | Claim validation | `services/layer5-ground-truth/tests/test_claim_validation.py` | layer5 |
| 18 | Evidence-strength calculation | `tests/layer6/test_evidence_strength.py` | layer6 |
| 19 | Benchmark recommendation | `services/layer6-benchmarks/tests/test_recommendation.py` | layer6 |
| 20 | Benchmark acceptance | `tests/layer6/test_benchmark_acceptance.py` | layer6 |
| 21 | Override creation | `tests/backend_integrated/test_approval_export_crm_governance.py` | backend-leads |
| 22 | Dependent-claim recalculation | `services/layer4-agents/tests/test_dependent_recalculation.py` | layer4 |
| 23 | Brief revision creation | `services/layer4-agents/tests/test_brief_revision.py` | layer4 |
| 24 | Read-model projection | `services/layer2-5-signal-refinery/tests/test_projection.py` | layer2-5 |
| 25 | UI retrieval | `apps/web/e2e/behaviors/j3-value-studio.behavior.spec.ts` | frontend-leads |
| 26 | Exact evidence-lineage retrieval | `services/layer3-knowledge/tests/test_lineage.py` | layer3 |
| 27 | Retry after transient failure | `tests/reliability/test_retry.py` | platform |
| 28 | Permanent-failure handling | `tests/reliability/test_permanent_failure.py` | platform |
| 29 | Worker restart and checkpoint resume | `tests/reliability/test_worker_resume.py` | platform |
| 30 | Cancellation | `tests/reliability/test_cancellation.py` | platform |
| 31 | Dead-letter handling and replay | `tests/security/test_audit_retry_queue.py` | security |
| 32 | Tenant-boundary enforcement | `scripts/ci/tenant_isolation_readiness_gate.sh` | security |
| 33 | Authorization enforcement | `tests/security/test_auth_boundaries.py` | security |
| 34 | Audit-event completeness | `tests/security/test_audit_event_emission.py` | security |
| 35 | Rollback or roll-forward recovery | `pnpm release:rollback:verify` | SRE |

## Execution pattern

- Staging: every path must be exercised at least once before production.
- Production canary: minimum paths 1, 7, 11, 16, 24, 25, 32 must be exercised.
- Production post-deploy: all 35 paths must be exercised within the observation window.

## Synthetic vs. real

- Synthetic tests must call the actual queue, storage, graph, and projection components.
- Tests that stub the queue, database, graph, or object store are not acceptable as E2E evidence.
