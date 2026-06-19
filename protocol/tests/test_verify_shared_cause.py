"""Tests for the VERIFY shared-cause gate (Phase D slice 2, Task 3).

The gate:
- Overlap between prior_cohorts and test-cohort dimnames_hash => CONFIRMATORY tier + severity cap.
- No overlap => HELD_OUT tier, no cap.
- strict_shared_cause=True + CONFIRMATORY => PENDING with SHARED_CAUSE_CONFIRMATORY.
- Empty prior_cohorts => byte-identical (severity_provenance stays None, strength untouched).
- MDL-gate route must also carry severity_provenance + capped strength (Fix 1).
"""
from polymer_grammar import (
    FDRLedger,
    GenerationMode,
    LicenseRoute,
    PatternRef,
    PatternTarget,
    Provenance,
    RepresentationRevision,
    RevisionOperation,
    SeverityProvenance,
    Status,
    StrengthVector,
)
from polymer_protocol.commit import commit
from polymer_protocol.corpus import Corpus, CycleScaffolding
from polymer_protocol.execute import execute_ground
from polymer_protocol.verify import verify_stage

from tests.conftest import make_claim, make_plan
from tests.helpers_verify import (
    licensable_corpus,
    with_dimnames,
)

_PAT_A = PatternRef(id="patA", version="v1")
_PAT_B = PatternRef(id="patB", version="v1")
_ADAPTERS_2 = None  # resolved lazily (avoids module-level import side-effects)


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


# ---------------------------------------------------------------------------
# Fix 1: MDL-gate route must honor shared-cause annotation + severity cap
# ---------------------------------------------------------------------------


def _redundant_object_claims():
    """Object claims split across two redundant identical-signature patterns A, B."""
    objs = [make_claim(f"a{i}", status=Status.PENDING, pattern=_PAT_A) for i in range(4)]
    objs += [make_claim(f"b{i}", status=Status.PENDING, pattern=_PAT_B) for i in range(4)]
    return objs


def test_mdl_route_carries_shared_cause_annotation_and_cap():
    """Regression: MDL-gate branch must stamp severity_provenance + cap strength.

    A representation-revision claim whose prior_cohorts overlaps its test dimnames_hash should
    license as CONFIRMATORY (annotated) with severity <= 0.2 — even when the MDL_GATE route
    fires. Before Fix 1 the MDL branch built a fresh mdl_licensing without severity_provenance
    and licensed with the uncapped _recorded_strength, silently violating the honesty contract.
    """
    from polymer_grammar import IdentityAdapter, MaterializationContext, ReferenceAdapter

    adapters = (IdentityAdapter(), ReferenceAdapter(identity="reference"))
    ctx = MaterializationContext(id="M1", api_version="v1", data_version="d1")
    empty_ledger = FDRLedger(target_fdr=0.05)

    # High-severity strength so the cap test is meaningful.
    strength = StrengthVector(
        magnitude=0.8, certainty=0.8, evidence_against_null=0.9,
        severity=0.9, world_contact=0.8, explanatory_virtue=0.8,
    )
    merge_rev = RepresentationRevision(
        operation=RevisionOperation.MERGE,
        target=PatternTarget(patterns=(_PAT_A, _PAT_B)),
        rationale="A and B are redundant duplicates",
    )
    rev_claim = make_claim(
        "rev",
        status=Status.PENDING,
        plan=make_plan(0.01, 0.05),
        representation_revision=merge_rev,
        strength=strength,
    )
    corpus = Corpus(claims=(*_redundant_object_claims(), rev_claim), fdr_ledger=empty_ledger)
    corpus = commit(corpus)
    corpus, records = execute_ground(corpus, adapters, ctx)

    # Stamp the test-cohort dimnames_hash onto the revision exec record.
    test_cohort = "cohortMDL"
    new_records = []
    for rec in records:
        if rec.claim_id != "rev":
            new_records.append(rec)
            continue
        ev = rec.evaluation
        if ev.satisfaction is None:
            new_records.append(rec)
            continue
        from polymer_grammar import Satisfaction, SatisfactionVerdict
        new_mat = ev.satisfaction.materialization.model_copy(
            update={"dimnames_hash": test_cohort}
        )
        new_sat = Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=new_mat)
        new_ev = ev.model_copy(update={"satisfaction": new_sat})
        new_records.append(type(rec)(claim_id=rec.claim_id, evaluation=new_ev))
    records = tuple(new_records)

    # Set prior_cohorts to overlap the test cohort => CONFIRMATORY.
    claims = tuple(
        c.model_copy(update={
            "provenance": c.provenance.model_copy(update={"prior_cohorts": (test_cohort,)})
        }) if c.id == "rev" else c
        for c in corpus.claims
    )
    corpus = corpus.model_copy(update={"claims": claims})

    scaffolding = CycleScaffolding(grounded_extension=tuple(c.id for c in corpus.claims))
    out = verify_stage(corpus, scaffolding, records)

    rev = out.by_id()["rev"]
    assert rev.status == Status.LICENSED
    assert rev.licensing is not None
    assert rev.licensing.route == LicenseRoute.MDL_GATE
    # MDL route must carry the shared-cause annotation (Fix 1: was missing)
    assert rev.licensing.severity_provenance is SeverityProvenance.CONFIRMATORY
    # MDL route must use the capped strength (Fix 1: was using uncapped _recorded_strength)
    assert rev.strength is not None and rev.strength.severity <= 0.2
