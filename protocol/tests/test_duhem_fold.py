from polymer_grammar import FDRLedger, PendingReason, Status
from polymer_protocol.sheaf import Obstruction
from polymer_protocol.corpus import Corpus
from polymer_protocol.duhem_fold import duhem_fold_from_obstructions

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
    corpus, audit = duhem_fold_from_obstructions(_corpus(a, b, c), [_obstruction("A", "B", "C")])
    by_id = corpus.by_id()
    for cid in ("A", "B", "C"):
        assert by_id[cid].status == Status.PENDING
        assert by_id[cid].pending_reason == PendingReason.DUHEM_UNDERDETERMINED
        assert by_id[cid].licensing is None
    assert set(audit.demoted) == {"A", "B", "C"}
    assert audit.reopened == ()


def test_never_sets_rejected():
    a = make_claim("A", status=Status.LICENSED)
    corpus, _ = duhem_fold_from_obstructions(_corpus(a, make_claim("B", status=Status.LICENSED)),
                                             [_obstruction("A", "B")])
    assert all(c.status != Status.REJECTED for c in corpus.claims)


def test_resolved_cycle_reopens_pending_duhem_to_reinstated():
    # a claim already PENDING duhem from a prior cycle, no longer implicated → reopen
    stuck = make_claim("A", status=Status.PENDING, pending_reason=PendingReason.DUHEM_UNDERDETERMINED)
    corpus, audit = duhem_fold_from_obstructions(_corpus(stuck), [])   # no obstructions now
    assert corpus.by_id()["A"].status == Status.PENDING
    assert corpus.by_id()["A"].pending_reason == PendingReason.REINSTATED
    assert set(audit.reopened) == {"A"}


def test_unimplicated_and_unrelated_claims_untouched():
    lic = make_claim("A", status=Status.LICENSED)                       # licensed, not implicated
    other = make_claim("B", status=Status.PENDING, pending_reason=PendingReason.UNTESTED)
    corpus, audit = duhem_fold_from_obstructions(_corpus(lic, other), [])
    assert corpus.by_id()["A"].status == Status.LICENSED
    assert corpus.by_id()["B"].pending_reason == PendingReason.UNTESTED
    assert audit.demoted == () and audit.reopened == ()


def test_ledger_is_untouched():
    a = make_claim("A", status=Status.LICENSED)
    corpus_in = _corpus(a, make_claim("B", status=Status.LICENSED))
    corpus_out, _ = duhem_fold_from_obstructions(corpus_in, [_obstruction("A", "B")])
    assert corpus_out.fdr_ledger == corpus_in.fdr_ledger   # warrant-only ⇒ no refund
