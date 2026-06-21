"""Tests for sheaf structure DTOs and vertex extraction (Task 1: pure, numpy-free)."""
from __future__ import annotations

from polymer_grammar import FDRLedger, Status
from polymer_protocol.corpus import Corpus
from polymer_protocol.sheaf import SheafVertex, extract_sheaf

from .conftest import make_quantity_claim


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
    assert struct.edges == ()
    assert struct.flags == ()


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
