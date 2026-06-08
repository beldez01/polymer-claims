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


def test_rationale_is_preserved_while_identity_is_forced():
    raw = _claim(
        "x",
        provenance=Provenance(
            generated_by=GenerationMode.AGENT_GENERATED,
            agent_id="someone",
            search_cardinality=1,
            rationale="why-x",
        ),
    )
    clean, reason = compile_untrusted(raw, "trusted-id", fingerprint="fp")
    assert reason is None and clean is not None
    assert clean.provenance.rationale == "why-x"          # benign free text survives
    assert clean.provenance.agent_id == "trusted-id"      # identity still forced
    assert clean.provenance.generated_by == GenerationMode.AGENT_GENERATED


def test_no_provenance_compiles_with_none_rationale():
    raw = _claim("x")  # provenance=None
    clean, reason = compile_untrusted(raw, "trusted-id", fingerprint="fp")
    assert reason is None and clean is not None
    assert clean.provenance.rationale is None


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


def test_pending_with_plan_is_accepted():
    # the load-bearing positive branch: an untrusted adapter MAY propose an executable
    # candidate (it still must clear the air-gapped verify to license).
    from tests.conftest import make_plan
    raw = _claim(
        "x", status=Status.PENDING, pending_reason=PendingReason.UNTESTED,
        evaluation_plan=make_plan(0.01, 0.05),
    )
    clean, reason = compile_untrusted(raw, "llm-7", fingerprint="fp")
    assert reason is None and clean is not None
    assert clean.status == Status.PENDING
    assert clean.evaluation_plan is not None
    assert clean.provenance.generated_by == GenerationMode.AGENT_GENERATED
    assert clean.provenance.agent_id == "llm-7"


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


def test_template_adapter_proposes_one_conjecture_per_claim():
    from polymer_protocol.generation_adapter import TemplateGenerationAdapter
    corp = _corpus([_claim("a"), _claim("b")])
    props = TemplateGenerationAdapter().propose(corp, ())
    assert len(props) == 2
    for p in props:
        assert p.claim.status == Status.CONJECTURED
        assert p.claim.id.startswith("gen-tmpl-")
        assert p.claim.conclusion is None and p.edges == ()


def test_template_adapter_is_deterministic():
    from polymer_protocol.generation_adapter import TemplateGenerationAdapter
    corp = _corpus([_claim("b"), _claim("a")])
    a1 = TemplateGenerationAdapter().propose(corp, ())
    a2 = TemplateGenerationAdapter().propose(corp, ())
    assert [p.claim.id for p in a1] == [p.claim.id for p in a2]


def test_template_adapter_skips_its_own_outputs():
    from polymer_protocol.generation_adapter import TemplateGenerationAdapter
    adapter = TemplateGenerationAdapter()
    corp = _corpus([_claim("a")])
    first = adapter.propose(corp, ())
    grown = _corpus([_claim("a"), first[0].claim])
    second = adapter.propose(grown, ())
    assert [p.claim.id for p in second] == [p.claim.id for p in first]  # only "a" elaborated, converges


def test_template_adapter_identity():
    from polymer_protocol.generation_adapter import TemplateGenerationAdapter
    assert TemplateGenerationAdapter().identity == "template-ref"


# --- C1: bridge coerces untrusted edges to provisional; compile_to_IR backstop ---


def test_bridge_coerces_untrusted_edges_to_provisional():
    from polymer_grammar import DefeatEdge, DefeatEdgeKind
    from polymer_protocol.corpus import Proposal
    from polymer_protocol.generation_adapter import bridge_proposer
    edge = DefeatEdge(source="x", target="honest", kind=DefeatEdgeKind.REBUT, provisional=False)
    raw = Proposal(operator_id="z", claim=_claim("x"), edges=(edge,))
    proposer = bridge_proposer((_StubAdapter("llm-7", [raw]),))
    out = proposer(_corpus(), ())
    assert len(out) == 1
    assert len(out[0].edges) == 1
    assert out[0].edges[0].provisional is True  # coerced inert until the source licenses


def test_compile_to_IR_rejects_non_provisional_self_sourced_edge():
    from polymer_grammar import DefeatEdge, DefeatEdgeKind
    from polymer_protocol.corpus import Proposal
    from polymer_protocol.generate import compile_to_IR
    claim = _claim("x")
    bad = DefeatEdge(source="x", target="honest", kind=DefeatEdgeKind.REBUT, provisional=False)
    prop = Proposal(operator_id="z", claim=claim, edges=(bad,))
    assert compile_to_IR(prop, {"honest"}) == "non-provisional-edge"
    # provisional version of the same edge is admissible
    ok = DefeatEdge(source="x", target="honest", kind=DefeatEdgeKind.REBUT, provisional=True)
    prop_ok = Proposal(operator_id="z", claim=claim, edges=(ok,))
    assert compile_to_IR(prop_ok, {"honest"}) is None


# --- C2: compile_to_IR rejects pre-LICENSED / licensing-bearing proposals ---


def test_compile_to_IR_rejects_illicit_licensing():
    # A valid LICENSED claim carrying a licensing block — the licensing check fires first.
    from polymer_protocol.corpus import Proposal
    from polymer_protocol.generate import compile_to_IR
    lic = _make_licensing()
    smuggled = _claim("x", status=Status.LICENSED, licensing=lic)
    prop = Proposal(operator_id="z", claim=smuggled)
    assert compile_to_IR(prop, set()) == "illicit-licensing"


def test_compile_to_IR_rejects_illicit_status():
    # A LICENSED claim with no licensing block — only the status check can catch it.
    from polymer_protocol.corpus import Proposal
    from polymer_protocol.generate import compile_to_IR
    smuggled = _claim("x").model_copy(update={"status": Status.LICENSED})
    prop = Proposal(operator_id="z", claim=smuggled)
    assert compile_to_IR(prop, set()) == "illicit-status"
