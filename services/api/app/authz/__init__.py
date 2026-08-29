"""Fabric authorization control-plane foundation.

The public entry point is AuthorizationService (the fail-closed
facade). The package also exposes the versioned request/decision schemas,
deny/reason codes, and the decision-record persistence layer, which are the
stable contracts consumed by the policy-decision plane.
"""
from app.authz.constants import DenyCode, ReasonCode
from app.authz.decision import AuthorizationService
from app.authz.records import DecisionOutbox, DecisionRecordStore
from app.authz.schemas import (
    AuthzContext,
    AuthzDecision,
    AuthzRequest,
    Obligation,
    Principal,
    Resource,
)

__all__ = [
    "AuthorizationService",
    "AuthzContext",
    "AuthzDecision",
    "AuthzRequest",
    "DecisionOutbox",
    "DecisionRecordStore",
    "DenyCode",
    "Obligation",
    "Principal",
    "ReasonCode",
    "Resource",
]
