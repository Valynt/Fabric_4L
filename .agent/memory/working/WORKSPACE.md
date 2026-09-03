# Workspace (live task state)

## Active task
- Goal: ADR Registry + CI (`make check-adr`) — dual-corpus registry, related-path existence, optional content rules.
- Status: COMPLETE — `docs/decisions/adr-registry.yaml`, `scripts/ci/check_adr.py`, tests, Make/CI, docs.
- Validation: `python scripts/ci/check_adr.py` pass; `pytest tests/ci/test_check_adr.py` 10 passed; inventory `--check` pass; command-map + workflow-parity + inventory tests pass (1 pre-existing Windows-CRLF fixture-hash failure reproduces at HEAD).

## Active hypotheses
- (cleared)

