"""Browser pool management for Playwright crawler efficiency.

P1-01: Reuses browser instances to reduce startup overhead and resource usage.
Provides pre-warmed browser instances with lifecycle management.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import structlog
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from .crawler_config import CrawlerConfig, load_config

logger = structlog.get_logger()


@dataclass
class BrowserInstance:
    """Represents a single browser instance in the pool."""

    browser: Browser
    context: BrowserContext
    created_at: float = field(default_factory=time.time)
    usage_count: int = 0
    last_used_at: float = field(default_factory=time.time)
    is_healthy: bool = True


class BrowserPool:
    """Manages a pool of Playwright browser instances for efficient reuse.

    Features:
    - Pre-warmed browser instances
    - Automatic recycling after usage thresholds
    - Health monitoring and replacement
    - Configurable pool size
    """

    def __init__(
        self,
        pool_size: int = 5,
        max_usage_per_instance: int = 50,
        max_age_seconds: int = 600,
        config: CrawlerConfig | None = None,
    ):
        """Initialize browser pool.

        Args:
            pool_size: Number of browser instances to maintain
            max_usage_per_instance: Recycle browser after this many uses
            max_age_seconds: Recycle browser after this age
            config: Crawler configuration
        """
        self.config = config or load_config()
        self.pool_size = pool_size
        self.max_usage_per_instance = max_usage_per_instance
        self.max_age_seconds = max_age_seconds

        self._playwright = None
        self._pool: list[BrowserInstance] = []
        self._lock = asyncio.Lock()
        self._initialized = False

        logger.info(
            "Browser pool initialized",
            pool_size=pool_size,
            max_usage_per_instance=max_usage_per_instance,
            max_age_seconds=max_age_seconds,
        )

    async def initialize(self) -> None:
        """Initialize the browser pool with pre-warmed instances."""
        if self._initialized:
            return

        self._playwright = await async_playwright().start()

        # Pre-warm pool
        for i in range(self.pool_size):
            instance = await self._create_browser_instance()
            self._pool.append(instance)
            logger.debug("Browser instance created", instance_id=i, total=len(self._pool))

        self._initialized = True
        logger.info("Browser pool initialized successfully", pool_size=len(self._pool))

    async def _create_browser_instance(self) -> BrowserInstance:
        """Create a new browser instance with context.

        Raises:
            RuntimeError: If browser or context creation fails
        """
        try:
            browser = await self._playwright.chromium.launch(
                headless=self.config.headless,
                args=self.config.browser_args,
            )

            context = await browser.new_context(
                user_agent=self.config.user_agent,
                viewport=self.config.viewport,
                java_script_enabled=True,
                bypass_csp=True,
            )

            context.set_default_timeout(self.config.timeout_ms)
            context.set_default_navigation_timeout(self.config.navigation_timeout_ms)

            return BrowserInstance(browser=browser, context=context)
        except Exception as e:
            logger.error("Failed to create browser instance", error=str(e))
            raise RuntimeError(f"Browser instance creation failed: {e}") from e

    async def acquire(self) -> BrowserInstance:
        """Acquire a browser instance from the pool.

        Returns:
            BrowserInstance: A healthy browser instance

        Raises:
            RuntimeError: If pool is not initialized
        """
        if not self._initialized:
            await self.initialize()

        async with self._lock:
            # Try to get an available instance
            for instance in self._pool:
                if self._is_instance_healthy(instance):
                    instance.usage_count += 1
                    instance.last_used_at = time.time()
                    logger.debug(
                        "Browser instance acquired",
                        usage_count=instance.usage_count,
                        pool_size=len(self._pool),
                    )
                    return instance

            # No healthy instances available, create a new one
            logger.warning("No healthy instances in pool, creating new one")
            instance = await self._create_browser_instance()
            self._pool.append(instance)
            instance.usage_count += 1
            instance.last_used_at = time.time()
            return instance

    async def release(self, instance: BrowserInstance) -> None:
        """Release a browser instance back to the pool.

        Args:
            instance: The browser instance to release
        """
        async with self._lock:
            # Check if instance needs recycling
            if self._should_recycle_instance(instance):
                await self._recycle_instance(instance)
                # Create a replacement to maintain pool size
                new_instance = await self._create_browser_instance()
                self._pool.append(new_instance)
                logger.debug("Browser instance recycled and replaced")
            else:
                # Return to pool
                instance.last_used_at = time.time()
                logger.debug("Browser instance released back to pool")

    def _is_instance_healthy(self, instance: BrowserInstance) -> bool:
        """Check if a browser instance is healthy and reusable.

        Args:
            instance: Browser instance to check

        Returns:
            bool: True if instance is healthy
        """
        if not instance.is_healthy:
            return False

        # Check usage count
        if instance.usage_count >= self.max_usage_per_instance:
            return False

        # Check age
        age = time.time() - instance.created_at
        if age >= self.max_age_seconds:
            return False

        return True

    def _should_recycle_instance(self, instance: BrowserInstance) -> bool:
        """Determine if an instance should be recycled.

        Args:
            instance: Browser instance to check

        Returns:
            bool: True if instance should be recycled
        """
        return not self._is_instance_healthy(instance)

    async def _recycle_instance(self, instance: BrowserInstance) -> None:
        """Recycle a browser instance by closing it.

        Args:
            instance: Browser instance to recycle
        """
        try:
            await instance.context.close()
            await instance.browser.close()
            self._pool.remove(instance)
            logger.debug("Browser instance recycled", usage_count=instance.usage_count)
        except Exception as e:
            logger.error("Error recycling browser instance", error=str(e))
            # Remove from pool even if close failed
            if instance in self._pool:
                self._pool.remove(instance)

    async def get_page(self) -> tuple[BrowserInstance, Page]:
        """Acquire a browser instance and create a new page.

        Returns:
            Tuple of (BrowserInstance, Page)
        """
        instance = await self.acquire()
        page = await instance.context.new_page()
        return instance, page

    async def release_page(self, instance: BrowserInstance, page: Page) -> None:
        """Release a page and return the instance to the pool.

        Args:
            instance: Browser instance to release
            page: Page to close
        """
        try:
            await page.close()
        except Exception as e:
            logger.warning("Error closing page", error=str(e))
        finally:
            await self.release(instance)

    async def cleanup(self) -> None:
        """Clean up all browser instances in the pool."""
        async with self._lock:
            for instance in self._pool:
                try:
                    await instance.context.close()
                    await instance.browser.close()
                except Exception as e:
                    logger.error("Error closing browser instance during cleanup", error=str(e))

            self._pool.clear()

            if self._playwright:
                await self._playwright.stop()
                self._playwright = None

            self._initialized = False
            logger.info("Browser pool cleaned up")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics.

        Returns:
            Dictionary with pool statistics
        """
        healthy_count = sum(1 for inst in self._pool if self._is_instance_healthy(inst))
        total_usage = sum(inst.usage_count for inst in self._pool)

        return {
            "pool_size": len(self._pool),
            "healthy_instances": healthy_count,
            "total_usage": total_usage,
            "initialized": self._initialized,
        }


# Global browser pool instance
_global_browser_pool: BrowserPool | None = None


def get_browser_pool() -> BrowserPool:
    """Get the global browser pool instance.

    Returns:
        BrowserPool instance
    """
    global _global_browser_pool
    if _global_browser_pool is None:
        _global_browser_pool = BrowserPool()
    return _global_browser_pool
