"""Hot-reload utilities for secret rotation.

Provides decorators and context managers for applications that need
to reload configuration when secrets change.
"""

import functools
import logging
import os
import time
from typing import Any, Callable, TypeVar

from .watcher import SecretWatcher

logger = logging.getLogger(__name__)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

# Global registry of reload handlers
_reload_handlers: dict[str, list[Callable[[], None]]] = {}


def register_secret_reload_handler(
    secret_name: str,
    handler: Callable[[], None],
) -> None:
    """Register a handler to be called when a secret rotates.

    Args:
        secret_name: Name of the secret (e.g., "openai-api-key")
        handler: Function to call when secret changes
    """
    if secret_name not in _reload_handlers:
        _reload_handlers[secret_name] = []
    _reload_handlers[secret_name].append(handler)
    logger.debug(f"Registered reload handler for secret: {secret_name}")


def _get_secret_path(secret_name: str) -> str | None:
    """Get the filesystem path for a Kubernetes secret.

    In Kubernetes, secrets are mounted as files at:
    /secrets/<secret-name>/<key>

    Returns:
        Path to the secret file, or None if not found
    """
    # Standard K8s secret mount path
    k8s_path = f"/secrets/{secret_name}"

    if os.path.isdir(k8s_path):
        # Return first file in the directory
        files = os.listdir(k8s_path)
        if files:
            return os.path.join(k8s_path, files[0])

    # Alternative: Check environment variable pattern
    env_var = f"{secret_name.upper().replace('-', '_')}_FILE"
    if env_var in os.environ:
        return os.environ[env_var]

    return None


def reload_on_secret_change(
    secret_name: str,
    *,
    poll_interval: int = 30,
) -> Callable[[F], F]:
    """Decorator that reloads a function when secrets change.

    This decorator watches the specified secret and re-executes
    the wrapped function when the secret rotates.

    Args:
        secret_name: Name of the secret to watch
        poll_interval: Seconds between secret checks

    Returns:
        Decorator function

    Example:
        @reload_on_secret_change("openai-api-key")
        def get_llm_client():
            return OpenAI(api_key=load_secret("openai-api-key"))
    """

    def decorator(func: F) -> F:
        secret_path = _get_secret_path(secret_name)

        if not secret_path:
            logger.warning(
                f"Secret {secret_name} not found at standard paths, "
                f"hot-reload disabled for {func.__name__}"
            )
            return func

        # Create watcher for this secret
        watcher = SecretWatcher(poll_interval=poll_interval)

        # Track last reload time to prevent thrashing
        last_reload = [0.0]
        min_reload_interval = 5.0  # Minimum seconds between reloads

        def on_secret_change(new_content: str) -> None:
            now = time.time()
            if now - last_reload[0] < min_reload_interval:
                logger.debug("Ignoring secret change - too soon after last reload")
                return

            last_reload[0] = now
            logger.info(f"Secret {secret_name} changed, triggering reload handlers")

            # Call registered handlers
            for handler in _reload_handlers.get(secret_name, []):
                try:
                    handler()
                except Exception as e:
                    logger.error(f"Reload handler failed for {secret_name}: {e}")

        watcher.watch_file(secret_path, on_secret_change)

        # Start watcher in background
        import asyncio

        try:
            asyncio.get_event_loop().create_task(watcher.run_async())
            logger.info(
                f"Hot-reload enabled for {func.__name__} (watching {secret_name})"
            )
        except RuntimeError:
            logger.warning(
                f"No event loop available, hot-reload disabled for {func.__name__}"
            )

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Attach watcher for testing/debugging
        wrapper._secret_watcher = watcher
        return wrapper

    return decorator
