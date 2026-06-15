"""CES-0 capstone: binding a claim to a profile (via oracle_ref) caps its empirical strength
to the substrate tier, end-to-end through run_cycle."""
from __future__ import annotations

from polymer_claims.analysis_profile import (
    profile_oracle_dossier,
    profile_oracle_id,
)
from polymer_claims.exec_adapters import (
    StatsPureAdapter,
    StatsStdlibAdapter,
    _PROVISIONAL_STRENGTH,
    independent_registry,
    mean_diff_claim,
)
from polymer_claims.profiles import load_profile
from polymer_grammar import Comparator, FDRLedger, MaterializationContext, Status
from polymer_protocol import Corpus, OracleRegistry, run_cycle

_CTX = MaterializationContext(id="M1", api_version="v1", data_version="dose_response@v1")


def _unbounded_registry(profile, substrate):
    """Build an OracleRegistry with an UNBOUNDED applicability domain (no subject_kinds).
    The mean_diff_claim has no subject, so a bounded domain (e.g. genomic_region/cohort)
    would resolve out-of-domain -> UNVALIDATED. CES-0 uses a proxy claim to prove the
    profile->tier->cap path; real methylation claims will carry a subject and use the
    bounded domain."""
    dossier = profile_oracle_dossier(profile, substrate=substrate, subject_kinds=())
    return OracleRegistry(dossiers=(dossier,))


def _run_with(profile, substrate):
    claim = mean_diff_claim(
        "ces0-bound",
        comparator=Comparator.GT,
        threshold=10.0,
        strength=_PROVISIONAL_STRENGTH,
        oracle_ref=profile_oracle_id(profile),
    )
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    result = run_cycle(
        corpus,
        (StatsPureAdapter(), StatsStdlibAdapter()),
        _CTX,
        adapter_registry=independent_registry(),
        oracles=_unbounded_registry(profile, substrate),
        budget=2.5,
    )
    return result.corpus.by_id()["ces0-bound"]


def test_recomputable_public_caps_empirical_axes_to_benchmarked():
    profile = load_profile("pinned_design_epicv2_hg38_v1", "1")
    claim = _run_with(profile, "recomputable_public")
    assert claim.status == Status.LICENSED
    s = claim.strength
    # BENCHMARKED ceiling = 0.6 on the four goodness empirical axes (capped DOWN from 0.8/0.9/0.7).
    assert s.magnitude == 0.6
    assert s.evidence_against_null == 0.6
    assert s.world_contact == 0.6
    assert s.certainty == 0.6
    # theory axes untouched.
    assert s.severity == _PROVISIONAL_STRENGTH.severity
    assert s.explanatory_virtue == _PROVISIONAL_STRENGTH.explanatory_virtue


def test_wet_lab_anchor_caps_higher_than_public():
    profile = load_profile("pinned_design_epicv2_hg38_v1", "1")
    claim = _run_with(profile, "wet_lab_anchor")
    assert claim.status == Status.LICENSED
    # ANCHORED ceiling = 0.85; magnitude 0.8 <= 0.85 so it is UNCAPPED (stays 0.8),
    # world_contact 0.9 caps DOWN to 0.85.
    assert claim.strength.magnitude == 0.8
    assert claim.strength.world_contact == 0.85
    # the other two goodness empirical axes are below 0.85 -> uncapped (unchanged).
    assert claim.strength.certainty == _PROVISIONAL_STRENGTH.certainty
    assert claim.strength.evidence_against_null == _PROVISIONAL_STRENGTH.evidence_against_null
