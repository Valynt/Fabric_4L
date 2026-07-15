# Layer 4 Settings Cohesion Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve cohesion of `services/layer4-agents/src/layer4_agents/config/settings.py` by removing dead code and grouping related behavior into focused mixins, while preserving the existing Pydantic `BaseSettings` env-loading contract and public API.

**Architecture:** Keep `Settings` as the single public Pydantic `BaseSettings` class (env vars, validators, and field access must remain unchanged). Extract behavior-only mixins for billing and runtime/environment concerns. Delete the unused `database_url_safe` property instead of extracting it. This addresses the static analyzer's cohesion concern without the breaking env-var and caller changes that would come from splitting fields across multiple `BaseSettings` classes.

**Tech Stack:** Python 3.11+, Pydantic v2, pydantic-settings, pytest, ruff, mypy.

## Global Constraints

- Preserve behavior exactly — no public API shift, no env var name changes, no caller migrations.
- All field definitions and validators that read env vars stay in the single `Settings(BaseSettings)` class.
- `get_settings()` must continue to return the same cached `Settings` instance with the same attribute surface.
- `settings` proxy (`_SettingsProxy`) must continue to forward all attribute access.
- Tests instantiating `Settings(**values)` directly must continue to work unchanged.
- Run `make verify` before claiming completion; suite must stay green.

---

## File Structure

- **Modify:** `services/layer4-agents/src/layer4_agents/config/settings.py:67-657`
  - Remove dead `database_url_safe` property.
  - Introduce `BillingSettingsMixin` and `RuntimeSettingsMixin`.
  - Update `Settings` inheritance to include mixins.
- **Test:** `services/layer4-agents/tests/test_security_fixes.py`
  - Confirms `is_production` and `cors_origins_list` still work.
- **Test:** `services/layer4-agents/tests/test_analysis_routes.py`, `services/layer4-agents/tests/test_analysis_smoke_mode_service_routes.py`
  - Confirm `settings` proxy still forwards attributes.
- **Test:** `services/layer4-agents/src/layer4_agents/api/routers.py`
  - Confirms `get_settings().is_billing_configured` still works.

---

## Task 1: Remove dead `database_url_safe` property

**Files:**
- Modify: `services/layer4-agents/src/layer4_agents/config/settings.py:645-657`
- Test: existing resilience/database tests (no direct test exists because the property is unused)

**Interfaces:**
- Consumes: `Settings.database_url` field
- Produces: removal of unused method; no public surface change

- [ ] **Step 1: Delete the dead property**

Remove lines 645-657 from `settings.py`:

```python
    @property
    def database_url_safe(self) -> str:
        """Get database URL with password masked for logging."""
        url = self.database_url
        # Simple masking - replace password with ***
        if "://" in url:
            parts = url.split("@")
            if len(parts) == 2:
                auth_part = parts[0].split(":")
                if len(auth_part) >= 3:
                    # postgresql://user:pass@host -> postgresql://user:***@host
                    return f"{auth_part[0]}:***@{parts[1]}"
        return url
```

- [ ] **Step 2: Verify no callers break**

Run:

```bash
grep -R "database_url_safe" services/layer4-agents/
```

Expected: no matches outside the deleted definition.

- [ ] **Step 3: Commit**

```bash
git add services/layer4-agents/src/layer4_agents/config/settings.py
git commit -m "refactor(l4): remove unused database_url_safe property

No callers existed. Deleting it reduces surface area before cohesion work.

Co-authored-by: Ona <no-reply@ona.com>"
```

---

## Task 2: Extract billing behavior into `BillingSettingsMixin`

**Files:**
- Create: `services/layer4-agents/src/layer4_agents/config/_billing_mixin.py`
- Modify: `services/layer4-agents/src/layer4_agents/config/settings.py`
- Test: `services/layer4-agents/src/layer4_agents/api/routers.py` (runtime caller), `services/layer4-agents/tests/test_security_fixes.py`

**Interfaces:**
- Consumes: `self.billing_enabled: bool`, `self.stripe_secret_key: str | None`
- Produces: `is_billing_configured() -> bool` property (same name, same semantics)

- [ ] **Step 1: Create the billing mixin**

Create `services/layer4-agents/src/layer4_agents/config/_billing_mixin.py`:

```python
"""Billing-related behavior for Layer 4 Settings.

This mixin contains only computed properties and helper methods that depend on
billing fields defined on the concrete Settings class. Fields remain on
Settings so env-var loading and validation stay centralized.
"""
from __future__ import annotations

from typing import Protocol


class _BillingSettingsProtocol(Protocol):
    billing_enabled: bool
    stripe_secret_key: str | None


class BillingSettingsMixin:
    """Mixin exposing billing configuration helpers."""

    @property
    def is_billing_configured(self: _BillingSettingsProtocol) -> bool:
        """Check if Stripe billing is properly configured."""
        return self.billing_enabled and self.stripe_secret_key is not None
```

