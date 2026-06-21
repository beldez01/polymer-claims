"""Tests for sheaf structure DTOs and vertex extraction (Task 1: pure, numpy-free)."""
from __future__ import annotations

from polymer_grammar import DefeatEdge, DefeatEdgeKind, FDRLedger, FDRTest, Status
from polymer_protocol.corpus import Corpus
from polymer_protocol.sheaf import SheafVertex, extract_sheaf

from .conftest import _make_quantity_claim as make_quantity_claim


def _corpus(*claims):
    return Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_only_quantity_claims_in_status_filter_become_vertices():
    q_lic = make_quantity_claim("q1", value=2.0, status=Status.LICENSED, dim=(("mass", 1),), unit=None)
    q_pend = make_quantity_claim("q2", value=5.0, status=Status.PENDING, dim=(("mass", 1),), unit=None)
    q_rej = make_quantity_claim("q3", value=9.0, status=Status.REJECTED, dim=(("mass", 1),), unit=None)
    struct = extract_sheaf(_corpus(q_lic, q_pend, q_rej))
    ids = {v.claim_id for v in struct.vertices}
    assert ids == {"q1", "q2"}  # REJECTED excluded by default filter
    assert SheafVertex(claim_id="q1", value=2.0, dimension_sig=(("mass", 1),), unit=None) in struct.vertices


def test_no_quantity_leaf_claims_excluded():
    """Claims without a QuantityLeaf (e.g. CategoricalLeaf) are excluded even if status passes."""
    from .conftest import make_claim

    cat_lic = make_claim("c1", status=Status.LICENSED)
    struct = extract_sheaf(_corpus(cat_lic))
    assert struct.vertices == ()


def test_custom_status_filter():
    """extract_sheaf respects a custom status_filter frozenset."""
    q_conj = make_quantity_claim("q1", value=1.0, status=Status.CONJECTURED, dim=(), unit=None)
    q_lic = make_quantity_claim("q2", value=2.0, status=Status.LICENSED, dim=(), unit=None)
    struct = extract_sheaf(_corpus(q_conj, q_lic), status_filter=frozenset({Status.CONJECTURED}))
    ids = {v.claim_id for v in struct.vertices}
    assert ids == {"q1"}


def test_no_dimension_claim():
    """Claims with dimension=None produce a vertex with dimension_sig=None."""
    q = make_quantity_claim("q1", value=3.0, status=Status.LICENSED, dim=None, unit=None)
    struct = extract_sheaf(_corpus(q))
    assert len(struct.vertices) == 1
    assert struct.vertices[0].dimension_sig is None


def test_empty_corpus():
    struct = extract_sheaf(_corpus())
    assert struct.vertices == ()
    assert struct.edges == ()
    assert struct.flags == ()


def test_equivalence_edge_weight_and_commensurability(make_quantity_claim, make_equiv, fdr):
    a = make_quantity_claim("a", value=1.0, status=Status.LICENSED, dim=(("mass", 1),), unit=None)
    b = make_quantity_claim("b", value=1.2, status=Status.LICENSED, dim=(("mass", 1),), unit=None)
    c = make_quantity_claim("c", value=3.0, status=Status.LICENSED, dim=(("time", 1),), unit=None)  # other dim
    from polymer_protocol.corpus import Corpus
    corpus = Corpus(
        claims=(a, b, c),
        equivalences=(make_equiv("e1", "a", "b", severity=0.8), make_equiv("e2", "a", "c", severity=0.9)),
        fdr_ledger=fdr,
    )
    struct = extract_sheaf(corpus)
    eq_edges = [e for e in struct.edges if e.kind == "equivalence"]
    assert len(eq_edges) == 1
    e = eq_edges[0]
    assert (e.u, e.v, e.weight, e.sign) == ("a", "b", 0.8, 1)            # canonical id order, severity weight
    assert any(f.kind == "dimension_mismatch" and set(f.claim_ids) == {"a", "c"} for f in struct.flags)


def test_unit_mismatch_flag_no_edge(make_quantity_claim, make_equiv, fdr):
    """Two claims with same dimension_sig but different unit → unit_mismatch flag, no edge."""
    a = make_quantity_claim("a", value=1.0, status=Status.LICENSED, dim=(("mass", 1),), unit="kg")
    b = make_quantity_claim("b", value=2.2, status=Status.LICENSED, dim=(("mass", 1),), unit="g")
    corpus = Corpus(
        claims=(a, b),
        equivalences=(make_equiv("e1", "a", "b", severity=0.5),),
        fdr_ledger=fdr,
    )
    struct = extract_sheaf(corpus)
    eq_edges = [e for e in struct.edges if e.kind == "equivalence"]
    assert len(eq_edges) == 0
    assert any(f.kind == "unit_mismatch" and set(f.claim_ids) == {"a", "b"} for f in struct.flags)


def test_effective_defeat_becomes_signed_edge_weighted_by_attacker_evalue(make_quantity_claim):
    atk = make_quantity_claim("atk", value=4.0, status=Status.LICENSED, dim=(("mass", 1),), unit=None)
    tgt = make_quantity_claim("tgt", value=4.0, status=Status.LICENSED, dim=(("mass", 1),), unit=None)
    ledger = FDRLedger(
        target_fdr=0.05,
        tests=(FDRTest(index=1, claim_id="atk", e_value=7.5, alpha_allocated=0.05, discovery=True),),
    )
    corpus = Corpus(
        claims=(atk, tgt),
        defeat_edges=(DefeatEdge(source="atk", target="tgt", kind=DefeatEdgeKind.REBUT),),
        fdr_ledger=ledger,
    )
    struct = extract_sheaf(corpus)
    d_edges = [e for e in struct.edges if e.kind == "defeat"]
    assert len(d_edges) == 1
    assert (d_edges[0].u, d_edges[0].v, d_edges[0].weight, d_edges[0].sign) == ("atk", "tgt", 7.5, -1)


def test_defeat_synthetic_source_skipped(make_quantity_claim):
    """A synthetic source id containing ':' is not in vmap → defeat edge silently skipped."""
    tgt = make_quantity_claim("tgt", value=4.0, status=Status.LICENSED, dim=(("mass", 1),), unit=None)
    ledger = FDRLedger(target_fdr=0.05)
    corpus = Corpus(
        claims=(tgt,),
        defeat_edges=(DefeatEdge(source="synthetic:123", target="tgt", kind=DefeatEdgeKind.REBUT),),
        fdr_ledger=ledger,
    )
    struct = extract_sheaf(corpus)
    d_edges = [e for e in struct.edges if e.kind == "defeat"]
    assert len(d_edges) == 0
