"""Task 6: project relation claims into signed, all-pairs TopologyEdges.

A relation claim (RelationLeaf over a ClaimSetSubject) is not itself an edge in the
existing defeat/equivalence/entails sense — export_topology must additionally emit,
per relation claim: an all-pairs edge set between source_set x target_set carrying the
relation's signed weight, plus weak "coheres" localization edges from the relation
claim's own id to every relatum. A relation-free corpus must stay byte-identical
(CONTRACT_VERSION "1.0", no extra edges) — Task 5's TopologyEdge fields are additive
and unset by default.
"""
from __future__ import annotations

import pytest
from polymer_grammar import FDRLedger, RelationKind, Status, Tier, make_relation_claim

from polymer_protocol.corpus import Corpus
from polymer_protocol.topology import (
    CONTRACT_VERSION,
    CONTRACT_VERSION_RELATIONS,
    Layout,
    export_topology,
)

from .conftest import make_claim

_LEDGER = FDRLedger(target_fdr=0.05)


@pytest.fixture
def tiny_relation_corpus() -> Corpus:
    a = make_claim("a", status=Status.PENDING)
    b = make_claim("b", status=Status.PENDING)
    r = make_relation_claim(
        "r", ["a"], ["b"], Tier.BIOLOGICAL, RelationKind.TENSION, -0.6,
        rationale="x",
    )
    return Corpus(claims=(a, b, r), fdr_ledger=_LEDGER)


@pytest.fixture
def relation_free_corpus() -> Corpus:
    a = make_claim("a", status=Status.PENDING)
    b = make_claim("b", status=Status.PENDING)
    return Corpus(claims=(a, b), fdr_ledger=_LEDGER)


def test_tension_projects_negative_all_pairs(tiny_relation_corpus):
    topo = export_topology(tiny_relation_corpus, layout=Layout.NONE)
    rel = [e for e in topo.edges if e.kind == "tension"]
    assert rel and all(e.signed_weight < 0 for e in rel)
    assert {frozenset((e.source, e.target)) for e in rel} == {frozenset(("a", "b"))}


def test_tension_edge_carries_tier_and_status(tiny_relation_corpus):
    topo = export_topology(tiny_relation_corpus, layout=Layout.NONE)
    rel = next(e for e in topo.edges if e.kind == "tension")
    assert rel.tier == "biological"
    assert rel.relation_status == "conjectured"
    assert rel.provisional is True
    assert rel.effective is False
    # severity(-0.6) * status_factor(0.3, conjectured) / (1*1) = -0.18
    assert rel.signed_weight == pytest.approx(-0.18)


def test_localization_edges_from_relation_id_to_relata(tiny_relation_corpus):
    topo = export_topology(tiny_relation_corpus, layout=Layout.NONE)
    loc = [e for e in topo.edges if e.kind == "coheres" and e.source == "r"]
    assert {e.target for e in loc} == {"a", "b"}
    assert all(e.signed_weight == pytest.approx(0.1) for e in loc)
    assert all(e.provisional is True and e.effective is False for e in loc)


def test_relation_free_corpus_stays_on_v1(relation_free_corpus):
    topo = export_topology(relation_free_corpus, layout=Layout.NONE)
    assert topo.contract_version == CONTRACT_VERSION == "1.0"
    assert not any(e.kind == "tension" for e in topo.edges)


def test_relation_bearing_export_stamps_v1_1(tiny_relation_corpus):
    topo = export_topology(tiny_relation_corpus, layout=Layout.NONE)
    assert topo.contract_version == CONTRACT_VERSION_RELATIONS == "1.1"


@pytest.fixture
def multi_relation_corpus() -> Corpus:
    """A 2x2 relation: source_set={a, b}, target_set={c, d}."""
    a = make_claim("a", status=Status.PENDING)
    b = make_claim("b", status=Status.PENDING)
    c = make_claim("c", status=Status.PENDING)
    d = make_claim("d", status=Status.PENDING)
    r = make_relation_claim(
        "r2", ["a", "b"], ["c", "d"], Tier.COMPUTATIONAL, RelationKind.RESTRICTION_MAP, 0.8,
        rationale="multi",
    )
    return Corpus(claims=(a, b, c, d, r), fdr_ledger=_LEDGER)


def test_multi_element_all_pairs_projects_four_edges(multi_relation_corpus):
    topo = export_topology(multi_relation_corpus, layout=Layout.NONE)
    rel = [e for e in topo.edges if e.kind == "restriction_map"]
    # 2 (source_set) x 2 (target_set) = 4 all-pairs edges.
    assert len(rel) == 4
    assert {(e.source, e.target) for e in rel} == {
        ("a", "c"), ("a", "d"), ("b", "c"), ("b", "d"),
    }
    # CONJECTURED (the relation's default status) -> status_factor 0.3; n = |source_set|*|target_set| = 4.
    expected_weight = round(0.8 * 0.3 / 4, 6)
    assert all(e.signed_weight == pytest.approx(expected_weight) for e in rel)


def test_multi_element_localization_edges_from_relation_id_to_relata(multi_relation_corpus):
    topo = export_topology(multi_relation_corpus, layout=Layout.NONE)
    loc = [e for e in topo.edges if e.kind == "coheres" and e.source == "r2"]
    # |source_set| + |target_set| = 2 + 2 = 4 weak localization edges, one per relatum.
    assert len(loc) == 4
    assert {e.target for e in loc} == {"a", "b", "c", "d"}
    assert all(e.signed_weight == pytest.approx(0.1) for e in loc)
    assert all(e.provisional is True and e.effective is False for e in loc)


@pytest.fixture
def licensed_relation_corpus() -> Corpus:
    """A relation claim with a non-CONJECTURED status (LICENSED), so factor=1.0.

    `Claim._licensing_only_when_licensed` (grammar/src/polymer_grammar/claim.py) only
    forbids the `licensing` field on a NON-LICENSED claim; LICENSED itself does not
    require `licensing` to be set. So `make_relation_claim(..., status=Status.LICENSED)`
    constructs cleanly without needing a Licensing object.
    """
    a = make_claim("a", status=Status.PENDING)
    b = make_claim("b", status=Status.PENDING)
    r = make_relation_claim(
        "r3", ["a"], ["b"], Tier.BIOLOGICAL, RelationKind.TENSION, -0.6,
        rationale="licensed", status=Status.LICENSED,
    )
    return Corpus(claims=(a, b, r), fdr_ledger=_LEDGER)


def test_non_conjectured_status_uses_full_weight_factor(licensed_relation_corpus):
    topo = export_topology(licensed_relation_corpus, layout=Layout.NONE)
    rel = next(e for e in topo.edges if e.kind == "tension")
    # LICENSED (non-CONJECTURED) -> status_factor 1.0, not the 0.3 CONJECTURED attenuation.
    assert rel.signed_weight == pytest.approx(round(-0.6 * 1.0 / 1, 6))
    assert rel.relation_status == "licensed"
    assert rel.provisional is False
    assert topo.contract_version == "1.1"
