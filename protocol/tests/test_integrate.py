from polymer_grammar import Status

from polymer_protocol.corpus import Corpus, CycleScaffolding
from polymer_protocol.integrate import integrate
from tests.conftest import make_claim, make_plan
from polymer_grammar import (
    DefeatEdge, DefeatEdgeKind, FDRLedger, FDRTest, LicenseRoute, Licensing,
    MaterializationContext, PendingReason, RejectionReason, RivalSetClosure,
    Satisfaction, SatisfactionVerdict,
    Direction, NeighborEdge, NeighborEdgeKind, Proposition, StrengthVector,
)


def _exec_record_with_value(claim_id, value, ctx, adapters, empty_ledger):
    """Helper: produce a real ExecRecord by executing a const-`value` plan."""
    from polymer_protocol.commit import commit
    from polymer_protocol.execute import execute_ground

    c = make_claim(claim_id, status=Status.PENDING, plan=make_plan(value, 0.05))
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    _out, records = execute_ground(corpus, adapters, ctx)
    return records[0]


def test_integrate_does_not_advance_fdr_ledger(empty_ledger, ctx, adapters):
    # Phase 2.1: FDR ledger now advances in VERIFY, not INTEGRATE. integrate() must leave
    # n_tests unchanged regardless of exec_records supplied.
    rec = _exec_record_with_value("a", 0.01, ctx, adapters, empty_ledger)
    licensed = make_claim("a", status=Status.LICENSED)  # post-VERIFY status
    corpus = Corpus(claims=(licensed,), fdr_ledger=empty_ledger)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    before = corpus.fdr_ledger.n_tests
    out, skipped = integrate(corpus, scaffolding, (rec,))
    assert out.fdr_ledger.n_tests == before  # ledger unchanged by integrate
    assert skipped == ()                      # always empty tuple now


def test_integrate_returns_empty_skipped(empty_ledger, ctx, adapters):
    # integrate() always returns an empty skipped tuple (no FDR logic, no skipping).
    rec = _exec_record_with_value("a", 7.0, ctx, adapters, empty_ledger)
    c = make_claim("a", status=Status.PENDING)
    corpus = Corpus(claims=(c,), fdr_ledger=empty_ledger)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out, skipped = integrate(corpus, scaffolding, (rec,))
    assert skipped == ()


def test_integrate_keeps_consistent_claims(empty_ledger, ctx, adapters):
    rec = _exec_record_with_value("a", 0.01, ctx, adapters, empty_ledger)
    corpus = Corpus(claims=(make_claim("a", status=Status.LICENSED),), fdr_ledger=empty_ledger)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out, _skipped = integrate(corpus, scaffolding, (rec,))
    assert "a" in out.by_id()  # no inconsistency -> claim survives


def test_integrate_ledger_stable_with_two_claims(empty_ledger, ctx, adapters):
    # The ledger is untouched regardless of exec_record order (no FDR sorting logic).
    rec_a = _exec_record_with_value("a", 0.01, ctx, adapters, empty_ledger)
    rec_b = _exec_record_with_value("b", 0.03, ctx, adapters, empty_ledger)
    corpus = Corpus(
        claims=(make_claim("a", status=Status.LICENSED), make_claim("b", status=Status.LICENSED)),
        fdr_ledger=empty_ledger,
    )
    scaffolding = CycleScaffolding(grounded_extension=("a", "b"))
    out_fwd, _ = integrate(corpus, scaffolding, (rec_a, rec_b))
    out_rev, _ = integrate(corpus, scaffolding, (rec_b, rec_a))
    # ledger is unchanged in both directions
    assert out_fwd.fdr_ledger == empty_ledger
    assert out_rev.fdr_ledger == empty_ledger


