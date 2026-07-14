"""test_residue.py — the PENDING residue-graveyard query surface (residualism R2/R3).

Read-only query over a Corpus: the graveyard's shape (census), inspectable entries, facet filters,
and the R3 re-conversion worklist. No licensing, no gate — grammar + protocol DTOs only.
"""
from __future__ import annotations

from polymer_grammar import (
    DefeatEdge,
    DefeatEdgeKind,
    FDRLedger,
    PendingReason,
    Status,
)

from polymer_protocol.corpus import Corpus
from polymer_protocol.residue import (
    ResidueEntry,
    conversion_candidates,
    query_residue,
    reason_needs_external_input,
    residue_census,
    residue_graveyard,
)
from tests.conftest import make_claim, make_plan


def _corpus() -> Corpus:
    """A corpus mixing non-residue claims with four PENDING claims spanning the facets that decide
    re-conversion: testable+convertible, testable+high-leverage(duhem), testable-but-external-blocked,
    and not-testable."""
    plan = make_plan(0.01, 0.05)
    claims = (
        make_claim("lic", Status.LICENSED),
        make_claim("rej", Status.REJECTED),
        make_claim("p_untested", Status.PENDING, plan=plan, pending_reason=PendingReason.UNTESTED),
        make_claim("p_duhem", Status.PENDING, plan=plan, pending_reason=PendingReason.DUHEM_UNDERDETERMINED),
        make_claim("p_obsolete", Status.PENDING, plan=plan, pending_reason=PendingReason.ONTOLOGY_TERM_OBSOLETE),
        make_claim("p_noplan", Status.PENDING, pending_reason=PendingReason.CONTESTED),  # no plan
    )
    # p_duhem sits on two defeat edges (once as source, once as target) → dependents == 2.
    edges = (
        DefeatEdge(source="p_duhem", target="lic", kind=DefeatEdgeKind.REBUT),
        DefeatEdge(source="rej", target="p_duhem", kind=DefeatEdgeKind.UNDERMINE),
    )
    return Corpus(claims=claims, defeat_edges=edges, fdr_ledger=FDRLedger(target_fdr=0.05))


def test_census_is_the_graveyard_shape_pending_only():
    census = residue_census(_corpus())
    assert census == {
        PendingReason.UNTESTED: 1,
        PendingReason.DUHEM_UNDERDETERMINED: 1,
        PendingReason.ONTOLOGY_TERM_OBSOLETE: 1,
        PendingReason.CONTESTED: 1,
    }
    # LICENSED / REJECTED never enter the residue.
    assert sum(census.values()) == 4


def test_graveyard_entries_carry_the_conversion_facets_and_are_ordered():
    grave = residue_graveyard(_corpus())
    assert [e.claim_id for e in grave] == ["p_duhem", "p_noplan", "p_obsolete", "p_untested"]  # sorted by id
    by_id = {e.claim_id: e for e in grave}
    assert isinstance(by_id["p_untested"], ResidueEntry)
    assert by_id["p_untested"].testable and not by_id["p_untested"].needs_external_input
    assert by_id["p_noplan"].testable is False          # no evaluation_plan
    assert by_id["p_obsolete"].needs_external_input is True
    assert by_id["p_duhem"].dependents == 2             # incident defeat edges (source + target)
    assert by_id["p_untested"].dependents == 0


def test_query_filters_by_each_facet():
    corpus = _corpus()
    assert [e.claim_id for e in query_residue(corpus, reason=PendingReason.UNTESTED)] == ["p_untested"]
    assert [e.claim_id for e in query_residue(corpus, testable=False)] == ["p_noplan"]
    assert [e.claim_id for e in query_residue(corpus, needs_external_input=True)] == ["p_obsolete"]


def test_conversion_candidates_are_testable_convertible_ranked_by_leverage():
    cand = conversion_candidates(_corpus())
    ids = [e.claim_id for e in cand]
    # p_obsolete excluded (needs external input); p_noplan excluded (not testable).
    assert ids == ["p_duhem", "p_untested"]  # duhem first: dependents 2 > 0
    assert "p_obsolete" not in ids and "p_noplan" not in ids


def test_reason_convertibility_classification():
    assert reason_needs_external_input(PendingReason.ONTOLOGY_TERM_OBSOLETE) is True
    assert reason_needs_external_input(PendingReason.UNREPRODUCIBLE_BY_GOVERNANCE) is True
    assert reason_needs_external_input(PendingReason.UNTESTED) is False
    assert reason_needs_external_input(None) is False


def test_empty_corpus_has_no_residue():
    empty = Corpus(fdr_ledger=FDRLedger(target_fdr=0.05))
    assert residue_census(empty) == {}
    assert residue_graveyard(empty) == ()
    assert conversion_candidates(empty) == ()
