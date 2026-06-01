import pytest

from polymer_grammar.proposition import (
    Direction,
    NeighborEdge,
    NeighborEdgeKind,
    Proposition,
)


def _prop(**kw):
    base = dict(direction=Direction.NEGATIVE, estimand="adjusted_effect_size",
                descriptor="curvature disfavors crossover after GC control")
    base.update(kw)
    return Proposition(**base)


def test_proposition_builds_with_typed_content():
    p = _prop()
    assert p.direction == Direction.NEGATIVE
    assert p.estimand == "adjusted_effect_size"
    assert p.neighborhood == ()


def test_content_hash_is_stable_and_independent_of_neighborhood():
    bare = _prop()
    with_nbr = _prop(neighborhood=(
        NeighborEdge(kind=NeighborEdgeKind.INCOMPATIBLE_WITH, target="deadbeef"),
    ))
    assert bare.content_hash == with_nbr.content_hash
    assert _prop().content_hash == _prop().content_hash


def test_content_hash_changes_with_each_content_field():
    base = _prop()
    assert base.content_hash != _prop(direction=Direction.POSITIVE).content_hash
    assert base.content_hash != _prop(estimand="other_estimand").content_hash
    assert base.content_hash != _prop(descriptor="a different conclusion").content_hash


def test_neighborhood_hash_is_sensitive_to_label():
    labeled = _prop(neighborhood=(
        NeighborEdge(kind=NeighborEdgeKind.ENTAILS, target="t", label="foo"),
    ))
    unlabeled = _prop(neighborhood=(
        NeighborEdge(kind=NeighborEdgeKind.ENTAILS, target="t"),
    ))
    assert labeled.neighborhood_hash != unlabeled.neighborhood_hash


def test_neighborhood_hash_is_order_independent_and_sensitive_to_edges():
    e1 = NeighborEdge(kind=NeighborEdgeKind.ENTAILS, target="aaa")
    e2 = NeighborEdge(kind=NeighborEdgeKind.INCOMPATIBLE_WITH, target="bbb")
    a = _prop(neighborhood=(e1, e2))
    b = _prop(neighborhood=(e2, e1))
    assert a.neighborhood_hash == b.neighborhood_hash
    assert a.neighborhood_hash != _prop().neighborhood_hash


def test_proposition_is_hashable_and_neighborhood_immutable():
    p = _prop(neighborhood=(NeighborEdge(kind=NeighborEdgeKind.ENTAILS, target="x"),))
    assert isinstance(hash(p), int)
    assert isinstance(p.neighborhood, tuple)
    with pytest.raises(AttributeError):
        p.neighborhood.append(NeighborEdge(kind=NeighborEdgeKind.ENTAILS, target="y"))
