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
