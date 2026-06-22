# Mandatory Security Regression Gate Evidence

- **Timestamp**: 2026-06-22T19:05:05Z
- **Git SHA**: 6f63e2710
- **Branch**: main
- **OS**: MINGW64_NT-10.0-26200
- **Test Mode**: 1
- **Artifact Directory**: artifacts/mandatory_security

## Check Results

| Check | Command | Required | Result | Evidence |
|-------|---------|----------|--------|----------|
| I-02/I-03 API Production Safety | `pytest app/tests/test_auth_enforcement.py test_health.py test_production_safety.py test_i03_durable_persistence_and_llm.py` | Yes | PASS | artifacts/mandatory_security/standalone_api_security.xml |
