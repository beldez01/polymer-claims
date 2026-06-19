# protocol/tests/test_preregistration_e2e.py
from polymer_grammar import Comparator, FDRLedger, MaterializationContext, RejectionReason, Status
from polymer_grammar import IdentityAdapter, ReferenceAdapter
from polymer_protocol import Corpus, register_hypotheses, run_cycle

from tests.conftest import make_claim, make_plan   # tests/ is a package (has __init__.py)

ADAPTERS = (IdentityAdapter(), ReferenceAdapter(identity="reference"))
CTX = MaterializationContext(id="M", api_version="v1", data_version="d1")


def test_multiplicity_charged_end_to_end():
    # One real claim that would license alone; preceded by 9 registered decoys (fished hypotheses).
    # The locked alpha at t=10 raises the bar so a moderate e-value is WITHHELD.
    import math
    q, g1 = 0.05, 6.0 / math.pi**2
    moderate_e = 1.0 / (q * g1) + 5.0                 # clears t=1 bar, far below the t=10 bar
    target = make_claim("zzz_target", Status.PENDING, plan=make_plan(12.0, 10.0, Comparator.GT))
    decoys = [make_claim(f"decoy{i}", Status.PENDING, plan=make_plan(12.0, 10.0, Comparator.GT))
              for i in range(9)]
    corpus = register_hypotheses(
        Corpus(claims=(*decoys, target), fdr_ledger=FDRLedger(target_fdr=q)))
    out = run_cycle(corpus, ADAPTERS, CTX, evidence={"zzz_target": moderate_e})   # returns CycleResult
    t = next(x for x in out.corpus.fdr_ledger.tests if x.claim_id == "zzz_target")
    assert t.index == 10 and t.discovery is False         # multiplicity charged -> withheld
    target_out = next(c for c in out.corpus.claims if c.id == "zzz_target")
    assert target_out.status is not Status.LICENSED


def test_hypothesis_altered_is_not_reinstatable():
    # an integrity rejection must stay terminal even if its (nonexistent) attacker scenario is run
    from polymer_protocol.integrate import _reinstate  # the per-claim reinstatement helper
    rejected = make_claim("c", Status.REJECTED, rejection_reason=RejectionReason.HYPOTHESIS_ALTERED)
    out = _reinstate(rejected)
    assert out.status is Status.REJECTED                  # NOT reopened to PENDING
    assert out.rejection_reason is RejectionReason.HYPOTHESIS_ALTERED
