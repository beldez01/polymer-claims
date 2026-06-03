from polymer_grammar import Governance, HazardClass

from polymer_protocol.corpus import Corpus
from polymer_protocol.safety import safety_gate
from tests.conftest import make_claim


def test_clean_claims_are_not_gated(empty_ledger):
    corpus = Corpus(claims=(make_claim("a"), make_claim("b")), fdr_ledger=empty_ledger)
    out, gated = safety_gate(corpus)
    assert gated == ()
    assert out is corpus  # unchanged


def test_high_hazard_claim_is_gated(empty_ledger):
    hot = make_claim("h", governance=Governance(hazard_class=HazardClass.HIGH))
    dual = make_claim("d", governance=Governance(hazard_class=HazardClass.DUAL_USE))
    safe = make_claim("s", governance=Governance(hazard_class=HazardClass.LOW))
    corpus = Corpus(claims=(hot, dual, safe), fdr_ledger=empty_ledger)
    _out, gated = safety_gate(corpus)
    assert gated == ("d", "h")  # sorted; LOW is not gated


def test_none_guard_and_non_hazard_classes_not_gated(empty_ledger):
    plain = make_claim("p")  # governance is None
    none_hz = make_claim("n", governance=Governance(hazard_class=HazardClass.NONE))
    moderate = make_claim("m", governance=Governance(hazard_class=HazardClass.MODERATE))
    hot = make_claim("h", governance=Governance(hazard_class=HazardClass.HIGH))
    corpus = Corpus(claims=(plain, none_hz, moderate, hot), fdr_ledger=empty_ledger)
    _out, gated = safety_gate(corpus)
    assert gated == ("h",)  # only HIGH; None/NONE/MODERATE all pass through
