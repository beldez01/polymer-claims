"""B3a — a RESTRICTION_MAP relation suppresses sheaf frustration between the claims it bridges.

The re-parameterization "reinterpret" semantics: two claims over DIFFERENT measurement spaces are
non-comparable, so an equivalence/defeat edge between them is not a contradiction. Only
RESTRICTION_MAP suppresses (COHERES/TENSION do not); absent any such relation the sheaf is
byte-identical to prior behavior (covered by the unchanged 509-test protocol suite).
"""
from __future__ import annotations

from polymer_grammar import (
    DefeatEdge,
    DefeatEdgeKind,
    EquivalenceClaim,
    FDRLedger,
    RelationKind,
    Status,
    Tier,
    make_relation_claim,
)

from polymer_protocol.corpus import Corpus
from polymer_protocol.sheaf import extract_sheaf, frustration_obstructions


def _corpus(make_quantity_claim, *, relation_kind: RelationKind | None):
    # A and B: two commensurable quantity claims that a defeat + an equivalence together frustrate
    # (a 2-edge cycle with sign product -1).
    a = make_quantity_claim("A", 1.0, Status.LICENSED)
    b = make_quantity_claim("B", 2.0, Status.LICENSED)
    equiv = EquivalenceClaim(id="eqAB", left="A", right="B", severity=0.5, status=Status.LICENSED)
    defeat = DefeatEdge(source="A", target="B", kind=DefeatEdgeKind.REBUT)
    claims = [a, b]
    if relation_kind is not None:
        claims.append(
            make_relation_claim(
                "rel-AB", ["A"], ["B"], Tier.BIOLOGICAL, relation_kind, 0.9,
                rationale="A and B are measured over different spaces",
            )
        )
    return Corpus(
        claims=tuple(claims), equivalences=(equiv,), defeat_edges=(defeat,),
        fdr_ledger=FDRLedger(target_fdr=0.05),
    )


def test_defeat_plus_equiv_frustrate_without_a_restriction_map(make_quantity_claim):
    s = extract_sheaf(_corpus(make_quantity_claim, relation_kind=None), effective_only=False)
    assert len(s.edges) == 2  # both the equivalence (+1) and the defeat (-1) are present
    assert frustration_obstructions(s)  # -> frustrated (contradiction)


def test_restriction_map_suppresses_the_frustration(make_quantity_claim):
    s = extract_sheaf(
        _corpus(make_quantity_claim, relation_kind=RelationKind.RESTRICTION_MAP),
        effective_only=False,
    )
    assert s.edges == ()  # both edges dropped — A,B are non-comparable
    assert frustration_obstructions(s) == ()  # no contradiction


def test_coheres_relation_does_not_suppress(make_quantity_claim):
    # Only RESTRICTION_MAP carries the non-comparability semantics; COHERES must leave the edges.
    s = extract_sheaf(
        _corpus(make_quantity_claim, relation_kind=RelationKind.COHERES),
        effective_only=False,
    )
    assert len(s.edges) == 2
    assert frustration_obstructions(s)