def test_string_terminal_does_not_affect_ledger(empty_ledger):
    from polymer_grammar import (
        EvaluationResult, ExecValue, SatisfactionVerdict, VerifiedEvaluation,
    )
    from polymer_protocol.corpus import ExecRecord

    string_result = EvaluationResult(
        verdict=SatisfactionVerdict.UNDETERMINED, terminal=ExecValue(value="high"),
        nodes=(), adapter_identity="identity", status="complete",
    )
    ev = VerifiedEvaluation(results=(string_result,), agreement=False)
    rec = ExecRecord(claim_id="z", evaluation=ev)
    corpus = Corpus(claims=(make_claim("z", status=Status.PENDING),), fdr_ledger=empty_ledger)
    scaffolding = CycleScaffolding(grounded_extension=("z",))
    out, skipped = integrate(corpus, scaffolding, (rec,))
    assert out.fdr_ledger.n_tests == 0  # ledger unchanged
    assert skipped == ()                # no skipping in the new integrate


# ---------------------------------------------------------------------------
# Phase 2.2: defeat de-licenses + refunds the e-LOND discovery
# ---------------------------------------------------------------------------

def _licensing():
    return Licensing(
        route=LicenseRoute.SEVERE_TEST,
        satisfactions=(Satisfaction(
            verdict=SatisfactionVerdict.SATISFIED,
            materialization=MaterializationContext(id="M", api_version="v1", data_version="d1"),
        ),),
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
    )


def _licensed_A_with_discovery():
    a = make_claim("A", status=Status.LICENSED, licensing=_licensing())
    ledger = FDRLedger(target_fdr=0.05, tests=(
        FDRTest(index=1, claim_id="A", e_value=1e6, alpha_allocated=0.03, discovery=True),
    ))
    return a, ledger


def test_defeat_delicenses_and_refunds_discovery():
    a, ledger = _licensed_A_with_discovery()
    b = make_claim("B", status=Status.PENDING)
    edge = DefeatEdge(source="B", target="A", kind=DefeatEdgeKind.REBUT)
    corpus = Corpus(claims=(a, b), defeat_edges=(edge,), fdr_ledger=ledger)
    scaff = CycleScaffolding(grounded_extension=("A", "B"))
    out, _ = integrate(corpus, scaff, ())
    a2 = next(c for c in out.claims if c.id == "A")
    assert a2.status == Status.REJECTED
    assert a2.licensing is None
    assert out.fdr_ledger.n_discoveries == 0
    assert out.fdr_ledger.tests[0].retracted is True
    assert next(c for c in out.claims if c.id == "B").status == Status.PENDING


def test_no_defeat_is_back_compat():
    a, ledger = _licensed_A_with_discovery()
    corpus = Corpus(claims=(a,), defeat_edges=(), fdr_ledger=ledger)
    scaff = CycleScaffolding(grounded_extension=("A",))
    out, _ = integrate(corpus, scaff, ())
    a2 = next(c for c in out.claims if c.id == "A")
    assert a2.status == Status.LICENSED
    assert out.fdr_ledger.n_discoveries == 1
    assert out.fdr_ledger.tests[0].retracted is False


def _sv(severity: float, ean: float) -> StrengthVector:
    return StrengthVector(
        magnitude=0.5, certainty=0.5, evidence_against_null=ean,
        severity=severity, world_contact=0.5, explanatory_virtue=0.5,
    )


