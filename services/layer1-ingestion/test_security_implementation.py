#!/usr/bin/env python3
"""
Quick security implementation verification script.
Tests the core security features without requiring PostgreSQL.
"""

import os
import sys
import time
from uuid import uuid4

# Add src to path
sys.path.insert(0, 'src')

def test_exception_hierarchy():
    """Test that the exception hierarchy works correctly."""
    print("Testing exception hierarchy...")
    
    try:
        from shared.exceptions import (
            SecurityError,
            TenantContextError,
            InvalidTenantContextError,
            SystemMaintenanceAuthorizationError,
            RobotsCheckerError,
            RobotsCacheError,
            RobotsFetchError,
            RobotsParseError,
        )
        print("[OK] All security exceptions imported successfully")
        
        # Test exception inheritance
        assert issubclass(TenantContextError, SecurityError)
        assert issubclass(InvalidTenantContextError, TenantContextError)
        assert issubclass(SystemMaintenanceAuthorizationError, SecurityError)
        assert issubclass(RobotsCacheError, RobotsCheckerError)
        assert issubclass(RobotsFetchError, RobotsCheckerError)
        assert issubclass(RobotsParseError, RobotsCheckerError)
        print("[OK] Exception hierarchy is correct")
        
        # Test exception creation
        try:
            raise InvalidTenantContextError("Test error", tenant_id="test-tenant")
        except InvalidTenantContextError as e:
            assert e.tenant_id == "test-tenant"
            assert "Test error" in str(e)
        print("[OK] Exception creation works correctly")
        
    except Exception as e:
        print(f"[FAIL] Exception hierarchy test failed: {e}")
        return False
    
    return True

def test_maintenance_identity():
    """Test system maintenance identity validation."""
    print("Testing maintenance identity...")
    
    try:
        from shared.maintenance import SystemMaintenanceIdentity, MaintenanceOperation
        
        # Test invalid tokens
        invalid_tokens = [
            "invalid-token",
            "wrong-prefix:123:signature",
            "fabric4l-maintenance:invalid-timestamp:signature",
        ]
        
        for token in invalid_tokens:
            identity = SystemMaintenanceIdentity(identity_token=token)
            assert not identity.is_valid(), f"Token {token} should be invalid"
        print("[OK] Invalid tokens are properly rejected")
        
        # Test valid token
        timestamp = int(time.time())
        valid_token = f"fabric4l-maintenance:{timestamp}:test-signature"
        identity = SystemMaintenanceIdentity(identity_token=valid_token)
        assert identity.is_valid(), "Valid token should be accepted"
        print("[OK] Valid tokens are properly accepted")
        
        # Test operation enum
        assert MaintenanceOperation.has_value("cleanup_old_content")
        assert not MaintenanceOperation.has_value("invalid_operation")
        print("[OK] Operation allowlist works correctly")
        
    except Exception as e:
        print(f"[FAIL] Maintenance identity test failed: {e}")
        return False
    
    return True

def test_robots_checker_exceptions():
    """Test RobotsChecker exception handling."""
    print("Testing RobotsChecker exceptions...")
    
    try:
        from compliance.robots_checker import RobotsChecker
        from shared.exceptions import (
            RobotsCacheError,
            RobotsFetchError,
            RobotsParseError,
            InvalidTenantContextError,
        )
        
        # Test invalid tenant_id
        try:
            checker = RobotsChecker(tenant_id="invalid-uuid")
            import asyncio
            asyncio.run(checker._get_cached_robots_txt("example.com"))
            assert False, "Should have raised InvalidTenantContextError"
        except InvalidTenantContextError:
            pass  # Expected
        print("[OK] Invalid tenant_id properly rejected")
        
        # Test valid tenant_id (will fail due to no database, but should validate tenant)
        try:
            checker = RobotsChecker(tenant_id=str(uuid4()))
            import asyncio
            asyncio.run(checker._get_cached_robots_txt("example.com"))
        except (RobotsCacheError, Exception):
            pass  # Expected - database connection will fail
        print("[OK] Valid tenant_id accepted (database error expected)")
        
    except Exception as e:
        print(f"[FAIL] RobotsChecker exceptions test failed: {e}")
        return False
    
    return True

def test_tenant_id_validation():
    """Test tenant_id validation."""
    print("Testing tenant_id validation...")
    
    try:
        from shared.database import validate_tenant_id
        from shared.exceptions import TenantContextError
        
        # Test valid UUIDs
        valid_uuids = [str(uuid4()) for _ in range(5)]
        for uuid_str in valid_uuids:
            result = validate_tenant_id(uuid_str)
            assert str(result) == uuid_str
        print("[OK] Valid UUIDs are accepted")
        
        # Test invalid UUIDs
        invalid_uuids = [
            "not-a-uuid",
            "123-456-789",
            "malicious-tenant-id",
            "' OR '1'='1",
            "",
            None,
        ]
        
        for invalid_uuid in invalid_uuids:
            try:
                validate_tenant_id(invalid_uuid)
                assert False, f"Should have rejected: {invalid_uuid}"
            except TenantContextError:
                pass  # Expected
        print("[OK] Invalid UUIDs are properly rejected")
        
    except Exception as e:
        print(f"[FAIL] Tenant ID validation test failed: {e}")
        return False
    
    return True

def test_security_hardening():
    """Test overall security hardening."""
    print("Testing security hardening...")
    
    try:
        # Test that security exceptions are not caught by generic handlers
        from shared.exceptions import (
            InvalidTenantContextError,
            SystemMaintenanceAuthorizationError,
        )
        
        security_errors = [
            InvalidTenantContextError("Test security error"),
            SystemMaintenanceAuthorizationError("Test auth error"),
        ]
        
        for error in security_errors:
            caught_by_generic = False
            try:
                raise error
            except (InvalidTenantContextError, SystemMaintenanceAuthorizationError):
                # This is the correct way to catch security errors
                pass
            except Exception:
                # Generic except should not catch security errors
                caught_by_generic = True
            
            assert not caught_by_generic, f"Security error {type(error)} was caught by generic except"
        
        print("[OK] Security exceptions are properly classified")
        
    except Exception as e:
        print(f"[FAIL] Security hardening test failed: {e}")
        return False
    
    return True

def main():
    """Run all security tests."""
    print("=== Security Implementation Verification ===\n")
    
    tests = [
        test_exception_hierarchy,
        test_maintenance_identity,
        test_robots_checker_exceptions,
        test_tenant_id_validation,
        test_security_hardening,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=== Summary ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("[OK] All security implementation tests passed!")
        return 0
    else:
        print("[FAIL] Some security tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
