from polymer_grammar import (
    FDRLedger,
    GenerationMode,
    Governance,
    HazardClass,
    PatternRef,
    Provenance,
    Status,
    StrengthVector,
)

from polymer_protocol.corpus import Corpus
from polymer_protocol.cost import CostModel, CostVector, CostWeights
from polymer_protocol.ledger import OperatorCredit, SelectionLedger
from polymer_protocol.select import ValueWeights, cell_of, select_stage
from tests.conftest import make_claim, make_plan


def _corpus(claims):
    return Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=0.05))


def _sv(ean):
    return StrengthVector(magnitude=0.5, certainty=0.8, evidence_against_null=ean,
                          severity=0.5, world_contact=0.5, explanatory_virtue=0.5)


def _run(corpus, budget=None, cost_model=None):
    return select_stage(
        corpus, budget=budget,
        cost_model=cost_model or CostModel(),
        value_weights=ValueWeights(), cost_weights=CostWeights(),
    )


def test_only_pending_planned_unganged_claims_are_candidates():
    conj = make_claim("conj")  # CONJECTURED, no plan
    planless = make_claim("p", status=Status.PENDING)  # PENDING, no plan
    gated = make_claim("g", status=Status.PENDING, plan=make_plan(0.01, 0.05),
                       governance=Governance(hazard_class=HazardClass.HIGH))
    ok = make_claim("ok", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corp, rec = _run(_corpus([conj, planless, gated, ok]))
    selected = {d.claim_id for d in rec.decisions if d.selected}
    assert selected == {"ok"}
    assert rec.cardinality == 1  # only "ok" was a candidate


def test_unbounded_budget_selects_all_candidates():
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    b = make_claim("b", status=Status.PENDING, plan=make_plan(0.02, 0.05))
    corp, rec = _run(_corpus([a, b]), budget=None)
    assert {d.claim_id for d in rec.decisions if d.selected} == {"a", "b"}
    assert rec.cardinality == 2


def test_selected_claims_get_cardinality_stamped():
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    b = make_claim("b", status=Status.PENDING, plan=make_plan(0.02, 0.05))
    corp, rec = _run(_corpus([a, b]))
    for c in corp.claims:
        assert c.provenance is not None
        assert c.provenance.search_cardinality == 2


def test_zero_budget_selects_nothing():
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corp, rec = _run(_corpus([a]), budget=0.0)
    assert all(not d.selected for d in rec.decisions)
    # unselected claim is untouched (no provenance stamped)
    assert corp.by_id()["a"].provenance is None


def test_budget_prefers_higher_value_density():
    # cheap high-evidence claim beats expensive one under a tight budget
    cheap = make_claim("cheap", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_sv(0.9))
    pricey = make_claim("pricey", status=Status.PENDING, plan=make_plan(0.02, 0.05), strength=_sv(0.9))
    cost_model = CostModel(costs=(
        ("cheap", CostVector(wall_latency=1.0)),
        ("pricey", CostVector(wall_latency=100.0)),
    ))
    corp, rec = _run(_corpus([cheap, pricey]), budget=1.0, cost_model=cost_model)
    selected = {d.claim_id for d in rec.decisions if d.selected}
    assert "cheap" in selected and "pricey" not in selected


def test_empty_candidate_pool():
    corp, rec = _run(_corpus([make_claim("conj")]))
    assert rec.decisions == ()
    assert rec.cardinality == 0


def test_select_is_deterministic():
    def build():
        return _corpus([
            make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_sv(0.5)),
            make_claim("b", status=Status.PENDING, plan=make_plan(0.02, 0.05), strength=_sv(0.5)),
        ])
    r1 = _run(build())
    r2 = _run(build())
    assert r1 == r2


def test_public_exports():
    import polymer_protocol as p
    for name in ["select_stage", "ValueVector", "ValueWeights", "SelectionRecord",
                 "SelectionDecision", "Beta", "prior_belief", "expected_information_gain",
                 "stakes", "dependency_cone", "CostVector", "CostModel", "CostWeights",
                 "aggregate_cost"]:
        assert hasattr(p, name), name