def test_agm_removed_licensed_claim_discovery_tombstoned():
    """A LICENSED claim removed by an AGM INCOMPATIBLE_WITH contest (less entrenched)
    has its e-LOND discovery tombstoned — the `removed` path in retract_ids."""
    # Build two incompatible conclusions: prop_b is incompatible with prop_a
    prop_b = Proposition(
        direction=Direction.NEGATIVE, estimand="e", descriptor="B",
        neighborhood=(NeighborEdge(kind=NeighborEdgeKind.INCOMPATIBLE_WITH, target="dummy_hash_A"),),
    )
    prop_a = Proposition(
        direction=Direction.POSITIVE, estimand="e", descriptor="A",
        neighborhood=(NeighborEdge(kind=NeighborEdgeKind.INCOMPATIBLE_WITH, target=prop_b.content_hash),),
    )
    # Rebuild prop_b to point at prop_a's actual content_hash
    prop_b2 = Proposition(
        direction=Direction.NEGATIVE, estimand="e", descriptor="B",
        neighborhood=(NeighborEdge(kind=NeighborEdgeKind.INCOMPATIBLE_WITH, target=prop_a.content_hash),),
    )
    # Rebuild prop_a to point at prop_b2's content_hash
    prop_a2 = Proposition(
        direction=Direction.POSITIVE, estimand="e", descriptor="A",
        neighborhood=(NeighborEdge(kind=NeighborEdgeKind.INCOMPATIBLE_WITH, target=prop_b2.content_hash),),
    )
    # strong_a (high strength) vs weak_b (low strength): AGM removes weak_b
    strong_a = make_claim("strong_a", status=Status.LICENSED, licensing=_licensing(),
                          conclusion=prop_a2, strength=_sv(0.9, 0.9))
    weak_b = make_claim("weak_b", status=Status.LICENSED, licensing=_licensing(),
                        conclusion=prop_b2, strength=_sv(0.1, 0.1))
    ledger = FDRLedger(target_fdr=0.05, tests=(
        FDRTest(index=1, claim_id="strong_a", e_value=1e6, alpha_allocated=0.02, discovery=True),
        FDRTest(index=2, claim_id="weak_b", e_value=1e5, alpha_allocated=0.03, discovery=True),
    ))
    corpus = Corpus(claims=(strong_a, weak_b), defeat_edges=(), fdr_ledger=ledger)
    scaff = CycleScaffolding(grounded_extension=("strong_a", "weak_b"))
    out, _ = integrate(corpus, scaff, ())
    # weak_b removed from claims by AGM
    assert not any(c.id == "weak_b" for c in out.claims)
    # weak_b's discovery tombstoned
    weak_test = next(t for t in out.fdr_ledger.tests if t.claim_id == "weak_b")
    assert weak_test.retracted is True
    # strong_a survives unaffected
    assert any(c.id == "strong_a" for c in out.claims)
    strong_test = next(t for t in out.fdr_ledger.tests if t.claim_id == "strong_a")
    assert strong_test.retracted is False
    assert out.fdr_ledger.n_discoveries == 1


# ---------------------------------------------------------------------------
# Task 3: INTEGRATE stamping + reinstatement
# ---------------------------------------------------------------------------

def test_defeat_stamps_rejection_reason():
    a, ledger = _licensed_A_with_discovery()
    b = make_claim("B", status=Status.PENDING)
    edge = DefeatEdge(source="B", target="A", kind=DefeatEdgeKind.REBUT)
    corpus = Corpus(claims=(a, b), defeat_edges=(edge,), fdr_ledger=ledger)
    scaff = CycleScaffolding(grounded_extension=("A", "B"))
    out, _ = integrate(corpus, scaff, ())
    a2 = next(c for c in out.claims if c.id == "A")
    assert a2.status == Status.REJECTED
    assert a2.rejection_reason == RejectionReason.DEFEAT_GROUNDED_OUT


def test_reinstatement_reopens_defeat_rejected_to_pending(empty_ledger):
    # A was defeat-rejected (B knocked it out). Now C defeats B, so grounded semantics brings A back
    # IN (flipped_in) -> A reopens to PENDING(REINSTATED) to re-test.
    a = make_claim("A", status=Status.REJECTED,
                   rejection_reason=RejectionReason.DEFEAT_GROUNDED_OUT,
                   plan=make_plan(0.01, 0.05))
    b = make_claim("B", status=Status.PENDING)
    c = make_claim("C", status=Status.LICENSED)
    edges = (DefeatEdge(source="B", target="A", kind=DefeatEdgeKind.REBUT),
             DefeatEdge(source="C", target="B", kind=DefeatEdgeKind.REBUT))
    corpus = Corpus(claims=(a, b, c), defeat_edges=edges, fdr_ledger=empty_ledger)
    scaff = CycleScaffolding(grounded_extension=("C", "B"))  # prior: A OUT
    out, _ = integrate(corpus, scaff, ())
    a2 = next(x for x in out.claims if x.id == "A")
    assert a2.status == Status.PENDING
    assert a2.pending_reason == PendingReason.REINSTATED
    assert a2.rejection_reason is None


