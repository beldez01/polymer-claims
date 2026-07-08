from polymer_grammar import DefeatEdge, DefeatEdgeKind, EquivalenceClaim, FDRLedger, PendingReason, Status
from polymer_protocol.sheaf import Obstruction, extract_sheaf, frustration_obstructions
from polymer_protocol.corpus import Corpus
from polymer_protocol.duhem_fold import apply_duhem_consistency, duhem_fold

from tests.conftest import _make_quantity_claim as make_quantity_claim
from tests.conftest import make_claim


def _obstruction(*ids):
    edges = tuple((ids[i], ids[(i + 1) % len(ids)]) for i in range(len(ids)))
    return Obstruction(claim_ids=tuple(ids), edges=edges, magnitude=1.0)


def _corpus(*claims):
    return Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_licensed_claim_in_frustrated_cycle_demotes_to_pending_duhem():
    a = make_claim("A", status=Status.LICENSED)
    b = make_claim("B", status=Status.LICENSED)
    c = make_claim("C", status=Status.LICENSED)
    obs = _obstruction("A", "B", "C")
    corpus, audit = duhem_fold(_corpus(a, b, c), frozenset({"A", "B", "C"}), frozenset({"A", "B", "C"}), [obs])
    by_id = corpus.by_id()
    for cid in ("A", "B", "C"):
        assert by_id[cid].status == Status.PENDING
        assert by_id[cid].pending_reason == PendingReason.DUHEM_UNDERDETERMINED
        assert by_id[cid].licensing is None
    assert set(audit.demoted) == {"A", "B", "C"}
    assert audit.reopened == ()


def test_never_sets_rejected():
    a = make_claim("A", status=Status.LICENSED)
    obs = _obstruction("A", "B")
    corpus, _ = duhem_fold(_corpus(a, make_claim("B", status=Status.LICENSED)),
                            frozenset({"A", "B"}), frozenset({"A", "B"}), [obs])
    assert all(c.status != Status.REJECTED for c in corpus.claims)


def test_resolved_cycle_reopens_pending_duhem_to_reinstated():
    # a claim already PENDING duhem from a prior cycle, no longer implicated → reopen
    stuck = make_claim("A", status=Status.PENDING, pending_reason=PendingReason.DUHEM_UNDERDETERMINED)
    corpus, audit = duhem_fold(_corpus(stuck), frozenset(), frozenset(), [])   # structural empty ⇒ reopen fires
    assert corpus.by_id()["A"].status == Status.PENDING
    assert corpus.by_id()["A"].pending_reason == PendingReason.REINSTATED
    assert set(audit.reopened) == {"A"}


def test_pending_duhem_stays_put_while_structurally_implicated():
    stuck = make_claim("A", status=Status.PENDING, pending_reason=PendingReason.DUHEM_UNDERDETERMINED)
    corpus, audit = duhem_fold(_corpus(stuck), frozenset(), frozenset({"A", "B"}), [])
    # effective empty (no demote), but A still in a STRUCTURAL cycle → NOT reopened
    assert corpus.by_id()["A"].pending_reason == PendingReason.DUHEM_UNDERDETERMINED
    assert audit.reopened == ()


def test_unimplicated_and_unrelated_claims_untouched():
    lic = make_claim("A", status=Status.LICENSED)                       # licensed, not implicated
    other = make_claim("B", status=Status.PENDING, pending_reason=PendingReason.UNTESTED)
    corpus, audit = duhem_fold(_corpus(lic, other), frozenset(), frozenset(), [])
    assert corpus.by_id()["A"].status == Status.LICENSED
    assert corpus.by_id()["B"].pending_reason == PendingReason.UNTESTED
    assert audit.demoted == () and audit.reopened == ()


def test_ledger_is_untouched():
    a = make_claim("A", status=Status.LICENSED)
    corpus_in = _corpus(a, make_claim("B", status=Status.LICENSED))
    obs = _obstruction("A", "B")
    corpus_out, _ = duhem_fold(corpus_in, frozenset({"A", "B"}), frozenset({"A", "B"}), [obs])
    assert corpus_out.fdr_ledger == corpus_in.fdr_ledger   # warrant-only ⇒ no refund