def _run_b(corpus, budget=None, cost_model=None, ledger=None, reserve=0.0, cell_cap=1.0):
    return select_stage(
        corpus, budget=budget, cost_model=cost_model or CostModel(),
        value_weights=ValueWeights(), cost_weights=CostWeights(),
        ledger=ledger or SelectionLedger(), reserve_fraction=reserve, cell_cap_fraction=cell_cap,
    )


def test_cell_of_is_pattern_and_subject_kind():
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    assert cell_of(c) == "adjusted_effect|none"  # conftest pattern id + subject None


def test_defaults_reproduce_3a_selection():
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    b = make_claim("b", status=Status.PENDING, plan=make_plan(0.02, 0.05))
    corp = Corpus(claims=(a, b), fdr_ledger=FDRLedger(target_fdr=0.05))
    _, rec = _run_b(corp)
    assert {d.claim_id for d in rec.decisions if d.selected} == {"a", "b"}
    assert all(d.lane == "main" for d in rec.decisions if d.selected)


def test_reserve_lane_pursues_a_dominated_candidate():
    sv_strong = StrengthVector(magnitude=0.9, certainty=0.9, evidence_against_null=0.9,
                               severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    sv_weak = StrengthVector(magnitude=0.1, certainty=0.1, evidence_against_null=0.1,
                             severity=0.1, world_contact=0.1, explanatory_virtue=0.1)
    strong = make_claim("strong", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=sv_strong)
    weak = make_claim("weak", status=Status.PENDING, plan=make_plan(0.02, 0.05), strength=sv_weak)
    corp = Corpus(claims=(strong, weak), fdr_ledger=FDRLedger(target_fdr=0.05))
    cm = CostModel(costs=(("strong", CostVector(wall_latency=1.0)), ("weak", CostVector(wall_latency=1.0))))
    # EIG is HIGH for uncertain claims, LOW for confident ones: the high-uncertainty "weak"
    # claim has higher EIG -> dominates -> front -> main; the confident "strong" claim is
    # dominated (low EIG) -> the reserve lane pursues it once main (1.0) is exhausted.
    _, rec = _run_b(corp, budget=2.0, cost_model=cm, reserve=0.5)
    lanes = {d.claim_id: d.lane for d in rec.decisions if d.selected}
    assert lanes.get("weak") == "main"        # higher EIG (uncertain) -> front -> main
    assert lanes.get("strong") == "reserve"   # dominated (confident, low EIG) -> reserve lane


def test_cell_cap_spreads_budget_across_cells():
    patB = PatternRef(id="other_pattern", version="v1")
    a1 = make_claim("a1", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    a2 = make_claim("a2", status=Status.PENDING, plan=make_plan(0.02, 0.05))
    a3 = make_claim("a3", status=Status.PENDING, plan=make_plan(0.03, 0.05))
    b1 = make_claim("b1", status=Status.PENDING, plan=make_plan(0.01, 0.05), pattern=patB)
    corp = Corpus(claims=(a1, a2, a3, b1), fdr_ledger=FDRLedger(target_fdr=0.05))
    cm = CostModel(default=CostVector(wall_latency=1.0))
    # budget 3.0, cell_cap 0.34 -> each cell may spend <= ~1.02 (1 claim). B's lone cell gets served.
    _, rec = _run_b(corp, budget=3.0, cost_model=cm, cell_cap=0.34)
    selected = {d.claim_id for d in rec.decisions if d.selected}
    assert "b1" in selected


def test_operator_discount_changes_fill_priority():
    sv = StrengthVector(magnitude=0.5, certainty=0.8, evidence_against_null=0.5,
                        severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    good_prov = Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id="good", search_cardinality=1)
    bad_prov = Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id="bad", search_cardinality=1)
    g = make_claim("g", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=sv, provenance=good_prov)
    b = make_claim("b", status=Status.PENDING, plan=make_plan(0.02, 0.05), strength=sv, provenance=bad_prov)
    corp = Corpus(claims=(g, b), fdr_ledger=FDRLedger(target_fdr=0.05))
    cm = CostModel(default=CostVector(wall_latency=1.0))
    led = SelectionLedger(credits=(OperatorCredit(operator_id="bad", n_high_eig=20, n_grounded=0),))
    _, rec = _run_b(corp, budget=1.0, cost_model=cm, ledger=led)
    assert {d.claim_id for d in rec.decisions if d.selected} == {"g"}
