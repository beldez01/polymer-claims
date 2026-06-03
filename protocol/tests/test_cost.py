import pytest

from polymer_protocol.cost import CostModel, CostVector, CostWeights, aggregate_cost


def test_resolve_returns_listed_or_default():
    cv = CostVector(wall_latency=5.0)
    model = CostModel(costs=(("a", cv),), default=CostVector(wall_latency=1.0))
    assert model.resolve("a") == cv
    assert model.resolve("missing") == CostVector(wall_latency=1.0)


def test_aggregate_is_weighted_sum_floored():
    cv = CostVector(wall_latency=2.0, capital=3.0, human_hours=0.0,
                    failure_rate=0.0, oracle_queue_depth=0.0)
    w = CostWeights(wall_latency=1.0, capital=2.0)
    assert aggregate_cost(cv, w) == 2.0 * 1.0 + 3.0 * 2.0  # = 8.0


def test_aggregate_never_zero():
    # all-zero cost would divide by zero in value-density; floored instead
    assert aggregate_cost(CostVector(), CostWeights()) >= 1e-6


def test_cost_models_are_frozen():
    with pytest.raises(Exception):
        CostVector().wall_latency = 9.0
