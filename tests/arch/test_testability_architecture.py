"""Architecture tests enforcing testability contracts.

These tests ensure that the shared testability primitives maintain their
contracts and can be used as drop-in replacements for hard-coded time/ID calls.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Ensure shared module is importable
_services_path = str(REPO_ROOT / "services")
if _services_path not in sys.path:
    sys.path.insert(0, _services_path)


class TestClockProtocolCompliance:
    """Verify that the Clock protocol implementations satisfy the contract."""

    def test_system_clock_returns_tz_aware_datetime(self):
        from value_fabric.shared.testability import SystemClock

        clock = SystemClock()
        now = clock.now()
        assert now.tzinfo is not None, "SystemClock.now() must be tz-aware"

    def test_fixed_clock_returns_tz_aware_datetime(self):
        from value_fabric.shared.testability import FixedClock

        clock = FixedClock()
        now = clock.now()
        assert now.tzinfo is not None, "FixedClock.now() must be tz-aware"

    def test_fixed_clock_is_deterministic(self):
        from value_fabric.shared.testability import FixedClock

        clock = FixedClock()
        assert clock.now() == clock.now()
        assert clock.monotonic() == clock.monotonic()

    def test_fixed_clock_advance(self):
        from value_fabric.shared.testability import FixedClock

        clock = FixedClock()
        t0 = clock.monotonic()
        dt0 = clock.now()
        clock.advance(10.0)
        assert clock.monotonic() == t0 + 10.0
        assert (clock.now() - dt0).total_seconds() == 10.0

    def test_fixed_clock_rejects_negative_advance(self):
        from value_fabric.shared.testability import FixedClock

        clock = FixedClock()
        with pytest.raises(ValueError, match="negative"):
            clock.advance(-1.0)


class TestIDGeneratorCompliance:
    """Verify that the IDGenerator protocol implementations satisfy the contract."""

    def test_uuid_generator_returns_string(self):
        from value_fabric.shared.testability import UUIDGenerator

        gen = UUIDGenerator()
        result = gen.generate()
        assert isinstance(result, str)
        assert len(result) == 32  # hex UUID4

    def test_uuid_generator_is_unique(self):
        from value_fabric.shared.testability import UUIDGenerator

        gen = UUIDGenerator()
        ids = {gen.generate() for _ in range(100)}
        assert len(ids) == 100

    def test_sequential_generator_is_deterministic(self):
        from value_fabric.shared.testability import SequentialIDGenerator

        gen = SequentialIDGenerator(prefix="test")
        assert gen.generate() == "test-1"
        assert gen.generate() == "test-2"
        assert gen.generate() == "test-3"

    def test_sequential_generator_custom_start(self):
        from value_fabric.shared.testability import SequentialIDGenerator

        gen = SequentialIDGenerator(prefix="x", start=42)
        assert gen.generate() == "x-42"


class TestProtocolRuntimeCheckable:
    """Verify that protocols can be checked at runtime with isinstance()."""

    @pytest.mark.parametrize(
        ("impl_name", "protocol_name"),
        [
            ("SystemClock", "Clock"),
            ("FixedClock", "Clock"),
            ("UUIDGenerator", "IDGenerator"),
            ("SequentialIDGenerator", "IDGenerator"),
        ],
    )
    def test_implementations_satisfy_protocols(self, impl_name: str, protocol_name: str):
        from value_fabric.shared.testability import (
            Clock,
            FixedClock,
            IDGenerator,
            SequentialIDGenerator,
            SystemClock,
            UUIDGenerator,
        )

        impl_map = {
            "SystemClock": SystemClock,
            "FixedClock": FixedClock,
            "UUIDGenerator": UUIDGenerator,
            "SequentialIDGenerator": SequentialIDGenerator,
        }
        protocol_map = {"Clock": Clock, "IDGenerator": IDGenerator}
        impl_cls = impl_map[impl_name]
        protocol_cls = protocol_map[protocol_name]
        assert isinstance(impl_cls(), protocol_cls)


class TestSharedTestabilityExports:
    """Ensure the public API of shared.testability is stable."""

    def test_all_exports_importable(self):
        from value_fabric.shared.testability import (
            CacheBackendProtocol,
            Clock,
            FixedClock,
            HTTPClientProtocol,
            IDGenerator,
            SequentialIDGenerator,
            SystemClock,
            UUIDGenerator,
        )
        # If this doesn't raise, all symbols are importable
        assert Clock is not None
        assert SystemClock is not None
        assert FixedClock is not None
        assert IDGenerator is not None
        assert UUIDGenerator is not None
        assert SequentialIDGenerator is not None
        assert HTTPClientProtocol is not None
        assert CacheBackendProtocol is not None
