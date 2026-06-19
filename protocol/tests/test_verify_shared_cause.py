"""Tests for the VERIFY shared-cause gate (Phase D slice 2, Task 3).

The gate:
- Overlap between prior_cohorts and test-cohort dimnames_hash => CONFIRMATORY tier + severity cap.
- No overlap => HELD_OUT tier, no cap.
- strict_shared_cause=True + CONFIRMATORY => PENDING with SHARED_CAUSE_CONFIRMATORY.
- Empty prior_cohorts => byte-identical (severity_provenance stays None, strength untouched).
"""
from polymer_grammar import (
    GenerationMode,
    Provenance,
    SeverityProvenance,
    Status,
)
from polymer_protocol.verify import verify_stage

from tests.helpers_verify import (
    licensable_corpus,
    with_dimnames,
)


def _set_prior(corpus, claim_id, prior_cohorts):
    claims = tuple(
        c.model_copy(update={
            "provenance": (c.provenance or Provenance(
                generated_by=GenerationMode.LITERATURE_EXTRACTED, search_cardinality=1
            )).model_copy(update={"prior_cohorts": prior_cohorts})
        }) if c.id == claim_id else c
        for c in corpus.claims
    )
    return corpus.model_copy(update={"claims": claims})


def test_overlap_marks_confirmatory_and_caps_severity():
    corpus, scaff, recs = licensable_corpus()
    corpus, recs = with_dimnames(corpus, recs, "c1", "cohortX")
    corpus = _set_prior(corpus, "c1", ("cohortX",))  # prior overlaps the test cohort
    out = verify_stage(corpus, scaff, recs)
    c1 = out.by_id()["c1"]
    assert c1.status == Status.LICENSED
    assert c1.licensing.severity_provenance is SeverityProvenance.CONFIRMATORY
    assert c1.strength is not None and c1.strength.severity <= 0.2


def test_no_overlap_marks_held_out_no_cap():
    corpus, scaff, recs = licensable_corpus()
    corpus, recs = with_dimnames(corpus, recs, "c1", "cohortX")
    corpus = _set_prior(corpus, "c1", ("cohortY",))  # disjoint
    out = verify_stage(corpus, scaff, recs)
    c1 = out.by_id()["c1"]
    assert c1.status == Status.LICENSED
    assert c1.licensing.severity_provenance is SeverityProvenance.HELD_OUT


def test_strict_mode_withholds_confirmatory():
    from polymer_grammar import PendingReason
    corpus, scaff, recs = licensable_corpus()
    corpus, recs = with_dimnames(corpus, recs, "c1", "cohortX")
    corpus = _set_prior(corpus, "c1", ("cohortX",))
    out = verify_stage(corpus, scaff, recs, strict_shared_cause=True)
    c1 = out.by_id()["c1"]
    assert c1.status == Status.PENDING
    assert c1.pending_reason == PendingReason.SHARED_CAUSE_CONFIRMATORY


def test_no_prior_cohorts_is_byte_identical():
    corpus, scaff, recs = licensable_corpus()
    corpus, recs = with_dimnames(corpus, recs, "c1", "cohortX")
    out = verify_stage(corpus, scaff, recs)  # no prior_cohorts set
    c1 = out.by_id()["c1"]
    assert c1.status == Status.LICENSED
    assert c1.licensing.severity_provenance is None  # inert