def _make_frustrated_corpus() -> Corpus:
    """Three LICENSED Quantity-leaf claims A,B,C, commensurable (same dimension, no unit ⇒
    DERIVED basis), related by two equivalence edges (A≡B, B≡C, sign +1) and one defeat edge
    (C⊣A, sign -1). Mirrors test_sheaf.py's equivalence/defeat constructions
    (test_equivalence_edge_weight_and_commensurability, test_effective_defeat_becomes_signed_edge...).
    Odd number (one) of sign -1 edges around the A-B-C triangle ⇒ extract_sheaf renders a
    frustrated cycle (BFS labeling contradiction, no local witness)."""
    dim = (("mass", 1),)
    a = make_quantity_claim("A", value=1.0, status=Status.LICENSED, dim=dim, unit=None)
    b = make_quantity_claim("B", value=1.0, status=Status.LICENSED, dim=dim, unit=None)
    c = make_quantity_claim("C", value=1.0, status=Status.LICENSED, dim=dim, unit=None)
    equivalences = (
        EquivalenceClaim(id="e1", left="A", right="B", severity=0.9, status=Status.LICENSED),
        EquivalenceClaim(id="e2", left="B", right="C", severity=0.9, status=Status.LICENSED),
    )
    defeat_edges = (DefeatEdge(source="C", target="A", kind=DefeatEdgeKind.REBUT),)
    return Corpus(
        claims=(a, b, c),
        equivalences=equivalences,
        defeat_edges=defeat_edges,
        fdr_ledger=FDRLedger(target_fdr=0.05),
    )


def test_apply_duhem_consistency_demotes_on_a_real_frustrated_corpus():
    frustrated_corpus = _make_frustrated_corpus()
    # Non-vacuous: the corpus really does frustrate before we ever call the fold.
    obstructions = frustration_obstructions(extract_sheaf(frustrated_corpus))
    assert obstructions != ()
    assert set(obstructions[0].claim_ids) == {"A", "B", "C"}

    corpus, audit = apply_duhem_consistency(frustrated_corpus)
    by_id = corpus.by_id()
    assert set(audit.demoted) == {"A", "B", "C"}
    for cid in ("A", "B", "C"):
        assert by_id[cid].status == Status.PENDING
        assert by_id[cid].pending_reason == PendingReason.DUHEM_UNDERDETERMINED
    assert corpus.fdr_ledger == frustrated_corpus.fdr_ledger   # still ledger-neutral end-to-end
    assert audit.contradiction_ids == ("h1:A|B|C",)


def test_structural_sheaf_ignores_support_edges_no_phantom_frustration():
    """A support (EVIDENCE_FOR) edge closing an equivalence triangle must NOT read as
    antagonism (sign=-1) in the STRUCTURAL sheaf — regression guard for the Critical bug
    where the structural branch dropped the ATTACK_KINDS filter, so `evidence_for` edges
    manufactured phantom frustration and PENDING-duhem claims could never reopen."""
    dim = (("mass", 1),)
    a = make_quantity_claim("A", value=1.0, status=Status.PENDING, dim=dim, unit=None)
    b = make_quantity_claim("B", value=1.0, status=Status.PENDING, dim=dim, unit=None)
    c = make_quantity_claim("C", value=1.0, status=Status.PENDING, dim=dim, unit=None)
    equivalences = (
        EquivalenceClaim(id="e1", left="A", right="B", severity=0.9, status=Status.LICENSED),
        EquivalenceClaim(id="e2", left="B", right="C", severity=0.9, status=Status.LICENSED),
    )
    defeat_edges = (DefeatEdge(source="C", target="A", kind=DefeatEdgeKind.EVIDENCE_FOR),)
    corpus = Corpus(
        claims=(a, b, c),
        equivalences=equivalences,
        defeat_edges=defeat_edges,
        fdr_ledger=FDRLedger(target_fdr=0.05),
    )
    structure = extract_sheaf(corpus, effective_only=False)
    assert frustration_obstructions(structure) == ()


