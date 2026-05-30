"""Unit tests for Layer 6 observability metrics contract."""

<<<<<<< HEAD
from layer6_benchmarks.observability.metrics_contract import (
=======
from value_fabric.layer6.observability.metrics_contract import (
>>>>>>> ab2ac2c2 (```)
    MetricSpec,
    load_metric_specs,
    metric_names,
    metric_spec_map,
)


def test_load_metric_specs_returns_tuple() -> None:
    specs = load_metric_specs()
    assert isinstance(specs, tuple)
    assert len(specs) > 0
    assert all(isinstance(s, MetricSpec) for s in specs)


def test_metric_spec_map_returns_dict_by_name() -> None:
    mapping = metric_spec_map()
    assert isinstance(mapping, dict)
    assert all(isinstance(v, MetricSpec) for v in mapping.values())
    # Names are unique.
    assert len(mapping) == len(load_metric_specs())


def test_metric_names_returns_set() -> None:
    names = metric_names()
    assert isinstance(names, set)
    assert len(names) > 0


def test_all_specs_have_required_fields() -> None:
    for spec in load_metric_specs():
        assert spec.name
        assert spec.metric_type
        assert isinstance(spec.required, bool)
        assert spec.description
        assert isinstance(spec.labels, tuple)
        assert isinstance(spec.max_cardinality, dict)


def test_load_metric_specs_is_cached() -> None:
    first = load_metric_specs()
    second = load_metric_specs()
    assert first is second


def test_metric_spec_max_cardinality_is_dict() -> None:
    for spec in load_metric_specs():
        assert isinstance(spec.max_cardinality, dict)
        for key, limit in spec.max_cardinality.items():
            assert isinstance(key, str)
            assert isinstance(limit, int)
            assert limit > 0
