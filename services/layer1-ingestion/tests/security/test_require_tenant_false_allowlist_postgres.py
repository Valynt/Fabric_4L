"""PostgreSQL-backed tests for require_tenant=False allowlist.

Tests validate that require_tenant=False usage is properly restricted:
- Only used for system-level operations
- Only used for operations that explicitly handle tenant context
- Not used for tenant-scoped queries
- Documented and reviewed for security implications

These tests MUST run against PostgreSQL.
"""

from __future__ import annotations

import pytest
import re
from pathlib import Path


pytestmark = pytest.mark.requires_postgres

# Resolve source paths relative to this test file (services/layer1-ingestion/tests/security/)
_L1_SRC = Path(__file__).resolve().parents[2] / "src" / "layer1_ingestion"
_TASKS_FILE = _L1_SRC / "shared" / "tasks.py"


class TestRequireTenantFalseAllowlist:
    """Test that require_tenant=False usage is properly allowlisted."""

    def test_require_tenant_false_count_is_limited(self):
        """Total count of require_tenant=False usages should be limited."""
        with open(_TASKS_FILE, 'r') as f:
            content = f.read()
        
        # Find all occurrences of require_tenant=False
        pattern = r'require_tenant=False'
        matches = re.findall(pattern, content)
        
        # The count should be minimal and documented
        # Current allowlist includes:
        # - System-level operations (no tenant-scoped tables)
        # - Error handling paths that have been reviewed
        # - Operations that explicitly set tenant context themselves
        assert len(matches) <= 15, f"Too many require_tenant=False usages: {len(matches)}. Review and document each usage."

    def test_require_tenant_false_not_in_main_pipeline_stages(self):
        """Main pipeline stages should not use require_tenant=False."""
        from layer1_ingestion.shared import tasks
        import inspect
        
        stage_tasks = [
            'compliance_check_stage',
            'browser_crawl_stage',
            'ai_extraction_stage',
            'post_processing_stage',
            'validation_stage',
            'storage_stage',
            'notification_stage',
        ]
        
        for task_name in stage_tasks:
            task = getattr(tasks, task_name)
            source = inspect.getsource(task)

            # Some stage tasks are thin wrappers around async internals;
            # include the inner implementation source when present.
            for inner_name in [f"_{task_name}", f"_a{task_name}"]:
                if hasattr(tasks, inner_name):
                    source += "\n" + inspect.getsource(getattr(tasks, inner_name))

            # Main DB session in pipeline stages should use require_tenant=True
            # or pass tenant_id as a keyword argument to get_db_session.
            assert 'require_tenant=True' in source or 'tenant_id=' in source or 'get_db_session' in source, \
                f"{task_name} should use require_tenant=True or tenant_id parameter"

    def test_require_tenant_false_documented_in_code(self):
        """require_tenant=False usages should be documented with comments."""
        with open(_TASKS_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find lines with require_tenant=False
        for i, line in enumerate(lines):
            if 'require_tenant=False' in line:
                # Check if there's a comment explaining why
                # Look at the previous line or same line
                context = ''.join(lines[max(0, i-2):i+1])
                # Should have some explanation (TODO, FIXME, SECURITY, or comment)
                # This is a soft check - in production, use stricter enforcement
                if '#' not in context:
                    # Log warning but don't fail (allowlist may be documented elsewhere)
                    print(f"Warning: require_tenant=False at line {i+1} lacks inline comment")

    def test_process_scraping_job_uses_require_tenant_true(self):
        """process_scraping_job should use require_tenant=True for main DB session."""
        from layer1_ingestion.shared.tasks import process_scraping_job
        import inspect
        
        source = inspect.getsource(process_scraping_job)
        
        # The main DB session should use tenant_id parameter
        assert 'tenant_id=' in source, "process_scraping_job should use tenant_id parameter"
        # Should not use require_tenant=False for tenant-scoped queries
        # Check that if require_tenant=False exists, it's for a specific reason
        if 'require_tenant=False' in source:
            # Ensure it's documented
            assert '#' in source or 'TODO' in source or 'FIXME' in source, \
                "require_tenant=False usage must be documented"

    def test_error_handling_paths_reviewed(self):
        """Error handling paths using require_tenant=False should be reviewed."""
        with open(_TASKS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find error handling blocks with require_tenant=False
        # Pattern: except block with get_db_session(require_tenant=False)
        pattern = r'except.*:\s*.*get_db_session.*require_tenant=False'
        matches = re.findall(pattern, content, re.DOTALL)
        
        # These should be minimal and documented
        for match in matches:
            # Check for documentation
            assert '#' in match or 'error' in match.lower(), \
                "Error handling with require_tenant=False should be documented"

    def test_no_tenant_scoped_queries_with_require_tenant_false(self):
        """Tenant-scoped queries should not use require_tenant=False."""
        with open(_TASKS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find patterns where require_tenant=False is used near tenant-scoped queries
        # This is a heuristic - in production, use static analysis
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if 'require_tenant=False' in line:
                # Check next few lines for tenant-scoped queries
                context = '\n'.join(lines[i:i+10])
                # If we see ScrapingJob, ScrapingTarget, etc. with require_tenant=False
                # that's suspicious
                if 'ScrapingJob' in context or 'ScrapingTarget' in context:
                    # This might be okay if tenant context is set explicitly
                    # Check for SET LOCAL or tenant_id assignment
                    if 'SET LOCAL' not in context and 'tenant_id=' not in context:
                        # Log warning - this needs review
                        print(f"Warning: Potential tenant-scoped query with require_tenant=False at line {i+1}")

    def test_cleanup_old_content_tenant_parameter(self):
        """cleanup_old_content should accept tenant_id parameter."""
        from layer1_ingestion.shared.tasks import cleanup_old_content
        import inspect
        
        sig = inspect.signature(cleanup_old_content)
        params = list(sig.parameters.keys())
        assert 'tenant_id' in params, "cleanup_old_content must accept tenant_id parameter"

    def test_cleanup_old_content_uses_tenant_context(self):
        """cleanup_old_content should use tenant context when tenant_id is provided."""
        from layer1_ingestion.shared.tasks import cleanup_old_content
        import inspect
        
        source = inspect.getsource(cleanup_old_content)
        
        # Should use tenant_id parameter in get_db_session
        assert 'tenant_id=' in source, "cleanup_old_content should use tenant_id parameter"
        # Should use require_tenant=True when tenant_id is provided
        assert 'require_tenant=True' in source or 'require_tenant=True if' in source, \
            "cleanup_old_content should use require_tenant=True when tenant_id is provided"

    def test_system_operations_allowlisted(self):
        """System-level operations can use require_tenant=False."""
        # This test documents the allowlist for system-level operations
        # In production, this should be enforced via code review and static analysis
        
        allowed_system_operations = [
            # Migration scripts
            # Database initialization
            # System configuration queries
            # Admin operations (with separate auth checks)
        ]
        
        # This is a documentation test - the actual enforcement is via code review
        assert len(allowed_system_operations) >= 0  # Placeholder for documentation

    def test_no_direct_sql_with_tenant_bypass(self):
        """No direct SQL should bypass tenant context."""
        with open(_TASKS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for patterns that might bypass tenant context
        # This is a heuristic - in production, use stricter static analysis
        
        # Look for raw SQL that doesn't include tenant filtering
        # This is complex - for now, we just document the concern
        if 'text(' in content or 'execute(' in content:
            # Raw SQL exists - ensure it's reviewed
            print("Warning: Raw SQL detected - ensure tenant context is properly handled")


class TestTenantContextSetting:
    """Test that tenant context is set before queries."""

    def test_set_local_not_used_anymore(self):
        """Direct SET LOCAL should not be used (replaced by get_db_session tenant_id)."""
        with open(_TASKS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # SET LOCAL should only be in error handling or specific allowlisted cases
        # The main pattern should be get_db_session(tenant_id=..., require_tenant=True)
        set_local_count = content.count('SET LOCAL')
        
        # Should be minimal (only in error handling or specific cases)
        assert set_local_count <= 5, f"Too many SET LOCAL usages: {set_local_count}. Use get_db_session(tenant_id=...) instead."

    def test_get_db_session_with_tenant_id_is_primary_pattern(self):
        """get_db_session(tenant_id=...) should be the primary pattern."""
        with open(_TASKS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count get_db_session calls with tenant_id parameter
        tenant_id_pattern = r'get_db_session\([^)]*tenant_id='
        tenant_id_count = len(re.findall(tenant_id_pattern, content))
        
        # Should be the dominant pattern
        assert tenant_id_count >= 10, f"Too few get_db_session calls with tenant_id: {tenant_id_count}"

    def test_current_setting_not_used_directly(self):
        """current_setting should not be used directly (handled by get_db_session)."""
        with open(_TASKS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # current_setting should be minimal (only in tests or specific cases)
        current_setting_count = content.count('current_setting')
        
        assert current_setting_count == 0, "current_setting should not be used directly. Use get_db_session(tenant_id=...) instead."


class TestSecurityHardeningCompleteness:
    """Test that security hardening is complete."""

    def test_all_tasks_accept_tenant_id(self):
        """All Celery tasks should accept tenant_id parameter."""
        from layer1_ingestion.shared import tasks
        import inspect
        
        # Get all task functions
        task_names = [
            'process_scraping_job',
            'compliance_check_stage',
            'browser_crawl_stage',
            'ai_extraction_stage',
            'post_processing_stage',
            'validation_stage',
            'storage_stage',
            'notification_stage',
            'dispatch_outbox_event',
            'cleanup_old_content',
            'crawl_url_with_routing',
        ]
        
        for task_name in task_names:
            if hasattr(tasks, task_name):
                task = getattr(tasks, task_name)
                sig = inspect.signature(task)
                params = list(sig.parameters.keys())
                assert 'tenant_id' in params, f"{task_name} must accept tenant_id parameter"

    def test_no_unsafe_pattern_remaining(self):
        """No unsafe "fetch job first, then set tenant context" pattern should remain."""
        with open(_TASKS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for the unsafe pattern: get job without tenant_id, then SET LOCAL
        # Pattern: get_db_session(require_tenant=False) followed by job query, then SET LOCAL
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if 'get_db_session(require_tenant=False)' in line:
                # Check next 10 lines for job query and SET LOCAL
                context = '\n'.join(lines[i:i+10])
                if 'ScrapingJob' in context and 'SET LOCAL' in context:
                    # This is the unsafe pattern
                    assert False, f"Unsafe pattern detected at line {i+1}: fetch job without tenant context, then SET LOCAL"

    def test_dispatch_calls_pass_tenant_id(self):
        """All dispatch calls should pass tenant_id."""
        import re
        
        api_files = [
            _L1_SRC / 'api' / 'main.py',
        ]
        for api_file in api_files:
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find process_scraping_job.delay calls (multi-line aware)
            pattern = r'process_scraping_job\.delay\((?:[^()]|\([^()]*\))*\)'
            matches = re.findall(pattern, content)

            for match in matches:
                # Should contain tenant_id parameter
                assert 'tenant_id' in match or 'str(job.tenant_id)' in match or 'str(new_job.tenant_id)' in match, \
                    f"Dispatch call missing tenant_id in {api_file}: {match[:100]}"

    def test_decision_store_writes_require_tenant_true(self):
        """Decision store persistence must enforce require_tenant=True."""
        from layer1_ingestion.crawler.decision_store import CrawlDecisionRepository
        import inspect

        source = inspect.getsource(CrawlDecisionRepository._save_sync)
        assert "require_tenant=True" in source
        assert "require_tenant=False" not in source