def _theta_corpus() -> Corpus:
    """The §7.7 theta witness: a,b,p2,p3 LICENSED Quantity-leaf claims (same dimension, no unit
    ⇒ DERIVED basis), joined by THREE independent paths between a and b — direct (a≡b), via p2
    (a≡p2, p2≡b), and via p3 (a≡p3, p3⊣b REBUT) — forming a single biconnected (theta) block.
    The a-b-p3 triangle is sign-unbalanced (one -1 defeat edge); the a-b-p2 triangle is balanced
    on its own. `frustration_obstructions`' spanning-tree BFS lands on the a-b-p3 fundamental
    cycle and never visits p2's fundamental-cycle edge, so its reported union misses p2 — but the
    whole block (all 4 vertices) is frustrated, which `frustrated_vertices` correctly reports."""
    dim = (("mass", 1),)
    a = make_quantity_claim("a", value=1.0, status=Status.LICENSED, dim=dim, unit=None)
    b = make_quantity_claim("b", value=1.0, status=Status.LICENSED, dim=dim, unit=None)
    p2 = make_quantity_claim("p2", value=1.0, status=Status.LICENSED, dim=dim, unit=None)
    p3 = make_quantity_claim("p3", value=1.0, status=Status.LICENSED, dim=dim, unit=None)
    equivalences = (
        EquivalenceClaim(id="e1", left="a", right="b", severity=0.9, status=Status.LICENSED),
        EquivalenceClaim(id="e2", left="a", right="p2", severity=0.9, status=Status.LICENSED),
        EquivalenceClaim(id="e3", left="p2", right="b", severity=0.9, status=Status.LICENSED),
        EquivalenceClaim(id="e4", left="a", right="p3", severity=0.9, status=Status.LICENSED),
    )
    defeat_edges = (DefeatEdge(source="p3", target="b", kind=DefeatEdgeKind.REBUT),)
    return Corpus(
        claims=(a, b, p2, p3),
        equivalences=equivalences,
        defeat_edges=defeat_edges,
        fdr_ledger=FDRLedger(target_fdr=0.05),
    )


def test_theta_demotes_the_vertex_obstructions_would_miss():
    corpus = _theta_corpus()   # a,b,p2,p3 LICENSED; a≡b, a≡p2, p2≡b, a≡p3, p3⊣b(REBUT)
    eff = extract_sheaf(corpus)
    assert len(eff.edges) == 5, "the REBUT defeat must survive the effective filter (attacker licensed)"
    reported = frozenset().union(*(frozenset(o.claim_ids) for o in frustration_obstructions(eff)))
    assert "p2" not in reported                       # obstruction-union would miss p2
    out, audit = apply_duhem_consistency(corpus)
    assert "p2" in audit.demoted                       # frustrated_vertices catches it
    assert out.by_id()["p2"].pending_reason == PendingReason.DUHEM_UNDERDETERMINED


def _triangle_corpus() -> Corpus:
    """§7.8 STATE 1: a simple frustrated triangle {a,p2,p3} — a≡p2, a≡p3, p2⊣p3(REBUT). Mirrors
    `_make_frustrated_corpus` (A-B-C) with the odd (one) sign-flip that makes the triangle
    unbalanced, relabeled to the p2/p3 ids used by the theta witness."""
    dim = (("mass", 1),)
    a = make_quantity_claim("a", value=1.0, status=Status.LICENSED, dim=dim, unit=None)
    p2 = make_quantity_claim("p2", value=1.0, status=Status.LICENSED, dim=dim, unit=None)
    p3 = make_quantity_claim("p3", value=1.0, status=Status.LICENSED, dim=dim, unit=None)
    equivalences = (
        EquivalenceClaim(id="e1", left="a", right="p2", severity=0.9, status=Status.LICENSED),
        EquivalenceClaim(id="e2", left="a", right="p3", severity=0.9, status=Status.LICENSED),
    )
    defeat_edges = (DefeatEdge(source="p2", target="p3", kind=DefeatEdgeKind.REBUT),)
    return Corpus(
        claims=(a, p2, p3),
        equivalences=equivalences,
        defeat_edges=defeat_edges,
        fdr_ledger=FDRLedger(target_fdr=0.05),
    )


