from layer2_extraction.extraction.signal_type_normalizer import (
    normalize_and_partition_signal_payloads,
    normalize_signal_type,
)


def _signal_payload(signal_type: str) -> dict[str, object]:
    return {"signal_type": signal_type, "source_text": "src", "confidence": 0.8, "metadata": {}}


def test_normalize_signal_type_returns_canonical_for_valid_and_legacy_labels() -> None:
    assert normalize_signal_type("pain") == "pain"
    assert normalize_signal_type(" Opportunity ") == "opportunity"
    assert normalize_signal_type("threat") == "risk"
    assert normalize_signal_type("issue") == "pain"
    assert normalize_signal_type("pattern") == "trend"


def test_normalize_and_partition_quarantines_unknown_labels() -> None:
    canonical, quarantined = normalize_and_partition_signal_payloads(
        [_signal_payload("pain"), _signal_payload("mystery")]
    )

    assert [s.signal_type for s in canonical] == ["pain"]
    assert len(quarantined) == 1
    assert quarantined[0].raw_label == "mystery"
    assert quarantined[0].reason == "unknown_signal_type"


def test_normalize_and_partition_supports_backward_compatibility_aliases() -> None:
    canonical, quarantined = normalize_and_partition_signal_payloads(
        [
            _signal_payload("issue"),
            _signal_payload("upside"),
            _signal_payload("warning"),
            _signal_payload("pattern"),
        ]
    )

    assert quarantined == []
    assert [s.signal_type for s in canonical] == ["pain", "opportunity", "risk", "trend"]
