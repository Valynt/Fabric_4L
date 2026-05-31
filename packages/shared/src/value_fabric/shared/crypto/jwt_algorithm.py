"""RS256 enforcement for production JWT (P2-004)."""
from __future__ import annotations
import os
from enum import StrEnum

class JWTAlgorithm(StrEnum):
    RS256 = "RS256"
    HS256 = "HS256"

ALLOWED_ALGORITHMS = {
    "production": {JWTAlgorithm.RS256},
    "staging": {JWTAlgorithm.RS256, JWTAlgorithm.HS256},
    "development": {JWTAlgorithm.RS256, JWTAlgorithm.HS256},
}

def validate_algorithm(algorithm: str) -> JWTAlgorithm:
    algo = JWTAlgorithm(algorithm)
    env = os.environ.get("ENVIRONMENT", "development").lower()
    allowed = ALLOWED_ALGORITHMS.get(env, ALLOWED_ALGORITHMS["development"])
    if algo not in allowed:
        raise ValueError(f"JWT algorithm {algorithm} not allowed in {env}. Use RS256.")
    return algo
