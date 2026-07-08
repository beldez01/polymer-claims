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
