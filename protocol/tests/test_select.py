from polymer_grammar import FDRLedger, Governance, HazardClass, Status, StrengthVector

from polymer_protocol.corpus import Corpus
from polymer_protocol.cost import CostModel, CostVector, CostWeights
from polymer_protocol.select import ValueWeights, select_stage
from tests.conftest import make_claim, make_plan


def _corpus(claims):
    return Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=0.05))


def _sv(ean):
    return StrengthVector(magnitude=0.5, uncertainty=0.2, evidence_against_null=ean,
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
