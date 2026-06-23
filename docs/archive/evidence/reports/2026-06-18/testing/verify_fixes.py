import subprocess
import sys

files = [
    "services/layer3-knowledge/tests/test_exception_handlers.py",
    "services/layer3-knowledge/tests/test_tenant_context_extraction.py",
    "services/layer3-knowledge/tests/test_tenant_isolation.py",
]

print("Running collection verification on fixed Layer3 test files...")
r = subprocess.run(
    [sys.executable, "-m", "pytest", "--co", "-n0", "-q"] + files,
    capture_output=True, text=True, timeout=60
)
print(r.stdout)
if r.stderr:
    print("STDERR:", r.stderr[-800:])
print("COLLECTION_EXIT:", r.returncode)

print("\nRunning execution on exception_handlers and tenant_context_extraction...")
r2 = subprocess.run(
    [sys.executable, "-m", "pytest", "-n0", "-q", "--tb=line", "--timeout=30"]
    + files[:2],
    capture_output=True, text=True, timeout=120
)
print(r2.stdout)
if r2.stderr:
    print("STDERR:", r2.stderr[-800:])
print("EXECUTION_EXIT:", r2.returncode)
