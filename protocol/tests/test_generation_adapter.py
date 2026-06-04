from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    GenerationMode,
    Governance,
    HazardClass,
    LicenseRoute,
    Licensing,
    MaterializationContext,
    PatternRef,
    PendingReason,
    Provenance,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
    Status,
)

from polymer_protocol.generation_adapter import compile_untrusted

_PAT = PatternRef(id="adjusted_effect", version="v1")


def _claim(cid, status=Status.CONJECTURED, **extra):
    return Claim(
        id=cid,
        title=f"c {cid}",
        pattern=_PAT,
        leaves=(CategoricalLeaf(ontology_term=f"t-{cid}"),),
        status=status,
        **extra,
    )


def _make_licensing() -> Licensing:
    """Build a valid Licensing record (requires >=1 SATISFIED satisfaction)."""
    mat = MaterializationContext(id="m1", api_version="v1", data_version="v1")
    sat = Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=mat)
    return Licensing(
        route=LicenseRoute.SEVERE_TEST,
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
        rivals_considered=(),
        satisfactions=(sat,),
    )


def test_conjectured_claim_is_accepted_and_provenance_forced():
    raw = _claim("x")  # no provenance
    clean, reason = compile_untrusted(raw, "llm-7", fingerprint="fp")
    assert reason is None and clean is not None
    assert clean.provenance.generated_by == GenerationMode.AGENT_GENERATED
    assert clean.provenance.agent_id == "llm-7"
    assert clean.provenance.method == "llm-7@fp"
    assert clean.provenance.search_cardinality >= 1


def test_incoming_provenance_is_overwritten_not_trusted():
    raw = _claim("x", provenance=Provenance(generated_by=GenerationMode.IMPORTED, agent_id=None, search_cardinality=1))
    clean, reason = compile_untrusted(raw, "llm-7", fingerprint="fp")
    assert reason is None
    assert clean.provenance.generated_by == GenerationMode.AGENT_GENERATED
    assert clean.provenance.agent_id == "llm-7"


def test_licensed_status_is_rejected():
    lic = _make_licensing()
    raw = _claim("x", status=Status.LICENSED, licensing=lic)
    clean, reason = compile_untrusted(raw, "llm-7", fingerprint="fp")
    assert clean is None and reason == "untrusted-licensing"


def test_licensing_block_without_licensed_status_is_rejected():
    # model_copy bypasses Pydantic validators — lets us create an invalid-state claim
    # (licensing present but status=CONJECTURED) to test that compile_untrusted rejects it.
    lic = _make_licensing()
    raw = _claim("x").model_copy(update={"licensing": lic})
    clean, reason = compile_untrusted(raw, "llm-7", fingerprint="fp")
    assert clean is None and reason == "untrusted-licensing"


def test_rejected_status_is_rejected():
    raw = _claim("x", status=Status.REJECTED)
    clean, reason = compile_untrusted(raw, "llm-7", fingerprint="fp")
    assert clean is None and reason == "untrusted-status"


def test_pending_without_plan_is_rejected():
    raw = _claim("x", status=Status.PENDING, pending_reason=PendingReason.UNTESTED)
    clean, reason = compile_untrusted(raw, "llm-7", fingerprint="fp")
    assert clean is None and reason == "untrusted-status"


def test_governance_is_preserved():
    gov = Governance(hazard_class=HazardClass.DUAL_USE)
    raw = _claim("x", governance=gov)
    clean, reason = compile_untrusted(raw, "llm-7", fingerprint="fp")
    assert reason is None and clean.governance == gov


def _corpus(claims=()):
    from polymer_grammar import FDRLedger
    from polymer_protocol.corpus import Corpus
    return Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=0.05))


class _StubAdapter:
    def __init__(self, identity, proposals):
        self.identity = identity
        self._proposals = proposals

    def propose(self, corpus, frontier):
        return tuple(self._proposals)


def test_bridge_forces_operator_id_to_adapter_identity():
    from polymer_protocol.corpus import Proposal
    from polymer_protocol.generation_adapter import bridge_proposer
    raw = Proposal(operator_id="IMPERSONATING-rival-generation", claim=_claim("x"))
    proposer = bridge_proposer((_StubAdapter("llm-7", [raw]),))
    out = proposer(_corpus(), ())
    assert len(out) == 1 and out[0].operator_id == "llm-7"
    assert out[0].claim.provenance.agent_id == "llm-7"


def test_bridge_drops_rejected_keeps_valid():
    from polymer_protocol.corpus import Proposal
    from polymer_protocol.generation_adapter import bridge_proposer
    good = Proposal(operator_id="x", claim=_claim("good"))
    bad = Proposal(operator_id="x", claim=_claim("bad", status=Status.REJECTED))
    proposer = bridge_proposer((_StubAdapter("llm-7", [good, bad]),))
    out = proposer(_corpus(), ())
    assert [p.claim.id for p in out] == ["good"]


def test_bridge_tags_each_adapter_distinctly():
    from polymer_protocol.corpus import Proposal
    from polymer_protocol.generation_adapter import bridge_proposer
    a = _StubAdapter("emb-A", [Proposal(operator_id="z", claim=_claim("a1"))])
    b = _StubAdapter("llm-B", [Proposal(operator_id="z", claim=_claim("b1"))])
    out = bridge_proposer((a, b))(_corpus(), ())
    tagged = {p.claim.id: p.operator_id for p in out}
    assert tagged == {"a1": "emb-A", "b1": "llm-B"}


def test_bridge_result_is_a_usable_proposer():
    from polymer_protocol.corpus import Proposal
    from polymer_protocol.generate import generate_stage
    from polymer_protocol.generation_adapter import bridge_proposer
    proposer = bridge_proposer((_StubAdapter("llm-7", [Proposal(operator_id="x", claim=_claim("x"))]),))
    corp, rec = generate_stage(_corpus(), (), proposers=(proposer,))
    assert "x" in [c.id for c in corp.claims]
    assert "x" in rec.admitted
