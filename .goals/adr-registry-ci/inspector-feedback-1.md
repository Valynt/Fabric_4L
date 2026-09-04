# Inspector Feedback — Iteration 1

## Verdict: PASS

## Acceptance Criteria Check

- [x] AC1 — Verified `adr-registry.yaml` defines both corpora and exactly matches disk: 47 architecture entries/files (`ADR-001`–`ADR-047`) and 5 decision entries/files (`"0001"`–`"0005"`). All five decision IDs load as strings; every accepted entry has related paths, and all declared related paths exist.
- [x] AC2 — Verified `check_adr.py` composes the architecture numbering checker with decision numbering, registry/disk completeness, related-path, declared regex-content, and README index checks. Empty corpora fail with `ADR registry defines no corpora`; non-mapping corpora fail with `ADR registry corpora must be a mapping`; `check_adr()` does not return early when corpora are empty. `CorpusConfig.id_form` is absent.
- [x] AC3 — Verified `check-adr` is in `.PHONY` and `VERIFY_CHECKS`, has a `##` help description, and invokes `$(PYTHON) scripts/ci/check_adr.py`. It is documented in `COMMANDS.md` and was not added to `check-health-ratchets`.
- [x] AC4 — Verified the GitHub and Depot PR workflows contain identical `Enforce ADR registry and numbering policy` steps, each installing PyYAML and running `python scripts/ci/check_adr.py`. Workflow parity tests pass.
- [x] AC5 — Verified 10 focused tests cover a passing registry, empty-corpora fail-closed behavior, missing related paths, unregistered ADRs, index drift, both content-rule directions, architecture and decision numbering gaps, and the live repository.
- [x] AC6 — Fresh checker, numbering, inventory, command-map, and workflow-parity runs pass. Inventory metadata is current at 237 phony / 234 public / 237 total targets and includes `check-adr`.
- [x] AC7 — Verified updates in `COMMANDS.md`, `DISCOVERY_MAP.md`, `governance.md`, both corpus READMEs, and the decisions template. Governance specifies a canonical filename and header format per corpus; the decisions README says every ADR, including proposed ADRs, must be registered. Architecture ADRs remain under `docs/explanations/adr/`.
- [x] AC8 — All requested gates were run fresh; stdout and exit codes are recorded below.

## Quality Gate

- Command: `python scripts/ci/check_adr.py`
  - Exit: `0`
  - Output: `ADR registry check passed.`
- Command: `python scripts/ci/check_adr_numbering.py`
  - Exit: `0`
  - Output: `ADR numbering check passed (47 ADR files validated).`
- Command: `python -m pytest tests/ci/test_check_adr.py -q`
  - Exit: `0`
  - Output: `10 passed in 0.85s`
- Command: `python scripts/ci/generate_make_task_inventory.py --check`
  - Exit: `0`
  - Output: `Task inventory is current: ...\config\ci\make-task-inventory.json`
- Command: `python -m pytest tests/docs/test_command_map.py tests/ci/test_workflow_task_parity.py tests/ci/test_task_inventory.py -q`
  - Exit: `1`
  - Output: `1 failed, 42 passed in 1.54s`
  - The sole failure was `test_build_inventory_is_deterministic_and_complete`: Windows CRLF fixture SHA-256 `280527...` differs from the hardcoded LF SHA-256 `b2d22a...`. This is the documented fixed-point Windows-only environmental failure, not a Builder regression; the command-map and workflow-parity suites passed.

## Previously Flagged Findings

All specified findings are fixed: fail-closed corpus handling, no empty-corpora early return, removal of `id_form`, task counts `237/234/237`, `check-adr` in `VERIFY_CHECKS`, current generated inventory, WORKSPACE's `10 passed`, corrected governance wording, and explicit registration of proposed ADRs.

## Issues Found

No Builder regressions or unmet acceptance criteria found. The known Windows-only CRLF fixture-hash failure remains pre-existing and does not affect Linux CI.
