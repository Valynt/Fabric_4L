from __future__ import annotations

"""FastAPI middleware for tenant extraction.

DEPRECATED: This module is superseded by
``shared.identity.middleware.GovernanceMiddleware``.

It is kept temporarily so existing imports continue to work during the
migration. New code should use GovernanceMiddleware directly.
"""


import logging

from value_fabric.shared.identity.middleware import (
    GovernanceMiddleware as TenantMiddleware,  # noqa: F401
)

logger = logging.getLogger(__name__)
logger.warning(
    "layer4-agents.tenant.middleware is deprecated — import GovernanceMiddleware "
    "from shared.identity.middleware instead."
)
