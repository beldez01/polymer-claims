from polymer_grammar import GenerationMode, Provenance, Status

from polymer_protocol.corpus import Corpus
from polymer_protocol.cost import CostModel, CostVector, CostWeights
from polymer_protocol.cycle import run_cycle
from polymer_protocol.ledger import credit_factor
from polymer_protocol.proposers import frontier_attack, rival_generation
from tests.conftest import make_claim, make_plan


def test_cycle_licenses_a_satisfied_claim(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    assert result.corpus.by_id()["a"].status == Status.LICENSED
    assert result.corpus.fdr_ledger.n_tests == 1
    assert result.gated_lane == ()
    # audit records one line per stage
    assert {a.stage for a in result.audit} == {
        "represent", "generate_stage", "canonicalize", "safety_gate", "select_stage",
        "commit", "execute_ground", "verify_stage", "integrate",
    }


def test_cycle_reports_gated_lane(empty_ledger, ctx, adapters):
    from polymer_grammar import Governance, HazardClass

    hot = make_claim(
        "h", status=Status.PENDING, plan=make_plan(0.01, 0.05),
        governance=Governance(hazard_class=HazardClass.HIGH),
    )
    result = run_cycle(Corpus(claims=(hot,), fdr_ledger=empty_ledger), adapters, ctx)
    assert result.gated_lane == ("h",)
    # gated claim was NOT executed -> still PENDING, no FDR test
    assert result.corpus.by_id()["h"].status == Status.PENDING
    assert result.corpus.fdr_ledger.n_tests == 0


def test_cycle_is_deterministic(empty_ledger, ctx, adapters):
    def build():
        return Corpus(
            claims=(
                make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05)),
                make_claim("b", status=Status.PENDING, plan=make_plan(0.99, 0.05)),
            ),
            fdr_ledger=empty_ledger,
        )

    first = run_cycle(build(), adapters, ctx)
    second = run_cycle(build(), adapters, ctx)
    assert first == second  # same (corpus, adapters, ctx) -> identical CycleResult


def test_frontier_is_emitted_for_an_unresolved_attack(empty_ledger, ctx, adapters):
    from polymer_grammar import DefeatEdge, DefeatEdgeKind

    # b (CONJECTURED, no plan) attacks a; nothing defends a -> a is on the frontier.
    a = make_claim("a")
    b = make_claim("b")
    edge = DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT)
    corpus = Corpus(claims=(a, b), defeat_edges=(edge,), fdr_ledger=empty_ledger)
    result = run_cycle(corpus, adapters, ctx)
    assert result.frontier == ("a",)


def test_run_cycle_caps_strength_with_registry(empty_ledger, ctx, adapters):
    from polymer_grammar import OracleDossier, StrengthVector, ValidationTier
    from polymer_protocol import OracleRegistry

    sv = StrengthVector(magnitude=0.9, uncertainty=0.9, evidence_against_null=0.9,
                        severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05, oracle_ref="api"), strength=sv)
    reg = OracleRegistry(dossiers=(OracleDossier(oracle_id="api", validation_tier=ValidationTier.BENCHMARKED),))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx, oracles=reg)
    graded = result.corpus.by_id()["a"]
    assert graded.status == Status.LICENSED
    assert graded.strength.magnitude == 0.6           # BENCHMARKED ceiling
    assert graded.strength.explanatory_virtue == 0.9  # theory axis untouched


def test_run_cycle_caps_oracle_claim_without_registry(empty_ledger, ctx, adapters):
    # Always-on guarantee at the run_cycle layer: an oracle_ref with no registry -> UNVALIDATED.
    from polymer_grammar import StrengthVector

    sv = StrengthVector(magnitude=0.9, uncertainty=0.9, evidence_against_null=0.9,
                        severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05, oracle_ref="api"), strength=sv)
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)  # no oracles
    graded = result.corpus.by_id()["a"]
    assert graded.status == Status.LICENSED
    assert graded.strength.magnitude == 0.0   # unresolved oracle -> capped, even with no registry
    assert graded.strength.severity == 0.9    # theory axis untouched


