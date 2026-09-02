"""Deterministic wait helpers for asynchronous tests.

Replaces fixed ``asyncio.sleep(...)`` waits with signal-based polling so tests
are deterministic under load and fail loudly with the awaited condition when it
never occurs.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable


async def wait_until(
    predicate: Callable[[], bool],
    *,
    timeout: float = 2.0,
    interval: float = 0.01,
    description: str = "condition",
) -> None:
    """Poll ``predicate`` until it returns True or ``timeout`` seconds elapse.

    Raises AssertionError (naming ``description``) on timeout so the failure
    identifies the awaited condition instead of silently passing.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        if predicate():
            return
        if loop.time() >= deadline:
            raise AssertionError(f"Timed out after {timeout}s waiting for {description}")
        await asyncio.sleep(interval)


async def wait_for_background_tasks(
    tasks_before: set[asyncio.Task],
    *,
    timeout: float = 2.0,
    interval: float = 0.01,
    description: str = "background tasks",
) -> None:
    """Wait for every task created after ``tasks_before`` to finish.

    Use to deterministically flush fire-and-forget deliveries (e.g. an asyncio
    ``create_task`` message bus) before asserting on their effects.
    """

    def _settled() -> bool:
        return not any(not t.done() for t in asyncio.all_tasks() - tasks_before)

    await wait_until(_settled, timeout=timeout, interval=interval, description=description)