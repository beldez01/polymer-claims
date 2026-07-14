"""Accumulating-universe store (B2) — behavior tests per
specs/2026-07-10-accumulating-universe-store-design.md §7.

Umbrella-side; Corpus stays 4; grammar/protocol untouched. All on synthetic corpora — the store
primitive is exercised without the slow live pipeline. The injected register/license fn uses the
REAL fdr.register_test so the ledger-position assertions are against genuine e-LOND mechanics.
"""
from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    ComputeGraph,
    DataHandle,
    EvaluationPlan,
    LiteralSubject,
    MeasurementBasis,
    OperationNode,
    PatternRef,
    PendingReason,
    ProducedLeafSpec,
    SatisfactionCriterion,
    Status,
)
from polymer_grammar.fdr import register_test

from polymer_claims.accumulating_store import (
    AccumulatingStore,
    claim_modalities,
    content_address,
)
from polymer_claims.measurement_space import Modality

_PATTERN = PatternRef(id="adjusted_effect", version="v1")


def _plan(ref: str | None = None) -> EvaluationPlan:
    inputs = (DataHandle(ref=ref),) if ref is not None else ()
    node = OperationNode(
        id="n0", impl="builtin::const", inputs=inputs,
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    return EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=0.05),
    )


def _claim(cid, *, ref=None, subject=None, status=Status.PENDING) -> Claim:
    return Claim(
        id=cid, title=f"claim {cid}", pattern=_PATTERN,
        leaves=(CategoricalLeaf(ontology_term=f"term-{cid}"),),
        status=status,
        pending_reason=PendingReason.UNTESTED if status == Status.PENDING else None,
        subject=subject,
        evaluation_plan=_plan(ref),
    )


def _register_pending(corpus, claims):
    """Injected register/license: append claims + register a pending e-LOND slot each (real fdr)."""
    ledger = corpus.fdr_ledger
    for c in claims:
        ledger = register_test(ledger, c.id, content_address(c))
    return corpus.model_copy(update={"claims": corpus.claims + claims, "fdr_ledger": ledger})


# --- §7: dedup on re-run (the headline regression) --------------------------------------------

def test_rerun_against_populated_store_mints_zero(tmp_path):
    store = AccumulatingStore(tmp_path)
    claims = (_claim("c1"), _claim("c2"))
    r1 = store.accumulate(claims, _register_pending)
    assert (r1.n_new, r1.n_deduped) == (2, 0)
    r2 = store.accumulate(claims, _register_pending)  # identical panel, again
    assert (r2.n_new, r2.n_deduped) == (0, 2)
    assert len(store.load_corpus().claims) == 2  # NOT 4


def test_empty_store_mints_expected_count(tmp_path):
    store = AccumulatingStore(tmp_path)
    r = store.accumulate((_claim("x1"), _claim("x2"), _claim("x3")), _register_pending)
    assert r.n_new == 3


def test_within_batch_duplicate_ids_deduped(tmp_path):
    # Two proposed claims with the same id in one batch must not both register (would violate the
    # Corpus unique-id invariant on reload). First wins.
    store = AccumulatingStore(tmp_path)
    r = store.accumulate((_claim("dup"), _claim("dup"), _claim("solo")), _register_pending)
    assert r.n_new == 2
    reloaded = store.load_corpus()  # must round-trip without a unique-id ValidationError
    assert sorted(c.id for c in reloaded.claims) == ["dup", "solo"]


# --- §7: whole-Corpus round-trip preserves the live fdr_ledger position ------------------------

def test_roundtrip_preserves_fdr_ledger_and_appends_as_stream(tmp_path):
    store = AccumulatingStore(tmp_path)
    store.accumulate(tuple(_claim(f"c{i}") for i in range(3)), _register_pending)
    reloaded = store.load_corpus()
    assert reloaded.fdr_ledger.n_tests == 3
    assert [t.index for t in reloaded.fdr_ledger.tests] == [1, 2, 3]
    # second wave APPENDS — does not reset the ledger to position 0
    store.accumulate(tuple(_claim(f"d{i}") for i in range(2)), _register_pending)
    reloaded2 = store.load_corpus()
    assert reloaded2.fdr_ledger.n_tests == 5
    assert [t.index for t in reloaded2.fdr_ledger.tests] == [1, 2, 3, 4, 5]
    # the first wave's slots are byte-identical after the second wave (stream property)
    assert reloaded2.fdr_ledger.tests[:3] == reloaded.fdr_ledger.tests


# --- §7: append-only / no erasure --------------------------------------------------------------

def test_log_is_append_only_no_erasure(tmp_path):
    store = AccumulatingStore(tmp_path)
    store.accumulate((_claim("a1"),), _register_pending)
    ids_after_a = store.registered_ids()
    store.accumulate((_claim("b1"),), _register_pending)
    recs = store.log_records()
    assert len(recs) == 2
    assert {r.claim_id for r in recs} == {"a1", "b1"}
    assert ids_after_a <= store.registered_ids()  # nothing removed


def test_content_address_stable_for_reobserved_atom():
    assert content_address(_claim("z")) == content_address(_claim("z"))
    assert content_address(_claim("z")) != content_address(_claim("z", status=Status.CONJECTURED))


# --- §7: modality's two moments (realized modality derived from the contract via B1 registry) ---

def test_realized_modality_derived_from_data_ref():
    assert claim_modalities(_claim("m1", ref="se:tcga_laml_fusion_expr@1")) == (Modality.EXPRESSION_TPM,)
    multi = claim_modalities(_claim("m2", ref="se:gdsc_pharmaco@1"))
    assert set(multi) == {Modality.METHYLATION_GENEBODY, Modality.DRUG_RESPONSE_AUC}
    assert claim_modalities(_claim("m3")) == ()  # no plan ref -> no modality


# --- §7: facet census over (subject × modality × status), coverage gaps ------------------------

def test_census_reports_coverage_gap_and_current_status(tmp_path):
    s1 = LiteralSubject(id="s1", display="S1", prose="S1")
    s2 = LiteralSubject(id="s2", display="S2", prose="S2")
    store = AccumulatingStore(tmp_path)
    claims = (
        _claim("g1", ref="se:gdsc_pharmaco@1", subject=s1),                          # meth + auc
        _claim("e1", ref="se:tcga_laml_fusion_expr@1", subject=s1, status=Status.LICENSED),  # expr
        _claim("e2", ref="se:tcga_laml_fusion_expr@1", subject=s2),                   # expr
    )
    store.accumulate(claims, _register_pending)
    cen = store.census()
    sk1, sk2 = s1.model_dump_json(), s2.model_dump_json()
    # S2 has an expression claim but NO methylation-genebody claim -> a coverage gap
    assert (sk2, "methylation_genebody") in cen.coverage_gaps
    assert (sk1, "methylation_genebody") not in cen.coverage_gaps
    # census reflects CURRENT status (read from the corpus snapshot, not the log)
    assert cen.cells[(sk1, "expression_tpm")] == {"licensed": 1}
    assert cen.cells[(sk2, "expression_tpm")] == {"pending": 1}