def test_budget_limits_what_executes(empty_ledger, ctx, adapters):
    from polymer_grammar import StrengthVector
    sv = StrengthVector(magnitude=0.5, uncertainty=0.2, evidence_against_null=0.95,
                        severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    # distinct plan values so canonicalize does not collapse them
    cheap = make_claim("cheap", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=sv)
    pricey = make_claim("pricey", status=Status.PENDING, plan=make_plan(0.02, 0.05), strength=sv)
    cost_model = CostModel(costs=(
        ("cheap", CostVector(wall_latency=1.0)),
        ("pricey", CostVector(wall_latency=100.0)),
    ))
    corpus = Corpus(claims=(cheap, pricey), fdr_ledger=empty_ledger)
    result = run_cycle(corpus, adapters, ctx, cost_model=cost_model,
                       budget=1.0, cost_weights=CostWeights())
    assert result.corpus.by_id()["cheap"].status == Status.LICENSED
    assert result.corpus.by_id()["pricey"].status == Status.PENDING
    assert result.selection.cardinality == 2
    assert {d.claim_id for d in result.selection.decisions if d.selected} == {"cheap"}


def test_unselected_claim_reappears_next_cycle(empty_ledger, ctx, adapters):
    from polymer_grammar import StrengthVector
    sv = StrengthVector(magnitude=0.5, uncertainty=0.2, evidence_against_null=0.9,
                        severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    cheap = make_claim("cheap", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=sv)
    pricey = make_claim("pricey", status=Status.PENDING, plan=make_plan(0.02, 0.05), strength=sv)
    cost_model = CostModel(costs=(
        ("cheap", CostVector(wall_latency=1.0)),
        ("pricey", CostVector(wall_latency=100.0)),
    ))
    c1 = run_cycle(Corpus(claims=(cheap, pricey), fdr_ledger=empty_ledger), adapters, ctx,
                   cost_model=cost_model, budget=1.0)
    # second cycle with a big budget: pricey (still PENDING) now executes
    c2 = run_cycle(c1.corpus, adapters, ctx, budget=None)
    assert c2.corpus.by_id()["pricey"].status == Status.LICENSED


def test_audit_includes_select_stage(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    assert "select_stage" in {a.stage for a in result.audit}


def test_audit_includes_generate_stage(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    assert "generate_stage" in {a.stage for a in result.audit}


def test_injected_claim_flows_through_and_licenses(empty_ledger, ctx, adapters):
    # an exogenous PENDING-with-plan claim enters via the port and licenses this cycle
    injected = make_claim("inj", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    result = run_cycle(Corpus(fdr_ledger=empty_ledger), adapters, ctx, injected=(injected,))
    assert result.corpus.by_id()["inj"].status == Status.LICENSED
    assert result.generation.proposed == 1
    assert result.generation.admitted == ("inj",)


def test_frontier_attack_plants_a_seed(empty_ledger, ctx, adapters):
    from polymer_grammar import DefeatEdge, DefeatEdgeKind
    # b (CONJECTURED, no plan) attacks a -> a on frontier -> frontier_attack plants a seed D
    a, b = make_claim("a"), make_claim("b")
    edge = DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT)
    corpus = Corpus(claims=(a, b), defeat_edges=(edge,), fdr_ledger=empty_ledger)
    result = run_cycle(corpus, adapters, ctx, proposers=(frontier_attack,))
    # a new gen-fa-* CONJECTURED seed claim appears; NO new defeat edge was added (belief-neutral)
    assert any(cid.startswith("gen-fa-") for cid in result.corpus.by_id())
    assert len(result.corpus.defeat_edges) == 1  # still just the original b->a edge


def test_generation_converges(empty_ledger, ctx, adapters):
    from polymer_grammar import Direction, Proposition
    c = make_claim("c", conclusion=Proposition(direction=Direction.POSITIVE, estimand="b", descriptor="d"))
    corpus = Corpus(claims=(c,), fdr_ledger=empty_ledger)
    c1 = run_cycle(corpus, adapters, ctx, proposers=(rival_generation,))
    n1 = len(c1.corpus.claims)
    c2 = run_cycle(c1.corpus, adapters, ctx, proposers=(rival_generation,))
    assert len(c2.corpus.claims) == n1  # second cycle adds nothing — convergent
    assert c2.generation.admitted == ()


def test_default_generation_is_noop(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    assert result.generation.proposed == 0
    assert result.corpus.by_id()["a"].status == Status.LICENSED  # #3a path unaffected


def test_ledger_threads_and_accumulates(empty_ledger, ctx, adapters):
    # a satisfied claim licenses -> its ClaimOutcome accrues a success in the returned ledger
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    o = result.ledger.outcome("a")
    assert o is not None and o.successes == 1


def test_ledger_default_is_backcompat(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    # default reserve/cell-cap OFF -> claim still licenses exactly as #3a
    assert result.corpus.by_id()["a"].status == Status.LICENSED


def test_rejected_claim_records_failure(empty_ledger, ctx, adapters):
    # value 0.99 vs threshold 0.05 (LT) -> NOT satisfied -> REFUTED -> REJECTED -> a failure outcome
    c = make_claim("miss", status=Status.PENDING, plan=make_plan(0.99, 0.05))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    o = result.ledger.outcome("miss")
    assert o is not None and o.failures == 1


def test_ledger_threads_across_two_cycles(empty_ledger, ctx, adapters):
    # the returned ledger can be fed into the next run_cycle
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    r1 = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    r2 = run_cycle(r1.corpus, adapters, ctx, ledger=r1.ledger)
    # a once-licensed claim is terminal (not re-executed) -> its success count is unchanged at 1
    assert r2.ledger.outcome("a").successes == 1


def test_surprise_goodhart_accrues_through_run_cycle(empty_ledger, ctx, adapters):
    # A high-EIG (strength-None -> max-uncertainty -> EIG ~0.278) claim from operator "bad"
    # that gets REJECTED must accrue a high-EIG miss against "bad" in the returned ledger,
    # dropping its credit_factor below 1.0 next cycle. (Before the HIGH_EIG recalibration this
    # was impossible because eig could never reach the 0.5 threshold.)
    bad_prov = Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id="bad", search_cardinality=1)
    # plan value 0.99 vs threshold 0.05 (LT) -> NOT satisfied -> REFUTED -> REJECTED; strength None -> high EIG
    miss = make_claim("m", status=Status.PENDING, plan=make_plan(0.99, 0.05), provenance=bad_prov)
    result = run_cycle(Corpus(claims=(miss,), fdr_ledger=empty_ledger), adapters, ctx)
    cr = result.ledger.credit("bad")
    assert cr is not None and cr.n_high_eig == 1 and cr.n_grounded == 0  # accrued a high-EIG miss
    assert credit_factor(result.ledger, "bad") == 0.5  # (0+1)/(1+1) -> discounted next cycle


def test_unselected_locked_claim_does_not_reexecute(empty_ledger, ctx, adapters):
    # A claim that stays PENDING after execution (fails the cardinality-BH bar in a pool) is
    # locked. Next cycle, if SELECT does not select it (budget=0), it must NOT re-execute.
    # Regression for F1: execute_ground must be gated by this cycle's selection, not the
    # permanent preregistration lock.
    from polymer_grammar import StrengthVector
    sv = StrengthVector(magnitude=0.5, uncertainty=0.2, evidence_against_null=0.5,
                        severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=sv)
    b = make_claim("b", status=Status.PENDING, plan=make_plan(0.02, 0.05), strength=sv)
    r1 = run_cycle(Corpus(claims=(a, b), fdr_ledger=empty_ledger), adapters, ctx)
    # both fail the BH bar (pseudo-p 0.5 vs crit (k/2)*0.10) -> stay PENDING, locked
    assert r1.corpus.by_id()["a"].status == Status.PENDING
    assert r1.corpus.by_id()["b"].status == Status.PENDING
    # cycle 2, budget 0 -> SELECT picks nothing -> NOTHING re-executes
    r2 = run_cycle(r1.corpus, adapters, ctx, budget=0.0)
    n_executed = next(x.count for x in r2.audit if x.stage == "execute_ground")
    assert n_executed == 0  # F1: was 2 before the fix (locked claims bypassed selection)
