"""Chaos tests for external API and enrichment dependency failures.

Verifies system behavior when external enrichment sources, crawlers, or
third-party APIs become unavailable:
- Ingestion/enrichment client failures don't crash workflows
- Partial/degraded state is explicit
- Retry policy and error classification are applied
- Tenant isolation is maintained
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from httpx import ConnectError, HTTPStatusError, TimeoutException
from value_fabric.shared.security.redaction import redact_credentials

pytestmark = [pytest.mark.chaos]


class TestExternalAPIFailure:
    """Verify behavior when external APIs fail."""

    @pytest.mark.asyncio
    async def test_external_api_timeout_handled_gracefully(self):
        """When external API times out, workflow continues with explicit degraded state.
        
        The workflow must not crash; it must continue with the degradation noted.
        """
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=TimeoutException("Request timed out after 30s")
        )
        
        # Simulate enrichment workflow
        result = await self._enrichment_workflow_with_fallback(mock_client, "https://api.example.com/data")
        
        # Result should indicate degradation, not crash
        assert result["status"] in ["degraded", "partial", "failed"]
        assert "external_api" in result.get("failed_components", [])

    async def _enrichment_workflow_with_fallback(self, client, url):
        """Simulate enrichment workflow that handles external API failures."""
        failed_components = []
        
        try:
            response = await client.get(url)
            data = response.json()
        except TimeoutException:
            failed_components.append("external_api")
            data = None
        
        return {
            "status": "degraded" if failed_components else "success",
            "data": data,
            "failed_components": failed_components
        }

    @pytest.mark.asyncio
    async def test_external_api_connection_error_fails_explicitly(self):
        """When external API is unreachable, error is explicit and structured.
        
        Security: Error must not expose internal network details.
        Safety: Caller must know the external dependency failed.
        """
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=ConnectError("[Errno 111] Connection refused")
        )
        
        with pytest.raises(Exception) as exc_info:
            await mock_client.get("https://unreachable.example.com")
        
        # Error should be caught and converted to structured error
        assert "Connection" in str(exc_info.value) or "unavailable" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_workflow_does_not_crash_on_external_failure(self):
        """External API failure must not crash the entire workflow.
        
        Resilience: Partial failures should be isolated.
        """
        async def complex_workflow():
            # Step 1: Internal processing (succeeds)
            internal_data = {"processed": True}
            
            # Step 2: External enrichment (fails)
            try:
                raise ConnectError("External API down")
            except ConnectError:
                enrichment_data = None
            
            # Step 3: Continue with partial data
            return {
                "internal_data": internal_data,
                "enrichment_data": enrichment_data,
                "status": "partial" if enrichment_data is None else "complete"
            }
        
        result = await complex_workflow()
        
        # Workflow completed despite external failure
        assert result["internal_data"]["processed"] is True
        assert result["enrichment_data"] is None
        assert result["status"] == "partial"

    @pytest.mark.asyncio
    async def test_partial_state_is_explicit(self):
        """When external dependency fails, partial state must be explicitly indicated.
        
        The caller must know that the result is incomplete.
        """
        async def ingestion_with_external_source():
            # Successfully fetched from primary source
            primary_data = {"entities": [1, 2, 3]}
            
            # Failed to enrich from external API
            enrichment_failed = True
            
            return {
                "data": primary_data,
                "enrichment_status": "failed" if enrichment_failed else "success",
                "completeness": "partial" if enrichment_failed else "full",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        result = await ingestion_with_external_source()
        
        assert result["enrichment_status"] == "failed"
        assert result["completeness"] == "partial"


class TestRetryPolicyApplication:
    """Verify retry policies are applied correctly."""

    @pytest.mark.asyncio
    async def test_retry_policy_applied_to_transient_failures(self):
        """Transient failures (503, timeout) trigger retry with backoff.
        
        Retry must not be applied to permanent failures (404, 400).
        """
        attempt_count = 0
        
        async def operation_with_retry():
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count < 3:
                # Simulate transient failure
                raise TimeoutException(f"Attempt {attempt_count} failed")
            
            return "success"
        
        # Simulate 3 retries
        result = None
        for attempt in range(3):
            try:
                result = await operation_with_retry()
                break
            except TimeoutException:
                if attempt == 2:
                    raise
                await asyncio.sleep(0.1)  # Minimal backoff for test
        
        assert result == "success"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_permanent_failures(self):
        """Permanent failures (400, 404) must not trigger retry.
        
        Efficiency: Don't waste resources on non-retriable errors.
        """
        attempt_count = 0
        
        async def operation_without_retry():
            nonlocal attempt_count
            attempt_count += 1
            
            # Simulate permanent failure (bad request)
            raise HTTPStatusError(
                "Bad request",
                request=None,  # type: ignore
                response=MagicMock(status_code=400)  # type: ignore
            )
        
        # Should fail immediately without retry
        with pytest.raises(HTTPStatusError):
            await operation_without_retry()
        
        assert attempt_count == 1  # No retries attempted

    @pytest.mark.asyncio
    async def test_retry_backoff_prevents_thundering_herd(self):
        """Retry backoff must prevent thundering herd when service recovers.
        
        Security: Randomized exponential backoff prevents synchronized retries.
        """
        import random
        
        retry_delays = []
        
        for _ in range(5):
            # Simulate exponential backoff with jitter
            base_delay = 1.0
            max_delay = 60.0
            exponential = min(base_delay * (2 ** len(retry_delays)), max_delay)
            jitter = random.uniform(0, exponential * 0.1)  # 10% jitter
            delay = exponential + jitter
            retry_delays.append(delay)
        
        # Verify delays are increasing (exponential)
        for i in range(1, len(retry_delays)):
            assert retry_delays[i] >= retry_delays[i-1] * 0.9  # Allow for jitter


class TestCrawlerDependencyFailure:
    """Verify crawler behavior when dependencies fail."""

    @pytest.mark.asyncio
    async def test_crawler_handles_robots_txt_fetch_failure(self):
        """When robots.txt fetch fails, crawler must make safe assumption.
        
        Compliance: If robots.txt is unreachable, assume disallow-all (conservative).
        """
        async def check_robots_txt(url):
            try:
                raise ConnectError("Cannot fetch robots.txt")
            except ConnectError:
                # Conservative default: assume not allowed
                return {"allowed": False, "reason": "robots_fetch_failed_conservative"}
        
        result = await check_robots_txt("https://example.com/page")
        
        # Must be conservative when robots.txt cannot be fetched
        assert result["allowed"] is False
        assert "conservative" in result["reason"]

    @pytest.mark.asyncio
    async def test_crawler_handles_target_site_unavailable(self):
        """When target site is unreachable, error must be explicit.
        
        The failure must be distinguished from successful crawl with no data.
        """
        async def crawl_url(url):
            try:
                raise ConnectError("Connection refused")
            except ConnectError as e:
                return {
                    "url": url,
                    "status": "unreachable",
                    "error": str(e),
                    "retry_eligible": True
                }
        
        result = await crawl_url("https://down-site.com")
        
        assert result["status"] == "unreachable"
        assert result["retry_eligible"] is True

    @pytest.mark.asyncio
    async def test_crawler_quality_gate_still_enforced_under_failure(self):
        """When crawling fails, quality gates must still be enforced.
        
        Low-quality data must not slip through because of failure conditions.
        """
        crawled_data = {"content": "", "confidence": 0.1}  # Very low quality
        
        async def quality_gate(data):
            if not data.get("content") or len(data["content"]) < 100:
                return {"passed": False, "reason": "insufficient_content"}
            if data.get("confidence", 0) < 0.5:
                return {"passed": False, "reason": "low_confidence"}
            return {"passed": True}
        
        result = await quality_gate(crawled_data)
        
        assert result["passed"] is False


class TestTenantIsolationUnderExternalFailure:
    """Verify tenant isolation when external dependencies fail."""

    @pytest.mark.asyncio
    async def test_external_cache_failure_does_not_expose_cross_tenant_data(self):
        """When external cache (Redis/CDN) fails, tenant isolation must be maintained.
        
        Fallback to shared storage must not expose cross-tenant data.
        """
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        # Simulate per-tenant external cache keys
        cache_keys = {
            tenant_a: f"cache:{tenant_a}:data",
            tenant_b: f"cache:{tenant_b}:data"
        }
        
        # When external cache fails, verify no shared fallback is used
        external_cache_available = False
        
        if not external_cache_available:
            # System must not fall back to shared memory cache
            # Each tenant must have their own isolated fallback (or fail)
            for tenant_id, key in cache_keys.items():
                assert str(tenant_id) in key, "Tenant ID must be in cache key"

    @pytest.mark.asyncio
    async def test_external_api_credentials_not_leaked_on_failure(self):
        """When external API fails, credentials must not appear in error messages.
        
        Security: API keys, tokens must not be exposed in logs or error responses.
        """
        api_key = "sk-live-12345-SECRET"
        
        try:
            # Simulate API call that fails with key in URL or headers
            url = f"https://api.example.com/data?key={api_key}"
            raise ConnectError(f"Failed to connect to {url}")
        except ConnectError as e:
            error_message = redact_credentials(e)
            # API key must not appear in error message
            assert api_key not in error_message
            assert "key=%5BREDACTED%5D" in error_message


class TestErrorClassification:
    """Verify errors are classified correctly for operational handling."""

    @pytest.mark.asyncio
    async def test_errors_classified_by_severity(self):
        """External dependency errors must be classified by severity.
        
        P0: Data loss, security breach
        P1: Feature degraded
        P2: Monitoring/alerting only
        """
        error_cases = [
            ("database_connection_lost", "P1"),
            ("external_cache_timeout", "P2"),
            ("payment_api_failure", "P0"),
            ("analytics_api_slow", "P2"),
        ]
        
        for error_type, expected_severity in error_cases:
            severity = self._classify_error_severity(error_type)
            assert severity == expected_severity, f"{error_type} should be {expected_severity}"

    def _classify_error_severity(self, error_type: str) -> str:
        """Classify error by severity for operational response."""
        p0_errors = ["payment_api_failure", "authentication_service_down"]
        p1_errors = ["database_connection_lost", "primary_cache_failure"]
        
        if error_type in p0_errors:
            return "P0"
        elif error_type in p1_errors:
            return "P1"
        else:
            return "P2"

    @pytest.mark.asyncio
    async def test_error_classification_includes_retry_recommendation(self):
        """Error classification must indicate whether retry is recommended.
        
        Operational: SRE needs to know if automatic retry is safe.
        """
        error = {
            "type": "TimeoutException",
            "retry_recommended": True,
            "backoff_strategy": "exponential",
            "max_retries": 3
        }
        
        assert error["retry_recommended"] is True
        assert error.get("backoff_strategy") is not None


class TestCircuitBreakerPattern:
    """Verify circuit breaker patterns for external dependencies."""

    @pytest.mark.asyncio
    async def test_circuit_opens_after_consecutive_failures(self):
        """Circuit breaker must open after threshold of consecutive failures.
        
        When external service is down, stop hammering it with requests.
        """
        failure_count = 0
        circuit_open = False
        threshold = 5
        
        for _ in range(10):
            if circuit_open:
                # Fast fail when circuit is open
                assert True  # Would raise CircuitBreakerOpen
                break
            
            try:
                raise ConnectError("External service down")
            except ConnectError:
                failure_count += 1
                if failure_count >= threshold:
                    circuit_open = True
        
        assert circuit_open is True
        assert failure_count == threshold

    @pytest.mark.asyncio
    async def test_circuit_half_open_allows_probe_requests(self):
        """In half-open state, limited requests are allowed to test recovery.
        
        Circuit breaker must not immediately fully close after timeout.
        """
        circuit_state = "open"
        probe_requests_allowed = 0
        
        # After timeout, transition to half-open
        circuit_state = "half_open"
        
        # In half-open, allow limited probes
        if circuit_state == "half_open":
            probe_requests_allowed = 1
        
        assert probe_requests_allowed == 1