def _theta_corpus_with_pending_p2() -> Corpus:
    """§7.8 STATE 2: the theta witness carrying p2 as an already-PENDING duhem_underdetermined
    claim (as if a prior fold cycle had suspended it) — a,b,p3 LICENSED, p2 PENDING duhem.
    Relative to STATE 1's triangle, the p2⊣p3 edge is REMOVED and b + a≡b, p2≡b, p3⊣b(REBUT)
    are ADDED, reproducing the exact _theta_corpus edge set with p2's status swapped to PENDING."""
    dim = (("mass", 1),)
    a = make_quantity_claim("a", value=1.0, status=Status.LICENSED, dim=dim, unit=None)
    b = make_quantity_claim("b", value=1.0, status=Status.LICENSED, dim=dim, unit=None)
    p2 = make_quantity_claim(
        "p2", value=1.0, status=Status.PENDING, dim=dim, unit=None,
        pending_reason=PendingReason.DUHEM_UNDERDETERMINED,
    )
    p3 = make_quantity_claim("p3", value=1.0, status=Status.LICENSED, dim=dim, unit=None)
    equivalences = (
        EquivalenceClaim(id="e1", left="a", right="b", severity=0.9, status=Status.LICENSED),
        EquivalenceClaim(id="e2", left="a", right="p2", severity=0.9, status=Status.LICENSED),
        EquivalenceClaim(id="e3", left="p2", right="b", severity=0.9, status=Status.LICENSED),
        EquivalenceClaim(id="e4", left="a", right="p3", severity=0.9, status=Status.LICENSED),
    )
    defeat_edges = (DefeatEdge(source="p3", target="b", kind=DefeatEdgeKind.REBUT),)
    return Corpus(
        claims=(a, b, p2, p3),
        equivalences=equivalences,
        defeat_edges=defeat_edges,
        fdr_ledger=FDRLedger(target_fdr=0.05),
    )


def test_reopen_does_not_fire_while_structurally_frustrated_but_fires_when_resolved():
    # STATE 1 — simple frustrated triangle {a,p2,p3}: a≡p2, a≡p3, p2⊣p3(REBUT) → p2 demotes
    state1 = _triangle_corpus()                        # a,p2,p3 LICENSED
    s1, a1 = apply_duhem_consistency(state1)
    assert "p2" in a1.demoted
    assert s1.by_id()["p2"].pending_reason == PendingReason.DUHEM_UNDERDETERMINED

    # STATE 2 — the theta witness, carrying p2 as PENDING-duhem; p2⊣p3 removed, b + 3 edges added
    state2 = _theta_corpus_with_pending_p2()           # a,b,p3 LICENSED; p2 PENDING duhem; a≡b,a≡p2,p2≡b,a≡p3,p3⊣b
    reported = frozenset().union(*(frozenset(o.claim_ids)
                                   for o in frustration_obstructions(extract_sheaf(state2, effective_only=False))))
    assert "p2" not in reported                        # reported structural obstructions miss p2 ...
    s2, a2 = apply_duhem_consistency(state2)
    assert "p2" not in a2.reopened                     # ... but frustrated_vertices keeps it suspended
    assert s2.by_id()["p2"].pending_reason == PendingReason.DUHEM_UNDERDETERMINED

    # COMPLEMENT — remove the p3⊣b defeat → p2 on no structural frustrated cycle → reopens
    resolved = state2.model_copy(update={"defeat_edges": ()})
    s3, a3 = apply_duhem_consistency(resolved)
    assert "p2" in a3.reopened
    assert s3.by_id()["p2"].pending_reason == PendingReason.REINSTATED
