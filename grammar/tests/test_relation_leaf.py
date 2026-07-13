"""RelationLeaf — cross-arm relation assertion (coherence/tension/restriction-map).

`kind` is the discriminator field shared by every Leaf variant (matches the sibling
leaves' `Literal["..."]` pattern); the relation-kind enum is therefore named
`relation_kind` to avoid colliding with the discriminator.
"""
import pytest
from pydantic import ValidationError

from polymer_grammar.leaf import RelationKind, RelationLeaf, Tier


def test_relation_leaf_ok():
    lf = RelationLeaf(tier=Tier.BIOLOGICAL, relation_kind=RelationKind.TENSION, severity=-0.4)
    assert lf.kind == "relation"
    assert lf.relation_kind == RelationKind.TENSION
    assert lf.severity == -0.4


def test_severity_bounds():
    with pytest.raises(ValidationError):
        RelationLeaf(tier=Tier.COMPUTATIONAL, relation_kind=RelationKind.COHERES, severity=1.5)