- [ ] **Step 2: Update Settings to use the mixin**

In `services/layer4-agents/src/layer4_agents/config/settings.py`:

1. Add import near the top (after pydantic imports):

```python
from ._billing_mixin import BillingSettingsMixin
```

2. Change class declaration:

```python
class Settings(BillingSettingsMixin, BaseSettings):
```

3. Remove the inline `is_billing_configured` property from `Settings`.

- [ ] **Step 3: Add a regression test for the mixin contract**

Create or append to `services/layer4-agents/tests/unit/test_settings_mixins.py`:

```python
"""Regression tests for Settings mixin behavior."""

import pytest

from layer4_agents.config.settings import Settings


class TestBillingSettingsMixin:
    def test_is_billing_configured_when_enabled_and_secret_present(self):
        settings = Settings(
            environment="development",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
            billing_enabled=True,
            stripe_secret_key="sk_test_xxx",
        )
        assert settings.is_billing_configured is True

    def test_is_billing_configured_false_when_disabled(self):
        settings = Settings(
            environment="development",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
            billing_enabled=False,
            stripe_secret_key="sk_test_xxx",
        )
        assert settings.is_billing_configured is False

    def test_is_billing_configured_false_when_secret_missing(self):
        settings = Settings(
            environment="development",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
            billing_enabled=True,
            stripe_secret_key=None,
        )
        assert settings.is_billing_configured is False
```

- [ ] **Step 4: Run focused tests**

```bash
pytest services/layer4-agents/tests/unit/test_settings_mixins.py services/layer4-agents/tests/test_security_fixes.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add services/layer4-agents/src/layer4_agents/config/_billing_mixin.py \
  services/layer4-agents/src/layer4_agents/config/settings.py \
  services/layer4-agents/tests/unit/test_settings_mixins.py
git commit -m "refactor(l4): extract billing behavior into BillingSettingsMixin

Keep billing fields and env loading on Settings; move is_billing_configured
into a focused mixin to improve cohesion.

Co-authored-by: Ona <no-reply@ona.com>"
```

---

## Task 3: Extract runtime/environment behavior into `RuntimeSettingsMixin`

**Files:**
- Create: `services/layer4-agents/src/layer4_agents/config/_runtime_mixin.py`
- Modify: `services/layer4-agents/src/layer4_agents/config/settings.py`
- Test: `services/layer4-agents/tests/test_security_fixes.py`, `services/layer4-agents/tests/test_analysis_routes.py`

**Interfaces:**
- Consumes: `self.environment: str`, `self.cors_origins: str`, `self.neo4j_uri: str`, `self.neo4j_password: str | None`, `self.oidc_state_store_backend: str`
- Produces: `is_production -> bool`, `is_development -> bool`, `cors_origins_list -> list[str]`

- [ ] **Step 1: Create the runtime mixin**

Create `services/layer4-agents/src/layer4_agents/config/_runtime_mixin.py`:

```python
"""Runtime/environment-related behavior for Layer 4 Settings.

This mixin contains computed properties and environment helpers that depend on
runtime fields defined on the concrete Settings class. Fields remain on
Settings so env-var loading and validation stay centralized.
"""
from __future__ import annotations

from typing import Protocol


class _RuntimeSettingsProtocol(Protocol):
    environment: str
    cors_origins: str


class RuntimeSettingsMixin:
    """Mixin exposing runtime and environment helpers."""

    @property
    def is_production(self: _RuntimeSettingsProtocol) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self: _RuntimeSettingsProtocol) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def cors_origins_list(self: _RuntimeSettingsProtocol) -> list[str]:
        """Get CORS origins as a list.

        Returns explicit origins when configured. Falls back to wildcard only
        in development; all other environments return an empty list (the
        validator above will have already raised for production).
        """
        if not self.cors_origins:
            return ["*"] if self.is_development else []
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        # Wildcard is only permitted in development.
        if "*" in origins and not self.is_development:
            raise ValueError(
                "CORS_ORIGINS cannot contain '*' outside of development. "
                "Specify exact allowed origins."
            )
        return origins
```

- [ ] **Step 2: Update Settings to use the mixin**

In `services/layer4-agents/src/layer4_agents/config/settings.py`:

1. Add import:

```python
from ._runtime_mixin import RuntimeSettingsMixin
```

2. Change class declaration:

```python
class Settings(BillingSettingsMixin, RuntimeSettingsMixin, BaseSettings):
```

3. Remove the inline `is_production`, `is_development`, and `cors_origins_list` properties from `Settings`.

- [ ] **Step 3: Extend regression tests**

Append to `services/layer4-agents/tests/unit/test_settings_mixins.py`:

