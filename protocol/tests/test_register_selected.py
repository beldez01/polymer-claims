from polymer_protocol.register import register_selected
from polymer_protocol.select import ValueWeights, select_stage

from tests.helpers_select import SIMPLE_COST, SIMPLE_COST_WEIGHTS, two_equal_candidates


def _pending_ids(corpus):
    return {t.claim_id for t in corpus.fdr_ledger.tests if t.e_value is None and not t.retracted}


def test_registers_only_selected_topk():
    corpus = two_equal_candidates()  # both selected when budget is unbounded
    out, rec = select_stage(
        corpus, cost_model=SIMPLE_COST, budget=None,
        value_weights=ValueWeights(), cost_weights=SIMPLE_COST_WEIGHTS,
        cohort_of_ref={"ds1": "cohortX"},
    )
    # pursue only the top-1 by rank -> exactly one e-LOND slot charged
    reg = register_selected(out, rec, k=1)
    pending = _pending_ids(reg)
    assert len(pending) == 1
    # the charged one is the rank-0 (held-out) candidate
    assert "c_held" in pending and "c_conf" not in pending


def test_unselected_candidates_are_not_charged():
    corpus = two_equal_candidates()
    # tiny budget so SELECT picks only one candidate
    out, rec = select_stage(
        corpus, cost_model=SIMPLE_COST, budget=1.0,
        value_weights=ValueWeights(), cost_weights=SIMPLE_COST_WEIGHTS,
        cohort_of_ref={"ds1": "cohortX"},
    )
    reg = register_selected(out, rec)
    selected = {d.claim_id for d in rec.decisions if d.selected}
    assert _pending_ids(reg) == selected
