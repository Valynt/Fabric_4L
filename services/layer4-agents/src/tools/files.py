"""Compatibility shim for the canonical Layer 4 module.

The implementation lives in ``layer4_agents.tools.files``. Keep this file as a thin
re-export only so the packaged source of truth remains ``layer4_agents``.
"""

from layer4_agents.tools.files import *  # noqa: F401,F403
from layer4_agents.tools.files import (  # noqa: F401
    TenantRequiredError,
    _get_tenant_id,
    _validate_path,
    delete_file,
    read_file,
    write_file,
)
