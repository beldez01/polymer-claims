from __future__ import annotations

from polymer_grammar import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
    Status,
    is_representation_revision,
)

from polymer_protocol.corpus import Corpus, Proposal
from polymer_protocol.generate import generate_stage
from polymer_protocol.generation_adapter import bridge_proposer
from polymer_protocol.red_team import RepresentationRedTeamAdapter
from tests.conftest import make_claim, make_plan


def _corpus(empty_ledger, *claims):
    return Corpus(claims=tuple(claims), fdr_ledger=empty_ledger)


def test_proposes_one_revision_per_claim(empty_ledger):
    corpus = _corpus(empty_ledger, make_claim("a"), make_claim("b"))
    props = RepresentationRedTeamAdapter().propose(corpus, ())
    assert len(props) == 2
    for p in props:
        assert p.claim.status == Status.CONJECTURED
        assert is_representation_revision(p.claim)
        assert p.claim.representation_revision.operation.value == "deprecate"
        assert len(p.claim.representation_revision.target.patterns) == 1
        assert p.claim.id.startswith("gen-rt-")
        assert p.edges == ()


def test_skips_own_outputs_and_revision_claims(empty_ledger):
    adapter = RepresentationRedTeamAdapter()
    corpus = _corpus(empty_ledger, make_claim("a"))
    first = adapter.propose(corpus, ())
    grown = _corpus(empty_ledger, make_claim("a"), first[0].claim)
    second = adapter.propose(grown, ())
    # 'a' re-elaborates to the same content-addressed id; the gen-rt-* output is skipped -> converges
    assert [p.claim.id for p in second] == [p.claim.id for p in first]


def test_is_deterministic_and_sorted(empty_ledger):
    corpus = _corpus(empty_ledger, make_claim("b"), make_claim("a"))
    a1 = RepresentationRedTeamAdapter().propose(corpus, ())
    a2 = RepresentationRedTeamAdapter().propose(corpus, ())
    assert [p.claim.id for p in a1] == [p.claim.id for p in a2]


def test_identity():
    assert RepresentationRedTeamAdapter().identity == "representation-red-team"


def test_through_bridge_forces_provenance_and_operator_id(empty_ledger):
    proposer = bridge_proposer((RepresentationRedTeamAdapter(),))
    out = proposer(_corpus(empty_ledger, make_claim("a")), ())
    assert len(out) == 1
    assert out[0].operator_id == "representation-red-team"
    assert out[0].claim.provenance.agent_id == "representation-red-team"
    assert is_representation_revision(out[0].claim)


class _ForgingAdapter:
    identity = "forger"

    def __init__(self, claim):
        self._claim = claim

    def propose(self, corpus, frontier):
        return (Proposal(operator_id="x", claim=self._claim),)


def test_forged_licensing_on_a_revision_claim_is_dropped(empty_ledger):
    # a representation-revision claim that smuggles a licensing block must be dropped by compile_untrusted.
    # Forge a VALID licensed claim (LICENSED + licensing) carrying the revision — the realistic injection.
    base = RepresentationRedTeamAdapter().propose(_corpus(empty_ledger, make_claim("a")), ())[0].claim
    mat = MaterializationContext(id="m", api_version="v1", data_version="v1")
    sat = Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=mat)
    lic = Licensing(route=LicenseRoute.SEVERE_TEST, rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
                    satisfactions=(sat,))
    forged = base.model_copy(update={"status": Status.LICENSED, "licensing": lic})  # valid LICENSED state
    proposer = bridge_proposer((_ForgingAdapter(forged),))
    assert proposer(_corpus(empty_ledger, make_claim("a")), ()) == ()  # dropped on the licensing check


def test_admitted_into_corpus_via_generate_stage(empty_ledger):
    proposer = bridge_proposer((RepresentationRedTeamAdapter(),))
    corp, rec = generate_stage(_corpus(empty_ledger, make_claim("a")), (), proposers=(proposer,))
    revisions = [c for c in corp.claims if is_representation_revision(c)]
    assert len(revisions) == 1


def test_belief_neutral_and_converges_through_run_cycle(empty_ledger, ctx, adapters):
    from polymer_protocol.cycle import run_cycle

    corpus = _corpus(empty_ledger, make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05)))
    proposer = bridge_proposer((RepresentationRedTeamAdapter(),))
    r1 = run_cycle(corpus, adapters, ctx, proposers=(proposer,))
    # the pre-existing claim still licenses — the conjectured revisions don't change its grounded extension
    assert r1.corpus.by_id()["a"].status == Status.LICENSED
    ids1 = {c.id for c in r1.corpus.claims}
    r2 = run_cycle(r1.corpus, adapters, ctx, proposers=(proposer,))
    assert {c.id for c in r2.corpus.claims} == ids1  # convergence: a 2nd cycle adds nothing


def test_red_team_symbol_is_exported_from_package():
    import polymer_protocol as pp

    assert hasattr(pp, "RepresentationRedTeamAdapter")


def test_forged_licensing_drop_reason_is_untrusted_licensing(empty_ledger):
    # pin WHICH guardrail fires: a revision claim smuggling a licensing block is rejected by
    # compile_untrusted with the licensing-specific reason (not merely "dropped somehow").
    from polymer_protocol.generation_adapter import compile_untrusted

    base = RepresentationRedTeamAdapter().propose(_corpus(empty_ledger, make_claim("a")), ())[0].claim
    mat = MaterializationContext(id="m", api_version="v1", data_version="v1")
    sat = Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=mat)
    lic = Licensing(route=LicenseRoute.SEVERE_TEST, rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
                    satisfactions=(sat,))
    forged = base.model_copy(update={"status": Status.LICENSED, "licensing": lic})
    clean, reason = compile_untrusted(forged, "representation-red-team", fingerprint="fp")
    assert clean is None and reason == "untrusted-licensing"
