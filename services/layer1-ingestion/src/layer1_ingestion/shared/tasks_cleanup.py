"""Maintenance and cleanup tasks (facade).

This module re-exports the maintenance/cleanup group from
``layer1_ingestion.shared.tasks``, which remains the single source of truth.
It provides a cohesive import surface for tenant-scoped cleanup and raw-content
purging without moving any implementation.

Important: these bindings are snapshots of the canonical module. Celery task
names (including the explicitly-registered ``purge_expired_raw_content``) and
persistent patches keep addressing ``layer1_ingestion.shared.tasks.<name>``
exactly as before.
"""

from .tasks import (
    _enumerate_authorized_tenants_for_cleanup,
    cleanup_old_content,
    purge_expired_raw_content,
)

__all__ = [
    "_enumerate_authorized_tenants_for_cleanup",
    "cleanup_old_content",
    "purge_expired_raw_content",
]
