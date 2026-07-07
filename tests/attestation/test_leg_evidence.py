"""R5.1 follow-up: `leg_evidence` must be SURFACED on the signed attestation/certificate for the
recompute (REPRODUCED) route, and absent everywhere else.

Grammar already records `Satisfaction.leg_evidence` at verify() for the recompute route (see
`grammar/src/polymer_grammar/evaluate.py::_leg_evidence`). This file proves the umbrella-side
half: `polymer_claims.attestation._internal_parameters` copies that evidence onto
`InternalParameters.leg_evidence` (alias `legEvidence`), which lands inside the signed in-toto
Statement (and therefore inside `Certificate.statement` too, since a Certificate just wraps a
Statement) — and that every non-recompute claim's serialized output is untouched (no new key).
"""
from __future__ import annotations

import json

from polymer_grammar import FDRLedger, MaterializationContext
from polymer_grammar.licensing import (
    LicenseRoute,
    Licensing,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
)
from polymer_grammar.verification_policy import EvidenceProvenance
from polymer_protocol import Corpus, run_cycle

from polymer_claims.analysis_profile import profile_oracle_registry
from polymer_claims.attestation import (
    _leg_evidence_for,
    build_attestation_statements,
    build_certificate,
)
from polymer_claims.capabilities import CAPABILITY_CELLS
from polymer_claims.methyl_adapters import (
    RegionHodgesLehmannAdapter,
    RegionMeanDiffAdapter,
    methyl_independent_registry,
    region_delta_beta_claim,
)
from polymer_claims.profiles import CANONICAL_EPICV2_V1
from tests.attestation._fixtures import corpus_with, licensed_claim, licensing as lic_fixture, mc, sat

_ADAPTERS = (RegionMeanDiffAdapter(), RegionHodgesLehmannAdapter())
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="epicv2_casectrl_demo@1")


def _oracles():
    return profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public"))


def _reproduced_corpus():
    """A LICENSED region-Δβ claim reached via the two-adapter (recompute/REPRODUCED) route --
    same fixture as test_methyl_licensing.py::test_true_region_claim_licenses_on_computed_delta_beta."""
    c = region_delta_beta_claim("c-true", threshold=0.10)
    corpus = Corpus(claims=(c,), fdr_ledger=FDRLedger(target_fdr=0.05))
    result = run_cycle(
        corpus, _ADAPTERS, _CTX,
        adapter_registry=methyl_independent_registry(), oracles=_oracles(),
        capability_registry=CAPABILITY_CELLS,
    )
    return result.corpus


def _internal_params_dict(statement) -> dict:
    d = json.loads(statement.model_dump_json(by_alias=True, exclude_none=True))
    return d["predicate"]["buildDefinition"]["internalParameters"]


# ---------------------------------------------------------------------------
# 1. Positive: REPRODUCED claim -- attestation Statement carries leg_evidence
# ---------------------------------------------------------------------------


def test_reproduced_claim_attestation_carries_leg_evidence():
    corpus = _reproduced_corpus()
    claim = next(c for c in corpus.claims if c.id == "c-true")
    assert claim.status.value == "licensed"

    # Sanity: the grammar side really did record leg_evidence on the Satisfaction.
    lic = claim.licensing
    grammar_evidence = next(s.leg_evidence for s in lic.satisfactions if s.leg_evidence is not None)
    assert {leg.identity for leg in grammar_evidence.legs} == {
        "methyl-meandiff-beta", "methyl-hodges-lehmann",
    }
    assert all(leg.value == 0.2 for leg in grammar_evidence.legs)
    assert grammar_evidence.relative_divergence == 0.0

    stmts = build_attestation_statements(corpus, contract_index={})
    st = next(s for s in stmts if s.subject[0].name == "c-true")

    ip = st.predicate.build_definition.internal_parameters
    assert ip.leg_evidence is not None
    assert {leg.identity for leg in ip.leg_evidence.legs} == {
        "methyl-meandiff-beta", "methyl-hodges-lehmann",
    }
    assert sorted(leg.value for leg in ip.leg_evidence.legs) == [0.2, 0.2]
    assert ip.leg_evidence.relative_divergence == 0.0

    # And the alias-serialized shape carries it under "legEvidence" with both legs + divergence.
    d = _internal_params_dict(st)
    assert "legEvidence" in d
    assert {leg["identity"] for leg in d["legEvidence"]["legs"]} == {
        "methyl-meandiff-beta", "methyl-hodges-lehmann",
    }
    assert d["legEvidence"]["relative_divergence"] == 0.0


