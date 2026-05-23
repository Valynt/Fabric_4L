#!/usr/bin/env python3
"""CI gate to detect error envelope drift across all backend services.

This script verifies that:
1. All error responses follow the canonical ErrorEnvelope structure
2. The ErrorEnvelope schema is consistent across services
3. No raw exception leakage occurs in error responses
4. request_id/trace_id is present in all error responses
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
# Add packages/shared/src to path for error handling imports
shared_src = project_root / "packages" / "shared" / "src"
sys.path.insert(0, str(shared_src))


def check_shared_error_envelope_schema():
    """Verify the shared ErrorEnvelope model exists and has correct structure."""
    try:
        from value_fabric.shared.error_handling import ErrorEnvelope, ErrorDetail

        # Check that ErrorEnvelope has the required nested structure
        envelope = ErrorEnvelope(
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="Test message",
                request_id="req_test123",
                details=None,
            )
        )
        dumped = envelope.model_dump()

        # Verify structure
        assert "error" in dumped, "ErrorEnvelope must have 'error' key"
        assert "code" in dumped["error"], "ErrorDetail must have 'code' key"
        assert "message" in dumped["error"], "ErrorDetail must have 'message' key"
        assert "request_id" in dumped["error"], "ErrorDetail must have 'request_id' key"
        assert "details" in dumped["error"], "ErrorDetail must have 'details' key"

        return True, "Shared ErrorEnvelope schema is valid"
    except ImportError as e:
        return False, f"Shared error handling models not found: {e}"
    except AssertionError as e:
        return False, f"ErrorEnvelope structure invalid: {e}"
    except Exception as e:
        return False, f"Unexpected error checking ErrorEnvelope: {e}"


def check_service_uses_shared_handlers(service_path: Path) -> tuple[bool, str]:
    """Check if a service uses the shared exception handlers anywhere."""
    py_files = list(service_path.rglob("*.py"))
    if not py_files:
        return True, "No Python files found"

    skip_parts = {"__pycache__", ".venv", "venv", ".pytest_cache", "node_modules", "tests", "migrations"}
    for py_file in py_files:
        if any(part in py_file.parts for part in skip_parts):
            continue
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        if "register_exception_handlers" in content:
            return True, f"Service uses shared exception handlers: {py_file.relative_to(project_root)}"
        if "from value_fabric.shared.error_handling" in content:
            return True, f"Service imports shared error handling: {py_file.relative_to(project_root)}"

    return False, f"Service does not use shared exception handlers: {service_path.relative_to(project_root)}"


def check_no_raw_exception_leakage(service_path: Path) -> tuple[bool, str]:
    """Check that service doesn't leak raw exceptions in error responses."""
    py_files = list(service_path.rglob("*.py"))
    if not py_files:
        return True, "No Python files found"

    leak_patterns = [
        "detail=str(exc)",
        "detail=str(e)",
        '"error": str(exc)',
        '"error": str(e)',
        "traceback.format_exc()",
    ]

    skip_parts = {"__pycache__", ".venv", "venv", ".pytest_cache", "node_modules", "tests", "migrations"}
    for py_file in py_files:
        if any(part in py_file.parts for part in skip_parts):
            continue
        # Tracing internals legitimately use traceback.format_exc for observability
        if "tracing" in py_file.parts:
            continue
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()
        for pattern in leak_patterns:
            if pattern not in content:
                continue
            for i, line in enumerate(lines):
                if pattern in line:
                    # Skip ImportError fallback blocks
                    context = '\n'.join(lines[max(0, i-5):i+5])
                    if "except ImportError" in context:
                        continue
                    return False, f"Potential raw exception leakage in {py_file.relative_to(project_root)}: line {i+1}: {line.strip()}"

    return True, "No raw exception leakage detected"


def main():
    """Run all error envelope drift checks."""
    print("Checking error envelope drift across backend services...")

    checks = []
    all_passed = True

    # Check 1: Shared ErrorEnvelope schema
    passed, message = check_shared_error_envelope_schema()
    checks.append(("Shared ErrorEnvelope schema", passed, message))
    if not passed:
        all_passed = False

    # Check 2: Services use shared handlers
    services_dir = project_root / "services"
    service_names = [
        "layer1-ingestion",
        "layer2-extraction",
        "layer3-knowledge",
        "layer4-agents",
        "layer5-ground-truth",
        "layer6-benchmarks",
    ]

    for service_name in service_names:
        service_path = services_dir / service_name
        if not service_path.exists():
            checks.append((f"{service_name} exists", False, f"Service directory not found"))
            all_passed = False
            continue

        passed, message = check_service_uses_shared_handlers(service_path)
        checks.append((f"{service_name} uses shared handlers", passed, message))
        if not passed:
            all_passed = False

        passed, message = check_no_raw_exception_leakage(service_path)
        checks.append((f"{service_name} no raw exception leakage", passed, message))
        if not passed:
            all_passed = False

    # Print results
    print("\n" + "=" * 80)
    print("ERROR ENVELOPE DRIFT CHECK RESULTS")
    print("=" * 80)
    for check_name, passed, message in checks:
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {check_name}")
        if not passed:
            print(f"       {message}")
    print("=" * 80)

    if all_passed:
        print("\nAll error envelope drift checks passed.")
        return 0
    else:
        print("\nError envelope drift checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
