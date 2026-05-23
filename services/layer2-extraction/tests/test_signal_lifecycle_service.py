from uuid import uuid4

import pytest

from layer2_extraction.models.signal_lifecycle import SignalLifecycleActor, SignalLifecycleStatus
from layer2_extraction.services.signal_lifecycle_service import InvalidLifecycleTransitionError, SignalLifecycleService


def _actor() -> SignalLifecycleActor:
    return SignalLifecycleActor(actor_id=str(uuid4()), account_id="acct-1")


def test_supersede_transition_and_lineage_traceability() -> None:
    svc = SignalLifecycleService()
    actor = _actor()
    old_signal = svc.create_signal("s-1", "tenant-1", actor)
    new_signal = svc.create_signal("s-2", "tenant-1", actor)

    updated = svc.supersede_signal(old_signal.signal_id, new_signal.signal_id, "tenant-1", actor)

    assert updated.status == SignalLifecycleStatus.SUPERSEDED
    assert updated.lineage.superseded_by == ["s-2"]
    assert svc.get_signal("s-2", "tenant-1", actor.account_id).lineage.supersedes == ["s-1"]


def test_invalid_transition_rejected_for_non_active_signal() -> None:
    svc = SignalLifecycleService()
    actor = _actor()
    svc.create_signal("s-1", "tenant-1", actor)
    svc.create_signal("s-2", "tenant-1", actor)
    svc.supersede_signal("s-1", "s-2", "tenant-1", actor)

    with pytest.raises(InvalidLifecycleTransitionError):
        svc.merge_signal("s-1", "s-2", "tenant-1", actor)


def test_merge_transition_lineage_traceability() -> None:
    svc = SignalLifecycleService()
    actor = _actor()
    svc.create_signal("s-1", "tenant-1", actor)
    svc.create_signal("s-2", "tenant-1", actor)

    merged = svc.merge_signal("s-1", "s-2", "tenant-1", actor)

    assert merged.status == SignalLifecycleStatus.MERGED
    assert merged.lineage.merged_into == "s-2"
    assert svc.get_signal("s-2", "tenant-1", actor.account_id).lineage.supersedes == ["s-1"]