def test_refuted_claim_in_extension_not_reopened(empty_ledger):
    # A REFUTED claim with no attackers sits in the grounded in_set every cycle (flipped_in) — it must
    # NOT be reopened (refutation is terminal). The correctness guard.
    r = make_claim("R", status=Status.REJECTED,
                   rejection_reason=RejectionReason.REFUTED,
                   plan=make_plan(0.01, 0.05))
    corpus = Corpus(claims=(r,), defeat_edges=(), fdr_ledger=empty_ledger)
    scaff = CycleScaffolding(grounded_extension=())  # R out prior; no attackers -> R in in_set
    out, _ = integrate(corpus, scaff, ())
    r2 = next(x for x in out.claims if x.id == "R")
    assert r2.status == Status.REJECTED
    assert r2.rejection_reason == RejectionReason.REFUTED


def test_defeat_rejected_without_plan_not_reopened(empty_ledger):
    # A planless reinstated claim could never self-relicense -> the has-plan gate skips it.
    a = make_claim("A", status=Status.REJECTED,
                   rejection_reason=RejectionReason.DEFEAT_GROUNDED_OUT)  # no plan
    b = make_claim("B", status=Status.PENDING)
    c = make_claim("C", status=Status.LICENSED)
    edges = (DefeatEdge(source="B", target="A", kind=DefeatEdgeKind.REBUT),
             DefeatEdge(source="C", target="B", kind=DefeatEdgeKind.REBUT))
    corpus = Corpus(claims=(a, b, c), defeat_edges=edges, fdr_ledger=empty_ledger)
    scaff = CycleScaffolding(grounded_extension=("C", "B"))
    out, _ = integrate(corpus, scaff, ())
    a2 = next(x for x in out.claims if x.id == "A")
    assert a2.status == Status.REJECTED  # planless -> not reopened


# ---------------------------------------------------------------------------
# Refund gate (evalue-claim-graph/fix-edge-kind-refund.md): a WARRANT-only defeat
# (undercut/reinterpret/reclassify) de-licenses in the graph but must NOT refund
# the e-LOND ledger — the effect is real, only the interpretation moved.
# ---------------------------------------------------------------------------

def test_warrant_only_defeat_delicenses_but_keeps_discovery_live():
    a, ledger = _licensed_A_with_discovery()
    b = make_claim("B", status=Status.PENDING)
    edge = DefeatEdge(source="B", target="A", kind=DefeatEdgeKind.UNDERCUT)
    corpus = Corpus(claims=(a, b), defeat_edges=(edge,), fdr_ledger=ledger)
    scaff = CycleScaffolding(grounded_extension=("A", "B"))
    out, _ = integrate(corpus, scaff, ())
    a2 = next(c for c in out.claims if c.id == "A")
    assert a2.status == Status.REJECTED          # de-licensed in the graph (grounded-OUT)
    assert out.fdr_ledger.tests[0].retracted is False   # but the ledger is NOT refunded
    assert out.fdr_ledger.n_discoveries == 1


def test_reinterpret_defeat_keeps_discovery_live():
    a, ledger = _licensed_A_with_discovery()
    b = make_claim("B", status=Status.PENDING)
    edge = DefeatEdge(source="B", target="A", kind=DefeatEdgeKind.REINTERPRET)
    corpus = Corpus(claims=(a, b), defeat_edges=(edge,), fdr_ledger=ledger)
    scaff = CycleScaffolding(grounded_extension=("A", "B"))
    out, _ = integrate(corpus, scaff, ())
    assert next(c for c in out.claims if c.id == "A").status == Status.REJECTED
    assert out.fdr_ledger.tests[0].retracted is False
    assert out.fdr_ledger.n_discoveries == 1
