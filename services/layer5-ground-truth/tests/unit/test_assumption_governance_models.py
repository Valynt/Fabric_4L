from layer5_ground_truth.models.assumption_governance import LifecycleState


def test_lifecycle_states_are_explicit_and_stable() -> None:
    assert {s.value for s in LifecycleState} == {
        "draft",
        "approved",
        "deprecated",
        "archived",
        "published",
    }
