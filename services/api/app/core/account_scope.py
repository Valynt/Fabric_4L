from fastapi import HTTPException

from app.core.security import TokenPayload


def derive_account_scope(auth: TokenPayload) -> set[str]:
    """Derive account scope from verified AuthContext claims.

    Accepts both ``account_id`` and ``account_ids`` claims to support
    compatibility during rollout.
    """
    scope: set[str] = set(auth.account_ids)
    if auth.account_id:
        scope.add(auth.account_id)
    return scope


def require_account_scope(*, auth: TokenPayload, account_id: str, route: str) -> None:
    """Fail closed when account scope claims are missing or do not include account_id."""
    scope = derive_account_scope(auth)
    if not scope:
        raise HTTPException(status_code=403, detail=f"Account scope missing for route {route}")
    if "*" not in scope and account_id not in scope:
        raise HTTPException(status_code=403, detail="Account access denied")