```python
class TestRuntimeSettingsMixin:
    def test_is_production(self):
        settings = Settings(
            environment="production",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
            cors_origins="https://app.example.com",
        )
        assert settings.is_production is True
        assert settings.is_development is False

    def test_is_development(self):
        settings = Settings(
            environment="development",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
        )
        assert settings.is_development is True
        assert settings.is_production is False

    def test_cors_origins_list_returns_wildcard_in_development(self):
        settings = Settings(
            environment="development",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
        )
        assert settings.cors_origins_list == ["*"]

    def test_cors_origins_list_parses_explicit_origins(self):
        settings = Settings(
            environment="production",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
            cors_origins="https://a.example.com,https://b.example.com",
        )
        assert settings.cors_origins_list == [
            "https://a.example.com",
            "https://b.example.com",
        ]

    def test_cors_origins_list_rejects_wildcard_outside_development(self):
        settings = Settings(
            environment="production",
            jwt_secret="x" * 32,
            api_key_hmac_secret="x" * 32,
            cors_origins="*",
        )
        with pytest.raises(ValueError, match="cannot contain '\\*' outside of development"):
            settings.cors_origins_list
```

- [ ] **Step 4: Run focused tests**

```bash
pytest services/layer4-agents/tests/unit/test_settings_mixins.py services/layer4-agents/tests/test_security_fixes.py services/layer4-agents/tests/test_analysis_routes.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add services/layer4-agents/src/layer4_agents/config/_runtime_mixin.py \
  services/layer4-agents/src/layer4_agents/config/settings.py \
  services/layer4-agents/tests/unit/test_settings_mixins.py
git commit -m "refactor(l4): extract runtime behavior into RuntimeSettingsMixin

Move is_production, is_development, and cors_origins_list into a focused
mixin while keeping env loading and validators on Settings.

Co-authored-by: Ona <no-reply@ona.com>"
```

---

## Task 4: Preserve `validate_prod_neo4j_aura` location

**Files:**
- Modify: none (keep validator on `Settings`)

**Interfaces:**
- Consumes: `self.neo4j_uri`, `self.neo4j_password`, `self.environment`, `self.oidc_state_store_backend`
- Produces: unchanged cross-field validation

- [ ] **Step 1: Leave the model validator on Settings**

`validate_prod_neo4j_aura` is a cross-cutting model validator that depends on both Neo4j fields and runtime/OIDC fields. Moving it to either a billing or runtime mixin would create a misleading dependency. Leave it on `Settings`.

- [ ] **Step 2: Add a code comment explaining the decision**

Add a short comment above `validate_prod_neo4j_aura` in `settings.py`:

```python
    @model_validator(mode="after")
    def validate_prod_neo4j_aura(self) -> Settings:
        """Production/staging must use managed Aura, not in-cluster Neo4j.

        Kept on Settings because it depends on both runtime (environment,
        oidc_state_store_backend) and Neo4j (neo4j_uri, neo4j_password) fields.
        """
```

- [ ] **Step 3: Commit**

```bash
git add services/layer4-agents/src/layer4_agents/config/settings.py
git commit -m "docs(l4): document why validate_prod_neo4j_aura stays on Settings

The validator is cross-cutting; moving it would create misleading cohesion.

Co-authored-by: Ona <no-reply@ona.com>"
```

---

## Task 5: Run full Layer 4 validation

**Files:**
- All of `services/layer4-agents/`

- [ ] **Step 1: Run lint and type-check for Layer 4**

```bash
make lint-layer4
make typecheck-layer4
```

Expected: both pass with no new issues.

- [ ] **Step 2: Run Layer 4 tests**

```bash
make test-layer4
```

Expected: all tests pass.

- [ ] **Step 3: Run repository-wide verify gate**

```bash
make verify
```

Expected: exit 0, all gates green.

- [ ] **Step 4: Commit (if any fixes were needed)**

If lint/typecheck required small fixes, commit them with a clear message. If no fixes were needed, no additional commit.

---

## Self-Review Checklist

1. **Spec coverage:**
   - [ ] Dead `database_url_safe` removed.
   - [ ] Billing behavior extracted to `BillingSettingsMixin`.
   - [ ] Runtime/environment behavior extracted to `RuntimeSettingsMixin`.
   - [ ] `Settings` remains the single public Pydantic `BaseSettings` class.
   - [ ] `get_settings()` and `settings` proxy behavior unchanged.
   - [ ] No env var names or caller code changed.

2. **Placeholder scan:**
   - [ ] No "TBD", "TODO", or "implement later" strings.
   - [ ] Every step includes exact file paths, commands, and expected output.
   - [ ] Test code is complete, not "write tests for the above".

3. **Type consistency:**
   - [ ] `is_billing_configured` returns `bool` in both mixin and original.
   - [ ] `is_production`/`is_development` return `bool`.
   - [ ] `cors_origins_list` returns `list[str]` and raises `ValueError` on wildcard outside development.

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-11-extract-layer4-settings-cohesion.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using `executing-plans`, batch execution with checkpoints.

**Which approach?**
