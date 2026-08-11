"""Guards for the V1-TENANCY-010 worker-plane fixes (#1258):

1. The L1 Celery worker tenant kill-switch is real (not a stub returning
   False): it consults the shared Redis suspended-tenant set and RAISES
   TenantKillSwitchUnavailable when the state cannot be determined —
   UNKNOWN is not ALLOW. Workers retry with backoff instead of processing
   tenant-owned work.
2. Durable idempotency: execute_target passes idempotency_key into
   create_scraping_job so the partial unique index
   idx_scraping_jobs_tenant_idempotency enforces dedup at the database
   boundary (Redis-only dedup loses entries on flush), with an
   IntegrityError path that returns the existing job.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.security, pytest.mark.p0, pytest.mark.tenant_boundary, pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
L1_TASKS = REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py"
L1_TARGET_HANDLERS = REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/api/target_handlers.py"


class TestKillSwitchWiring:
    def test_stub_removed_and_unavailable_raises(self) -> None:
        text = L1_TASKS.read_text(encoding="utf-8")
        assert "No kill-switch implementation yet" not in text, "stub must be gone"
        assert "class TenantKillSwitchUnavailable(RuntimeError)" in text
        assert "check_status_sync" in text
        assert 'getattr(kill_switch, "_redis", None)' not in text

    def test_both_call_sites_retry_on_unknown_state(self) -> None:
        text = L1_TASKS.read_text(encoding="utf-8")
        count = text.count("except TenantKillSwitchUnavailable as exc:")
        assert count == 2, f"both worker call sites must handle UNKNOWN, found {count}"
        assert text.count("self.retry(exc=exc, countdown=30)") >= 2, (
            "kill-switch call sites must retry on UNKNOWN (other retries pre-exist)"
        )

    def test_suspension_still_fails_closed(self) -> None:
        text = L1_TASKS.read_text(encoding="utf-8")
        assert text.count('"Tenant suspended"') >= 2, "confirmed suspension still fails the job"


class TestKillSwitchBehavior:
    """Behavioral proof via a fake Redis against the shared kill switch."""

    def _fake_redis(self, members: set[str] | None = None, fail: bool = False):
        class _FakeRedis:
            def __init__(self) -> None:
                self._members = members or set()

            def sismember(self, key: str, member: str) -> bool:
                if fail:
                    raise ConnectionError("redis down")
                return member in self._members

        return _FakeRedis()

    def test_suspended_tenant_detected(self) -> None:
        import sys

        sys.path.insert(0, str(REPO_ROOT / "packages" / "shared" / "src"))
        from value_fabric.shared.tenant_kill_switch import SUSPENDED_TENANTS_SET, TenantKillSwitch

        tenant = "11111111-1111-1111-1111-111111111111"
        redis = self._fake_redis(members={tenant})
        switch = TenantKillSwitch(redis)
        assert redis.sismember(SUSPENDED_TENANTS_SET, tenant) is True
        assert switch.check_status_sync(tenant).value == "suspended"

    def test_active_tenant_not_detected(self) -> None:
        import sys

        sys.path.insert(0, str(REPO_ROOT / "packages" / "shared" / "src"))
        from value_fabric.shared.tenant_kill_switch import SUSPENDED_TENANTS_SET, TenantKillSwitch

        redis = self._fake_redis()
        tenant = "22222222-2222-2222-2222-222222222222"
        assert redis.sismember(SUSPENDED_TENANTS_SET, tenant) is False
        assert TenantKillSwitch(redis).check_status_sync(tenant).value == "active"

    def test_unavailable_status_is_unknown(self) -> None:
        import sys

        sys.path.insert(0, str(REPO_ROOT / "packages" / "shared" / "src"))
        from value_fabric.shared.tenant_kill_switch import TenantKillSwitch

        tenant = "33333333-3333-3333-3333-333333333333"
        assert TenantKillSwitch(None).check_status_sync(tenant).value == "unknown"
        assert (
            TenantKillSwitch(self._fake_redis(fail=True))
            .check_status_sync(tenant)
            .value
            == "unknown"
        )


class TestDurableIdempotency:
    def test_idempotency_key_passed_to_job_factory(self) -> None:
        text = L1_TARGET_HANDLERS.read_text(encoding="utf-8")
        assert "idempotency_key=idempotency_key" in text, (
            "execute_target must populate the durable idempotency column"
        )

    def test_integrity_error_returns_existing_job(self) -> None:
        text = L1_TARGET_HANDLERS.read_text(encoding="utf-8")
        assert "except sqlalchemy.exc.IntegrityError:" in text
        assert "db.rollback()" in text
        assert "ScrapingJob.idempotency_key == idempotency_key" in text
        assert "return ExecuteTargetResponse(" in text
