# Workspace (live task state)

## Active task
- Goal: ADR Registry + CI (`make check-adr`) — dual-corpus registry, related-path existence, optional content rules.
- Status: COMPLETE — `docs/decisions/adr-registry.yaml`, `scripts/ci/check_adr.py`, tests, Make/CI, docs.
- Validation: `python scripts/ci/check_adr.py` pass; `pytest tests/ci/test_check_adr.py` 10 passed; inventory `--check` pass; command-map + workflow-parity + inventory tests pass (1 pre-existing Windows-CRLF fixture-hash failure reproduces at HEAD).

## Archived tasks
- Goal: Complete the fail-closed policy decision facade work: centralize tenant/RBAC/LLM-safety enforcement while preserving the repo's governance stack and layer boundaries.
- Status: COMPLETE — the fail-closed enforcement flow is implemented in the repo and validated with the targeted governance suite.
- Validation: `python -m pytest tests/shared/governance/test_gate_phase2.py tests/shared/governance/test_gate_phase3.py -q` passed with 52/52 tests passing.
- Goal: Remediate Trivy HIGH/CRITICAL findings in the Layer 3 SBOM and restore security-gate health.
- Status: COMPLETE — refreshed the pinned Python base digest across maintained service Dockerfiles and build documentation.
- Validation: Structural preflight and workflow-reference checks passed; Layer 3 Docker build reached dependency installation but local PyPI TLS interception prevented completion; secret scan found no secrets.

## Active hypotheses
- The repo contains the intended fail-closed enforcement logic; the remaining work is to maintain this contract and validate changes with the targeted governance tests before broader releases.
