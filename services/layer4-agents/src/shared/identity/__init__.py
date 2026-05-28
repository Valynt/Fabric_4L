from __future__ import annotations

"""Identity and authentication shared components."""


from value_fabric.shared.identity.oidc import OIDCClient, map_role_from_claims
from value_fabric.shared.identity.oidc_config import OIDCProviderConfig

from .oidc_state import (
    InMemoryOIDCStateStore,
    OIDCStateStore,
    OIDCStateStoreProtocol,
    RedisOIDCStateStore,
    create_oidc_state_store,
)

__all__ = [
    "OIDCClient",
    "map_role_from_claims",
    "OIDCProviderConfig",
    "OIDCStateStore",
    "OIDCStateStoreProtocol",
    "RedisOIDCStateStore",
    "InMemoryOIDCStateStore",
    "create_oidc_state_store",
]