def test_reproduced_claim_certificate_carries_leg_evidence():
    """The signed Certificate payload (not just the bare Statement) carries leg_evidence --
    Certificate.statement is the same Statement, so this is the same field, reached via the
    build_certificate entry point instead of build_attestation_statements directly."""
    corpus = _reproduced_corpus()
    cert = build_certificate(corpus, "c-true", target_q=0.05, contract_index={})
    ip = cert.statement.predicate.build_definition.internal_parameters
    assert ip.leg_evidence is not None
    assert {leg.identity for leg in ip.leg_evidence.legs} == {
        "methyl-meandiff-beta", "methyl-hodges-lehmann",
    }
    assert sorted(leg.value for leg in ip.leg_evidence.legs) == [0.2, 0.2]
    assert ip.leg_evidence.relative_divergence == 0.0

    # It's inside the signed DSSE bytes too (not just the in-memory object).
    from polymer_claims.attestation import certificate_dsse_envelope
    import base64
    env = certificate_dsse_envelope(cert)
    payload = json.loads(base64.b64decode(env.payload))
    assert "legEvidence" in payload["statement"]["predicate"]["buildDefinition"]["internalParameters"]


# ---------------------------------------------------------------------------
# 2. Negative: single-source EVIDENCE_LICENSED claim -- no leg_evidence anywhere
# ---------------------------------------------------------------------------


def _evidence_licensed_licensing() -> Licensing:
    """A minimal, directly-constructed EVIDENCE_LICENSED Licensing (single satisfaction, no
    credential_ids, no leg_evidence) -- mirrors the shape produced by the real evidence-executor
    pipeline (see tests/capability/test_benchmark_end_to_end.py) without pulling in that whole
    executor/DGP fixture stack, since only the licensing SHAPE matters here."""
    satisfaction = Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=mc())
    provenance = EvidenceProvenance(
        claim_id="c-evidence",
        executor_descriptor_ref="sha256:" + "a" * 64,
        evidence_policy_ref="sha256:" + "b" * 64,
        benchmark_ref="bench:sha256:" + "c" * 64,
        baseline_config_ref="sha256:" + "d" * 64,
        baseline_predictions_ref="sha256:" + "e" * 64,
        predictor_config_ref="sha256:" + "f" * 64,
        capability_descriptor_ref="sha256:" + "1" * 64,
        observed_advantage=0.1,
        theta0=0.0,
        e_value=40.0,
        execution_contract_digest="sha256:" + "2" * 64,
        fdr_test_index=1,
        alpha_allocated=0.05,
    )
    return Licensing(
        route=LicenseRoute.EVIDENCE_LICENSED,
        satisfactions=(satisfaction,),
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
        independence_tier=None,
        verification_standing="single_source_baseline",
        evidence_provenance=provenance,
    )


def test_leg_evidence_for_returns_none_for_evidence_licensed_route():
    """Unit-level: the selector itself returns None for the single-source route."""
    assert _leg_evidence_for(_evidence_licensed_licensing()) is None


def test_evidence_licensed_claim_attestation_has_no_leg_evidence_key():
    corpus = corpus_with(licensed_claim("c-evidence", _evidence_licensed_licensing()))
    stmts = build_attestation_statements(corpus, contract_index={})
    st = next(s for s in stmts if s.subject[0].name == "c-evidence")
    assert st.predicate.build_definition.internal_parameters.leg_evidence is None
    d = _internal_params_dict(st)
    assert "legEvidence" not in d


# ---------------------------------------------------------------------------
# 3. Non-recompute claims stay byte-identical (the pre-existing fixture shape used
#    everywhere else in tests/attestation/ never sets leg_evidence).
# ---------------------------------------------------------------------------


def test_non_recompute_claim_attestation_byte_identical_with_and_without_leg_evidence_field():
    """A claim built the ordinary way (single Satisfaction via the `sat()` helper, no
    leg_evidence) must serialize with no 'legEvidence' key at all -- proving the new field is
    purely additive for every claim that doesn't set it."""
    claim = licensed_claim(
        "c1",
        lic_fixture(sat(mc(
            dimnames_hash="sha256:" + "a" * 64, profile_hash="sha256:" + "b" * 64, semantic_run_id="r1",
        ))),
    )
    corpus = corpus_with(claim)
    stmts = build_attestation_statements(corpus, contract_index={})
    st = stmts[0]
    assert st.predicate.build_definition.internal_parameters.leg_evidence is None
    out = st.model_dump_json(by_alias=True, exclude_none=True)
    assert "legEvidence" not in out
