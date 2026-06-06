import json

from polymer_grammar import (
    GenerationMode, IdentityAdapter, MaterializationContext, ReferenceAdapter, Status,
)
from polymer_protocol import Corpus, bridge_proposer, run_cycle
from polymer_claims.llm_adapter import LLMGenerationAdapter
from tests.conftest import make_claim   # umbrella builder

_CTX = MaterializationContext(id="M1", api_version="v1", data_version="d1")
_ADAPTERS = (IdentityAdapter(), ReferenceAdapter(identity="reference"))

_DSL = {"proposals": [{"title": "gen claim", "pattern_id": "adjusted_effect",
        "ontology_term": "g1", "value": 0.01, "comparator": "lt", "threshold": 0.05}]}


def _seed_corpus():
    # one CONJECTURED source claim for context; the LLM proposer adds the executable gen claim.
    # FDRLedger comes through the conftest; build a Corpus the same way licensing_corpus does.
    from polymer_grammar import FDRLedger
    return Corpus(claims=(make_claim("SRC"),), fdr_ledger=FDRLedger(target_fdr=0.05))


def _gen_proposer():
    return bridge_proposer((LLMGenerationAdapter(lambda _p: json.dumps(_DSL)),))


def test_generated_claim_licenses_through_run_cycle():
    res = run_cycle(_seed_corpus(), _ADAPTERS, _CTX, proposers=(_gen_proposer(),))
    gen = [c for c in res.corpus.claims if c.id.startswith("gen-llm-")]
    assert gen, "the LLM-generated claim was admitted"
    g = gen[0]
    assert g.status == Status.LICENSED
    assert g.provenance.generated_by == GenerationMode.AGENT_GENERATED
    assert g.provenance.agent_id == "llm-claim-proposer"   # forced by compile_untrusted at the bridge


def test_run_cycle_with_stub_adapter_is_deterministic():
    a = run_cycle(_seed_corpus(), _ADAPTERS, _CTX, proposers=(_gen_proposer(),))
    b = run_cycle(_seed_corpus(), _ADAPTERS, _CTX, proposers=(_gen_proposer(),))
    assert a.model_dump_json() == b.model_dump_json()


def test_forged_licensed_proposal_dropped_by_compile_untrusted():
    # The DSL can't express a licensing block, so assert the bridge's guard directly:
    # a directly-forged LICENSED claim is rejected by compile_untrusted (propose-not-license).
    from polymer_grammar import (
        CategoricalLeaf, Claim, LicenseRoute, Licensing, PatternRef, RivalSetClosure,
        Satisfaction, SatisfactionVerdict,
    )
    from polymer_protocol import compile_untrusted
    licensed = Claim(
        id="forged", title="forged", pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="t"),), status=Status.LICENSED,
        licensing=Licensing(route=LicenseRoute.SEVERE_TEST,
                            satisfactions=(Satisfaction(verdict=SatisfactionVerdict.SATISFIED,
                                materialization=_CTX),),
                            rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED),
    )
    cleaned, reason = compile_untrusted(licensed, "llm-claim-proposer", fingerprint="fp")
    assert cleaned is None and reason is not None
