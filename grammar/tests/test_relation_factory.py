from polymer_grammar.relation import make_relation_claim, is_relation
from polymer_grammar.leaf import RelationKind, Tier
from polymer_grammar.status import Status


def test_make_relation_claim():
    c = make_relation_claim(
        "rel-1", ["a"], ["b"], Tier.BIOLOGICAL, RelationKind.TENSION, -0.5,
        rationale="TP53 vs apoptosis",
    )
    assert c.status == Status.CONJECTURED
    assert c.subject.kind == "claim_set"
    assert c.leaves[0].kind == "relation"
    assert c.leaves[0].relation_kind == RelationKind.TENSION
    assert c.leaves[0].severity == -0.5
    assert c.evaluation_plan is None  # lane guard relies on this
    assert is_relation(c) is True


def test_ordinary_claim_is_not_relation():
    c = make_relation_claim(
        "rel-2", ["x"], ["y"], Tier.COMPUTATIONAL, RelationKind.COHERES, 0.7,
        rationale="same target, concordant nulls",
    )
    assert is_relation(c) and c.leaves[0].relation_kind == RelationKind.COHERES
