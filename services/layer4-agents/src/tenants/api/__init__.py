"""Tenant governance API package."""

from __future__ import annotations

from .routes.admin import router as admin_router
from .routes.admin_console import router as admin_console_router
from .routes.api_keys import router as api_keys_router
from .routes.provisioning import router as provisioning_router
from .routes.registration import router as registration_router
from .routes.tenants import router as tenants_router
from .routes.users import router as users_router

__all__ = [
    "tenants_router",
    "users_router",
    "api_keys_router",
    "registration_router",
    "admin_router",
    "admin_console_router",
    "provisioning_router",
]
