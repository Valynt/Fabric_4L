"""Robots.txt compliance checker.

Fetches, caches, and enforces robots.txt rules for ethical web crawling.
Uses Protego for fast parsing and respects crawl-delay directives.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urljoin, urlparse
from uuid import UUID

import httpx
import structlog
from protego import Protego
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..shared.circuit_breaker import get_circuit_breaker_manager
from ..shared.config import settings
from ..shared.database import get_db_session
from ..shared.exceptions import (
    InvalidTenantContextError,
    RobotsCacheError,
    RobotsFetchError,
    RobotsParseError,
    TenantContextError,
)
from ..shared.models import RobotsTxtCache


class RobotsChecker__get_robots_txtResult(TypedDictModel):
    content: Any
    http_status: Any
    rules: Any


class RobotsChecker__parse_robots_txtResult(TypedDictModel):
    parse_error: Any


class RobotsChecker__get_cached_robots_txtResult(TypedDictModel):
    content: Any
    expires_at: Any
    fetched_at: Any
    rules: Any


logger = structlog.get_logger()


def _validated_tenant_uuid(tenant_id: str | None) -> UUID | None:
    """Return a UUID tenant context when one is supplied.

    Robots.txt is public metadata, but callers may still provide a tenant
    context for auditability. Invalid tenant context must fail closed before any
    cache access occurs.
    """
    if not tenant_id:
        return None

    try:
        return UUID(tenant_id)
    except (ValueError, TypeError) as exc:
        raise InvalidTenantContextError(
            f"Invalid tenant_id format: {tenant_id}", tenant_id=tenant_id
        ) from exc


class RobotsChecker:
    """Checker for robots.txt compliance.

    Handles fetching, caching, and parsing of robots.txt files
    with proper rate limiting and TTL management.
    """

    def __init__(
        self,
        tenant_id: str | None = None,
        user_agent: str | None = None,
        cache_ttl_hours: int | None = None,
        respect_crawl_delay: bool = True,
        strict_mode: bool | None = None,
    ):
        self.tenant_id = tenant_id
        self.user_agent = user_agent or "ValueFabricBot/1.0"
        self.cache_ttl_hours = cache_ttl_hours or settings.robots_txt_cache_hours
        self.respect_crawl_delay = respect_crawl_delay
        self.strict_mode = (
            strict_mode
            if strict_mode is not None
            else (settings.strict_robots_enforcement or settings.robots_txt_strict_mode)
        )
        self._http_client: httpx.AsyncClient | None = None
        self.logger = logger

        # Initialize circuit breaker for robots.txt fetches
        self._circuit_breaker = get_circuit_breaker_manager().create_breaker(
            name="robots_txt_fetch",
            failure_threshold=5,
            recovery_timeout=30,
            expected_exception=(httpx.RequestError, httpx.TimeoutException),
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=10.0, headers={"User-Agent": self.user_agent}, follow_redirects=True
            )
        return self._http_client

    async def close(self):
        """Close HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    def _strict_fetch_failure_response(self, domain: str) -> tuple[bool, str, dict[str, Any]]:
        return (
            False,
            "robots.txt fetch failed (strict mode): internal error",
            {
                "strict_mode": True,
                "domain": domain,
                "error": "ROBOTS_FETCH_ERROR",
                "reason_code": "ROBOTS_FETCH_ERROR",
            },
        )

    def _strict_missing_robots_response(self, domain: str) -> tuple[bool, str, dict[str, Any]]:
        return (
            False,
            "robots.txt required but not available (strict mode)",
            {
                "strict_mode": True,
                "domain": domain,
            },
        )

    def _parse_failure_response(self) -> tuple[bool, str | None, dict[str, Any]]:
        if self.strict_mode:
            return (
                False,
                "robots.txt parse error (strict mode)",
                {
                    "parse_error": "ROBOTS_PARSE_ERROR",
                    "strict_mode": True,
                    "reason_code": "ROBOTS_PARSE_ERROR",
                },
            )

        return True, None, {"parse_error": "ROBOTS_PARSE_ERROR"}

    async def check_url(
        self, url: str, force_refresh: bool = False, job_id: str | None = None
    ) -> tuple[bool, str | None, dict | None]:
        """Check if a URL is allowed by robots.txt.

        Args:
            url: URL to check
            force_refresh: Force refresh of robots.txt cache

        Returns:
            Tuple of (allowed: bool, reason: str, rules: dict)
            - allowed: True if crawling is permitted
            - reason: Human-readable explanation if blocked
            - rules: Parsed robots.txt rules for this URL
        """
        parsed = urlparse(url)
        domain = parsed.netloc
        robots_url = urljoin(f"{parsed.scheme}://{domain}", "/robots.txt")

        # Get or fetch robots.txt
        try:
            robots_data = await self._get_robots_txt(domain, robots_url, force_refresh)
        except RobotsFetchError as e:
            self.logger.warning(
                "robots compliance decision",
                tenant_id=self.tenant_id,
                domain=domain,
                job_id=job_id,
                decision="blocked" if self.strict_mode else "error",
                reason_code="ROBOTS_FETCH_ERROR",
                error=repr(e),
            )
            if self.strict_mode:
                # Emit metric for strict mode block
                from ..metrics.prometheus_metrics import get_metrics

                metrics = get_metrics()
                if metrics:
                    metrics.increment_strict_robots_block(domain=domain, reason="fetch_error")

                # Audit log entry
                logger.error(
                    "robots.txt fetch failed in strict mode", exc_info=e, extra={"domain": domain}
                )
                return self._strict_fetch_failure_response(domain)
            # In permissive mode, re-raise so caller can decide to allow
            raise

        if robots_data is None:
            if self.strict_mode:
                # Emit metric for strict mode block
                from ..metrics.prometheus_metrics import get_metrics

                metrics = get_metrics()
                if metrics:
                    metrics.increment_strict_robots_block(domain=domain, reason="not_available")

                # Audit log entry
                logger.warning(
                    "Strict robots mode: blocked due to robots.txt not available",
                    tenant_id=self.tenant_id,
                    domain=domain,
                    strict_mode=True,
                )

                return self._strict_missing_robots_response(domain)
            # No robots.txt found - assume allowed in permissive mode
            return True, None, None

        try:
            # Parse robots.txt
            rp = Protego.parse(robots_data.get("content", ""))

            # Check if URL is allowed
            path = parsed.path or "/"
            allowed = rp.can_fetch(self.user_agent, path)

            # Get crawl delay
            crawl_delay = None
            if self.respect_crawl_delay:
                crawl_delay = rp.crawl_delay(self.user_agent)

            rules = {
                "allowed": allowed,
                "crawl_delay": crawl_delay,
                "domain": domain,
                "robots_url": robots_url,
            }

            if not allowed:
                reason = f"Disallowed by robots.txt for {self.user_agent}"
                return False, reason, rules

            if crawl_delay:
                rules["crawl_delay"] = crawl_delay

            return True, None, rules

        except Exception:
            self.logger.error(
                "robots compliance decision",
                domain=domain,
                tenant_id=self.tenant_id,
                job_id=job_id,
                decision="blocked" if self.strict_mode else "allowed",
                reason_code="ROBOTS_PARSE_ERROR",
            )
            if self.strict_mode:
                return self._parse_failure_response()
            # If parsing fails, allow but log in permissive mode
            return self._parse_failure_response()

    async def _get_robots_txt(
        self, domain: str, robots_url: str, force_refresh: bool = False
    ) -> dict[str, Any] | None:
        """Get robots.txt content, using cache if available.

        Args:
            domain: Domain name
            robots_url: URL to robots.txt
            force_refresh: Force cache refresh

        Returns:
            Dict with content and metadata, or None if not available
        """
        # Check cache first
        if not force_refresh:
            try:
                cached = self._get_cached_robots_txt(domain)
                if cached:
                    self.logger.debug("Using cached robots.txt", domain=domain)
                    return cached
            except RobotsCacheError as e:
                # Log cache error but continue to fetch fresh
                self.logger.warning(
                    "Cache error, fetching fresh robots.txt", domain=domain, error=repr(e)
                )

        # Fetch fresh robots.txt
        try:
            client = await self._get_client()

            # Wrap HTTP call with circuit breaker
            async def _fetch_robots():
                return await client.get(robots_url)

            response = await self._circuit_breaker.call(_fetch_robots)

            if response.status_code == 404:
                # No robots.txt - all allowed
                self.logger.debug("No robots.txt found", domain=domain)
                return None

            response.raise_for_status()
            content = response.text

            # Parse and cache
            try:
                parsed_rules = self._parse_robots_txt(content)
            except RobotsParseError as e:
                # Log parse error but cache the failure
                self.logger.warning("Parse error, caching failure", domain=domain, error=repr(e))
                self._cache_robots_txt(
                    domain=domain,
                    url=robots_url,
                    content=content,
                    rules={},
                    http_status=response.status_code,
                    is_valid=False,
                    error=repr(e),
                )
                # Be conservative and allow crawling on parse errors
                return None

            try:
                self._cache_robots_txt(
                    domain=domain,
                    url=robots_url,
                    content=content,
                    rules=parsed_rules,
                    http_status=response.status_code,
                )
            except RobotsCacheError as e:
                # Log cache error but continue with fetched data
                self.logger.warning("Failed to cache robots.txt", domain=domain, error=repr(e))

            self.logger.info("Fetched and cached robots.txt", domain=domain, size=len(content))

            return RobotsChecker__get_robots_txtResult.model_validate(
                {"content": content, "rules": parsed_rules, "http_status": response.status_code}
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None

            self.logger.error(
                "HTTP error fetching robots.txt", domain=domain, status=e.response.status_code
            )

            # Cache the error state
            self._cache_robots_txt(
                domain=domain,
                url=robots_url,
                content=None,
                rules={},
                http_status=e.response.status_code,
                is_valid=False,
                error="HTTP_STATUS_ERROR",
            )

            # On error, be conservative and assume allowed
            return None

        except httpx.RequestError as e:
            # Network/connection errors - these are recoverable
            raise RobotsFetchError(
                f"Network error fetching robots.txt for domain {domain}: {e!r}", domain=domain
            )
        except Exception as e:
            # Convert other errors to RobotsFetchError
            raise RobotsFetchError(
                f"Unexpected error fetching robots.txt for domain {domain}: {e!r}", domain=domain
            )

    def _get_cached_robots_txt(self, domain: str) -> dict[str, Any] | None:
        """Get cached robots.txt from global public metadata cache.

        This cache contains only public robots.txt response data and does not
        require tenant isolation. The tenant_id column is legacy/system-owned only.

        Args:
            domain: Domain name

        Returns:
            Cached robots.txt data or None if expired/not found

        Raises:
            InvalidTenantContextError: If tenant_id is provided but invalid
            RobotsCacheError: If cache operation fails
        """
        tenant_uuid = _validated_tenant_uuid(self.tenant_id)

        try:
            # Use require_tenant=False for global public metadata cache
            # This is NOT an admin bypass - it's a global public cache
            with get_db_session(tenant_id=tenant_uuid, require_tenant=False) as session:
                query = session.query(RobotsTxtCache).filter(
                    RobotsTxtCache.domain == domain,
                    RobotsTxtCache.expires_at > datetime.now(UTC),
                    RobotsTxtCache.is_valid.is_(True),
                )

                # Global cache - no tenant filtering required
                # The tenant_id column is legacy/system-owned only

                cache_entry = query.first()

                if cache_entry:
                    return RobotsChecker__get_cached_robots_txtResult.model_validate(
                        {
                            "content": cache_entry.content,
                            "rules": cache_entry.rules,
                            "fetched_at": cache_entry.fetched_at,
                            "expires_at": cache_entry.expires_at,
                        }
                    )

                return None

        except TenantContextError:
            # Re-raise tenant context errors - these are security failures
            raise
        except Exception as e:
            # Convert to specific RobotsCacheError for proper error classification
            raise RobotsCacheError(
                f"Failed to retrieve cached robots.txt for domain {domain}: {e!r}", domain=domain
            )

    def _cache_robots_txt(
        self,
        domain: str,
        url: str,
        content: str | None,
        rules: dict[str, Any],
        http_status: int,
        is_valid: bool = True,
        error: str | None = None,
    ):
        """Cache robots.txt in global public metadata cache.

        This cache stores only public robots.txt response data and does not
        require tenant isolation. The tenant_id column is legacy/system-owned only.

        Args:
            domain: Domain name
            url: URL of robots.txt
            content: Raw robots.txt content
            rules: Parsed rules dict
            http_status: HTTP status code
            is_valid: Whether parsing succeeded
            error: Error message if parsing failed

        Raises:
            InvalidTenantContextError: If tenant_id is provided but invalid
            RobotsCacheError: If cache operation fails
        """
        tenant_uuid = _validated_tenant_uuid(self.tenant_id)

        try:
            # Use require_tenant=False for global public metadata cache
            # This is NOT an admin bypass - it's a global public cache
            with get_db_session(tenant_id=tenant_uuid, require_tenant=False) as session:
                # Check if entry exists (global cache - no tenant filtering)
                existing = (
                    session.query(RobotsTxtCache).filter(RobotsTxtCache.domain == domain).first()
                )

                now = datetime.now(UTC)
                expires_at = now + timedelta(hours=self.cache_ttl_hours)

                if existing:
                    # Update existing
                    existing.content = content
                    existing.url = url
                    existing.rules = rules
                    existing.fetched_at = now
                    existing.expires_at = expires_at
                    existing.http_status = http_status
                    existing.is_valid = is_valid
                    existing.parse_error = error
                else:
                    # Create new - tenant_id is legacy/system-owned only
                    cache_entry = RobotsTxtCache(
                        domain=domain,
                        tenant_id=tenant_uuid,  # Legacy column - system-owned only
                        content=content,
                        url=url,
                        rules=rules,
                        fetched_at=now,
                        expires_at=expires_at,
                        http_status=http_status,
                        is_valid=is_valid,
                        parse_error=error,
                    )
                    session.add(cache_entry)

                session.commit()

        except TenantContextError:
            # Re-raise tenant context errors - these are security failures
            raise
        except Exception as e:
            # Convert to specific RobotsCacheError for proper error classification
            raise RobotsCacheError(
                f"Failed to cache robots.txt for domain {domain}: {e!r}", domain=domain
            )

    def _parse_robots_txt(self, content: str) -> dict[str, Any]:
        """Parse robots.txt content into structured rules.

        Args:
            content: Raw robots.txt content

        Returns:
            Dict of user_agent -> rules

        Raises:
            RobotsParseError: If robots.txt parsing fails
        """
        try:
            rp = Protego.parse(content)

            # Extract rules for common user agents
            user_agents = ["*", "ValueFabricBot", "ValueFabricBot/1.0", "Googlebot"]
            rules = {}

            for ua in user_agents:
                crawl_delay = rp.crawl_delay(ua)
                request_rate = rp.request_rate(ua)

                rules[ua] = {
                    "crawl_delay": crawl_delay,
                    "request_rate": str(request_rate) if request_rate else None,
                }

            return rules

        except Exception as e:
            # Convert to specific RobotsParseError for proper error classification
            logger.error("Failed to parse robots.txt content", exc_info=e)
            raise RobotsParseError(
                "Failed to parse robots.txt content",
                content_preview=content[:200] if content else None,
            )

    async def get_crawl_delay(self, url: str) -> float | None:
        """Get crawl-delay directive for a domain.

        Args:
            url: URL to check

        Returns:
            Crawl delay in seconds or None
        """
        parsed = urlparse(url)
        domain = parsed.netloc
        robots_url = urljoin(f"{parsed.scheme}://{domain}", "/robots.txt")

        robots_data = await self._get_robots_txt(domain, robots_url)

        if not robots_data:
            return None

        try:
            rp = Protego.parse(robots_data.get("content", ""))
            return rp.crawl_delay(self.user_agent)
        except Exception:
            return None
