"""B3b — the re-parameterization evaluator. Behavior tests per
specs/2026-07-10-reparameterization-evaluator-design.md §10.

Synthetic claims over REAL contract ids (the contracts' metadata is real; no real numerical re-test
is run — the gate is injected as a stub, per §8/§10, and the real MGMT->TMZ proof is B4-data-gated).
The reparam LLM is an untrusted proposer: it only narrows WHICH space to re-test; the injected gate
licenses. grammar/protocol already done (B3a); this slice is umbrella-side; Corpus stays 4.
"""
from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    ComputeGraph,
    DataHandle,
    EvaluationPlan,
    GenerationMode,
    MeasurementBasis,
    OperationNode,
    PatternRef,
    ProducedLeafSpec,
    Provenance,
    RejectionReason,
    RelationKind,
    SatisfactionCriterion,
    Status,
)

from polymer_claims.reparam_evaluator import (
    ReparamAgent,
    evaluate,
    refuted_claims,
    reissue_over_space,
)
from polymer_claims.measurement_space import get_space

_PATTERN = PatternRef(id="adjusted_effect", version="v1")


def _plan(ref: str) -> EvaluationPlan:
    node = OperationNode(
        id="n0", impl="builtin::const", inputs=(DataHandle(ref=ref),),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    return EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=0.05),
    )


def _refuted(cid="mgmt-tmz", ref="se:gdsc_pharmaco@1") -> Claim:
    return Claim(
        id=cid, title=f"{cid} refuted over gene-body", pattern=_PATTERN,
        leaves=(CategoricalLeaf(ontology_term=f"term-{cid}"),),
        status=Status.REJECTED, rejection_reason=RejectionReason.REFUTED,
        provenance=Provenance(
            generated_by=GenerationMode.AGENT_GENERATED, agent_id="test", search_cardinality=1,
            rationale="MGMT silencing is promoter-localized; gene-body average washes it out.",
        ),
        evaluation_plan=_plan(ref),
    )


def _agent(modalities):
    """A ReparamAgent whose injected LLM returns a canned modality proposal (untrusted -> validated)."""
    import json
    payload = json.dumps({"modalities": modalities})
    return ReparamAgent(complete=lambda _prompt: payload)


def _noop_retest(corpus, alternates):
    return corpus  # alternates stay PENDING; the mechanism is what's under test, not the outcome


# --- §10: trigger scoping ---------------------------------------------------------------------

def test_trigger_only_refuted():
    from polymer_grammar import FDRLedger
    from polymer_protocol import Corpus
    refuted = _refuted("r-refuted")
    rejected_other = _refuted("r-other")
    rejected_other = rejected_other.model_copy(
        update={"rejection_reason": RejectionReason.DEFEAT_GROUNDED_OUT}
    )
    pending = _refuted("r-pending").model_copy(
        update={"status": Status.PENDING, "rejection_reason": None,
                "pending_reason": __import__("polymer_grammar").PendingReason.UNTESTED}
    )
    corpus = Corpus(claims=(refuted, rejected_other, pending), fdr_ledger=FDRLedger(target_fdr=0.05))
    trig = refuted_claims(corpus)
    assert [c.id for c in trig] == ["r-refuted"]


# --- §10: grounded generation, no fabrication -------------------------------------------------

def test_grounds_promoter_alternate_and_emits_restriction_map():
    from polymer_grammar import FDRLedger
    from polymer_protocol import Corpus
    corpus = Corpus(claims=(_refuted(),), fdr_ledger=FDRLedger(target_fdr=0.05))
    res = evaluate(corpus, _agent(["methylation_promoter"]), retest=_noop_retest)
    assert res.n_triggered == 1
    assert res.n_alternates == 1
    ids = [c.id for c in res.corpus.claims]
    assert "mgmt-tmz" in ids  # ORIGINAL retained verbatim (residualism)
    orig = next(c for c in res.corpus.claims if c.id == "mgmt-tmz")
    assert orig.status == Status.REJECTED and orig.rejection_reason == RejectionReason.REFUTED
    # the alternate is over the promoter contract, PENDING, and round-trips
    alt = next(c for c in res.corpus.claims if c.id.startswith("mgmt-tmz::reparam::"))
    assert alt.status == Status.PENDING
    Claim.model_validate_json(alt.model_dump_json())  # consistent claim
    # a RESTRICTION_MAP relation links original -> alternate
    rel = next(c for c in res.corpus.claims if c.leaves[0].kind == "relation")
    assert rel.leaves[0].relation_kind is RelationKind.RESTRICTION_MAP
    assert orig.id in rel.subject.source_set and alt.id in rel.subject.target_set


