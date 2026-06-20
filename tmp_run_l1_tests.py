import subprocess, sys

ZXxfiles = [
    "tests/integration/test_batch_operations.py",
    "tests/integration/test_target_status_transitions.py",
    "tests/api/test_targets_batch.py",
    "tests/api/test_targets_execute_idempotency.py",
    "tests/api/test_targets_route_ordering.py",
    "tests/api/test_targets_status.py",
    "tests/test_rate_limit_enforcement.py",
    "tests/test_observability_contract_integration.py",
]
result = subprocess.run(
    [sys.executable, "-m", "pytest"] + files +
    ["-p", "no:randomly", "-v", "--tb=short", "--timeout=60"],
    cwd="C:/Users/BBB/Fabric_4L/services/layer1-ingestion",
    capture_output=True,
    text=True,
    timeout=600,
)
print("STDOUT:")
print(result.stdout[-10000:])
print("STDERR:")
print(result.stderr[-2000:])
print("EXIT:", result.returncode)
