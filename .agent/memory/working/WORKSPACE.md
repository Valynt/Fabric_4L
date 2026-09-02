# Workspace (live task state)

## Archived tasks
- Goal: Remediate Trivy HIGH/CRITICAL findings in the Layer 3 SBOM and restore security-gate health.
- Status: COMPLETE — refreshed the pinned Python base digest across maintained service Dockerfiles and build documentation.
- Validation: Structural preflight and workflow-reference checks passed; Layer 3 Docker build reached dependency installation but local PyPI TLS interception prevented completion; secret scan found no secrets.

## Active hypotheses
- Goal: Remediate the remaining OAuth callback review comments on PR #1624 by hardening the CLI login flow and adding regression tests.
- Status: COMPLETE — the callback handler now validates the expected PKCE state and callback path, binds to `127.0.0.1`, fail-closes on bind errors, and uses monotonic timeout checks.
- Validation: `python3 -m ruff check src/valuefabric/cli/auth.py tests/test_cli.py` and `python3 -m pytest tests/test_cli.py -q` both passed.