def test_no_fabrication_when_modality_has_no_available_alternate():
    from polymer_grammar import FDRLedger
    from polymer_protocol import Corpus
    corpus = Corpus(claims=(_refuted(),), fdr_ledger=FDRLedger(target_fdr=0.05))
    # gene-body is the CURRENT space; its only space is excluded -> no alternate, no fabrication
    res = evaluate(corpus, _agent(["methylation_genebody"]), retest=_noop_retest)
    assert res.n_alternates == 0
    assert not any(c.id.startswith("mgmt-tmz::reparam::") for c in res.corpus.claims)


def test_untrusted_llm_output_revalidated():
    # a bogus modality string is dropped (not fabricated into a space)
    from polymer_grammar import FDRLedger
    from polymer_protocol import Corpus
    corpus = Corpus(claims=(_refuted(),), fdr_ledger=FDRLedger(target_fdr=0.05))
    res = evaluate(corpus, _agent(["not_a_real_modality", "methylation_promoter"]), retest=_noop_retest)
    assert res.n_alternates == 1  # the bogus one dropped, the valid promoter one grounded


# --- §10: declare-and-charge, non-adaptive ----------------------------------------------------

def test_declare_and_charge_all_slots_before_retest():
    from polymer_grammar import FDRLedger
    from polymer_protocol import Corpus
    corpus = Corpus(claims=(_refuted(),), fdr_ledger=FDRLedger(target_fdr=0.05))
    seen = {}

    def _retest(corpus_in, alternates):
        ledger_ids = {t.claim_id for t in corpus_in.fdr_ledger.tests}
        seen["all_pre_registered"] = all(a.id in ledger_ids for a in alternates)
        seen["k"] = len(alternates)
        return corpus_in

    res = evaluate(corpus, _agent(["methylation_promoter"]), retest=_retest)
    assert seen["all_pre_registered"] is True  # every alternate slot charged BEFORE testing
    assert seen["k"] == 1
    assert res.corpus.fdr_ledger.n_tests == 1  # one alternate slot charged


# --- §10: depth-1 -----------------------------------------------------------------------------

def test_depth_1_a_rejected_alternate_does_not_recurse():
    from polymer_grammar import FDRLedger
    from polymer_protocol import Corpus
    corpus = Corpus(claims=(_refuted(),), fdr_ledger=FDRLedger(target_fdr=0.05))

    def _retest_rejects(corpus_in, alternates):
        # simulate the alternate ALSO being refuted over the new space
        updated = []
        alt_ids = {a.id for a in alternates}
        for c in corpus_in.claims:
            if c.id in alt_ids:
                updated.append(c.model_copy(update={
                    "status": Status.REJECTED, "pending_reason": None,
                    "rejection_reason": RejectionReason.REFUTED,
                }))
            else:
                updated.append(c)
        return corpus_in.model_copy(update={"claims": tuple(updated)})

    res = evaluate(corpus, _agent(["methylation_promoter"]), retest=_retest_rejects)
    # exactly ONE alternate — the rejected alternate did NOT spawn a second-generation reparam
    assert res.n_alternates == 1
    assert sum(c.id.startswith("mgmt-tmz::reparam::") for c in res.corpus.claims) == 1


def test_evaluate_is_idempotent_no_duplicate_alternates():
    from polymer_grammar import FDRLedger
    from polymer_protocol import Corpus
    corpus = Corpus(claims=(_refuted(),), fdr_ledger=FDRLedger(target_fdr=0.05))
    res1 = evaluate(corpus, _agent(["methylation_promoter"]), retest=_noop_retest)
    # feed the result back in — the original is still REFUTED, but the alternate already exists
    res2 = evaluate(res1.corpus, _agent(["methylation_promoter"]), retest=_noop_retest)
    assert res2.n_alternates == 0
    Corpus.model_validate_json(res2.corpus.model_dump_json())  # unique-id invariant holds
    assert sum(c.id.startswith("mgmt-tmz::reparam::") for c in res2.corpus.claims) == 1


# --- reissue helper -----------------------------------------------------------------------------

def test_reissue_swaps_data_ref_and_resets_status():
    sp = get_space("gdsc_pharmaco_promoter@1::meth")
    alt = reissue_over_space(_refuted(), sp, new_id="alt-1")
    assert alt.id == "alt-1"
    assert alt.status == Status.PENDING and alt.rejection_reason is None
    ref = alt.evaluation_plan.graph.nodes[0].inputs[0].ref
    assert ref == "se:gdsc_pharmaco_promoter@1"  # data_ref swapped to the alternate contract
