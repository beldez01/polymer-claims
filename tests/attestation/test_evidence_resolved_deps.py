"""v2 Slice 2 — the EVIDENCE_LICENSED route lists its real artifacts in SLSA resolvedDependencies.

Additive: recompute-route claims have no `evidence_provenance` → no evidence deps → byte-identical
(covered by the unchanged attestation/golden suite). Digests are the route's already-computed
content addresses (never fabricated).
"""
from __future__ import annotations

from polymer_grammar.licensing import (
    LicenseRoute,
    Licensing,
    RivalSetClosure,
)
from polymer_grammar.verification_policy import EvidenceProvenance

from polymer_claims.attestation import (
    _evidence_resolved_dependencies,
    build_attestation_statements,
)
from tests.attestation._fixtures import corpus_with, licensed_claim, licensing, mc, sat


def _provenance() -> EvidenceProvenance:
    return EvidenceProvenance(
        claim_id="c-evidence",
        executor_descriptor_ref="sha256:" + "a" * 64,
        evidence_policy_ref="sha256:" + "b" * 64,
        benchmark_ref="bench:sha256:" + "c" * 64,
        baseline_config_ref="sha256:" + "d" * 64,
        baseline_predictions_ref="sha256:" + "e" * 64,
        predictor_config_ref="sha256:" + "f" * 64,
        capability_descriptor_ref="sha256:" + "1" * 64,
        observed_advantage=0.1, theta0=0.0, e_value=40.0,
        execution_contract_digest="sha256:" + "2" * 64,
        fdr_test_index=1, alpha_allocated=0.05,
        # oracle_dossier_ref left None -> that descriptor is dropped
    )


def _evidence_licensing() -> Licensing:
    return Licensing(
        route=LicenseRoute.EVIDENCE_LICENSED,
        satisfactions=(sat(mc()),),
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
        independence_tier=None,
        verification_standing="single_source_baseline",
        evidence_provenance=_provenance(),
    )


def test_evidence_resolved_dependencies_maps_real_digests():
    deps = _evidence_resolved_dependencies(_evidence_licensing())
    by_name = {d.name: d for d in deps}
    assert by_name["evidence:benchmark"].digest.sha256 == "c" * 64      # "bench:" stripped
    assert by_name["evidence:executor-descriptor"].digest.sha256 == "a" * 64
    assert by_name["evidence:baseline-predictions"].digest.sha256 == "e" * 64
    assert by_name["evidence:execution-contract"].digest.sha256 == "2" * 64
    assert "evidence:oracle-dossier" not in by_name  # oracle_dossier_ref is None -> dropped


def test_recompute_route_has_no_evidence_deps():
    # a recompute-route licensing carries no evidence_provenance -> empty -> byte-identical
    assert _evidence_resolved_dependencies(licensing(sat(mc()))) == ()


def test_statement_carries_evidence_artifacts_in_resolved_dependencies():
    claim = licensed_claim("c-evidence", _evidence_licensing())
    stmts = build_attestation_statements(corpus_with(claim), contract_index={})
    st = next(s for s in stmts if s.subject[0].name == "c-evidence")
    names = {d.name for d in st.predicate.build_definition.resolved_dependencies}
    assert {"evidence:benchmark", "evidence:executor-descriptor",
            "evidence:evidence-policy", "evidence:execution-contract"} <= names
