"""Compatibility shim for the canonical Layer 4 module.

The implementation lives in ``layer4_agents.tenants.api.routes.admin_dashboard``. Keep this file as a thin
re-export only so the packaged source of truth remains ``layer4_agents``.
"""

from layer4_agents.tenants.api.routes.admin_dashboard import *  # noqa: F401,F403
from layer4_agents.tenants.api.routes.admin_dashboard import _authorize_tenant_access  # noqa: F401
