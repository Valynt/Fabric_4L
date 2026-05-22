"""Shared startup guards for service entrypoints."""

from .validator import reject_insecure_bypass_in_production

__all__ = ["reject_insecure_bypass_in_production"]
