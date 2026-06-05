"""Tests for export_topology — the pure corpus → TopologyExport data contract."""
from __future__ import annotations

import pytest
from polymer_grammar import (
    DefeatEdge,
    DefeatEdgeKind,
    Direction,
    EquivalenceClaim,
    GenomicRegion,
    NeighborEdge,
    NeighborEdgeKind,
    Proposition,
    RepresentationRevision,
    RevisionOperation,
    Status,
    StrengthVector,
)

from polymer_protocol.corpus import Corpus
from polymer_protocol.topology import (
    Layout,
    export_topology,
)

from .conftest import make_claim

_STRENGTH = StrengthVector(
    magnitude=0.8,
    certainty=0.7,
    evidence_against_null=0.6,
    severity=0.5,
    world_contact=0.4,
    explanatory_virtue=0.3,
)


def _region() -> GenomicRegion:
    return GenomicRegion(
        id="GR1",
        display="chr1:1-100",
        assembly="GRCh38",
        chrom="chr1",
        start=1,
        end=100,
    )


@pytest.fixture
def small_corpus(empty_ledger) -> Corpus:
    """Two claims (a LICENSED w/ subject+strength, b CONJECTURED) + a provisional rebut edge
    from an unlicensed source d -> b, and an equivalence a~b."""
    a = make_claim(
        "a",
        Status.LICENSED,
        strength=_STRENGTH,
        subject=_region(),
    )
    b = make_claim("b", Status.CONJECTURED)
    d = make_claim("d", Status.CONJECTURED)
    return Corpus(
        claims=(a, b, d),
        defeat_edges=(
            DefeatEdge(source="d", target="b", kind=DefeatEdgeKind.REBUT, provisional=True),
        ),
        equivalences=(
            EquivalenceClaim(
                id="eq1", left="a", right="b", severity=0.5, status=Status.LICENSED
            ),
        ),
        fdr_ledger=empty_ledger,
    )


def test_nodes_carry_claim_attributes(small_corpus):
    exp = export_topology(small_corpus, layout=Layout.NONE)
    n = {x.id: x for x in exp.nodes}
    assert n["a"].status == "licensed"
    assert n["a"].pattern_id == "adjusted_effect"
    assert n["a"].subject_kind == "genomic_region"
    assert n["a"].strength is not None and len(n["a"].strength) == 6
    assert n["a"].strength[0] == pytest.approx(0.8)
    assert n["b"].subject_kind is None
    assert n["b"].strength is None
    assert n["b"].is_representation_revision is False
    # NONE layout -> all positions at origin
    assert all(node.position == (0.0, 0.0, 0.0) for node in exp.nodes)


def test_nodes_sorted_by_id(small_corpus):
    exp = export_topology(small_corpus, layout=Layout.NONE)
    assert [n.id for n in exp.nodes] == ["a", "b", "d"]


def test_defeat_edge_effective_and_provisional_flags(small_corpus):
    exp = export_topology(small_corpus, layout=Layout.NONE)
    e = next(x for x in exp.edges if x.kind == "rebut")
    # source d is CONJECTURED (unlicensed) -> provisional edge inert -> not effective
    assert e.provisional is True
    assert e.effective is False
    assert e.source == "d" and e.target == "b"


def test_equivalence_edge_present(small_corpus):
    exp = export_topology(small_corpus, layout=Layout.NONE)
    e = next(x for x in exp.edges if x.kind == "equivalence")
    assert e.effective is True
    assert e.provisional is False
    assert {e.source, e.target} == {"a", "b"}


def test_provisional_edge_effective_when_source_licensed(empty_ledger):
    a = make_claim("a", Status.CONJECTURED)
    d = make_claim("d", Status.LICENSED)
    corpus = Corpus(
        claims=(a, d),
        defeat_edges=(
            DefeatEdge(source="d", target="a", kind=DefeatEdgeKind.REBUT, provisional=True),
        ),
        fdr_ledger=empty_ledger,
    )
    exp = export_topology(corpus, layout=Layout.NONE)
    e = next(x for x in exp.edges if x.kind == "rebut")
    assert e.provisional is True
    assert e.effective is True


def test_entails_edges_resolved_to_claim_ids(empty_ledger):
    target_prop = Proposition(direction=Direction.POSITIVE, estimand="E", descriptor="D-target")
    src_prop = Proposition(
        direction=Direction.POSITIVE,
        estimand="E",
        descriptor="D-source",
        neighborhood=(
            NeighborEdge(kind=NeighborEdgeKind.ENTAILS, target=target_prop.content_hash),
            # unresolved entails -> skipped
            NeighborEdge(kind=NeighborEdgeKind.ENTAILS, target="deadbeef"),
        ),
    )
    a = make_claim("a", Status.LICENSED, conclusion=src_prop)
    b = make_claim("b", Status.LICENSED, conclusion=target_prop)
    corpus = Corpus(claims=(a, b), fdr_ledger=empty_ledger)
    exp = export_topology(corpus, layout=Layout.NONE)
    entails = [e for e in exp.edges if e.kind == "entails"]
    assert len(entails) == 1
    assert entails[0].source == "a" and entails[0].target == "b"
    assert entails[0].effective is True and entails[0].provisional is False


def test_clusters_one_per_pattern(empty_ledger):
    from polymer_grammar import PatternRef

    other = PatternRef(id="other_pattern", version="v1")
    a = make_claim("a")
    b = make_claim("b")
    c = make_claim("c", pattern=other)
    corpus = Corpus(claims=(a, b, c), fdr_ledger=empty_ledger)
    exp = export_topology(corpus, layout=Layout.NONE)
    cl = {x.id: x for x in exp.clusters}
    assert set(cl) == {"pattern:adjusted_effect", "pattern:other_pattern"}
    assert cl["pattern:adjusted_effect"].label == "pattern:adjusted_effect"
    assert cl["pattern:adjusted_effect"].member_ids == ("a", "b")
    assert cl["pattern:other_pattern"].member_ids == ("c",)
    # clusters sorted by id
    assert [x.id for x in exp.clusters] == sorted(x.id for x in exp.clusters)


def test_representation_revision_flag(empty_ledger):
    rev = RepresentationRevision(
        operation=RevisionOperation.ADD,
        target={"kind": "ontology_term", "term_id": "HP:0000001"},
        rationale="needed for new assay",
    )
    a = make_claim("a", representation_revision=rev)
    corpus = Corpus(claims=(a,), fdr_ledger=empty_ledger)
    exp = export_topology(corpus, layout=Layout.NONE)
    assert exp.nodes[0].is_representation_revision is True


def test_layout_none_id(small_corpus):
    exp = export_topology(small_corpus, layout=Layout.NONE)
    assert exp.layout_id == "none"
