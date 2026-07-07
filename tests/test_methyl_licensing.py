from __future__ import annotations

from polymer_grammar import FDRLedger, MaterializationContext, StrengthVector
from polymer_protocol import AdapterCredential, AdapterRegistry, Corpus, run_cycle

from polymer_claims.analysis_profile import profile_oracle_registry
from polymer_claims.capabilities import CAPABILITY_CELLS
from polymer_claims.methyl_adapters import (
    RegionHodgesLehmannAdapter, RegionMeanDiffAdapter, methyl_independent_registry, region_delta_beta_claim,
)
from polymer_claims.profiles import CANONICAL_EPICV2_V1

_ADAPTERS = (RegionMeanDiffAdapter(), RegionHodgesLehmannAdapter())
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="epicv2_casectrl_demo@1")
_CONTROL = ("cg00000006", "cg00000007", "cg00000008", "cg00000009", "cg00000010")
_CONTROL_REGION = ("chr1", 1_001_000, 1_001_800)

_STR = StrengthVector(magnitude=0.8, certainty=0.7, evidence_against_null=0.8,
                      severity=0.5, world_contact=0.9, explanatory_virtue=0.6)


def _corpus(claim):
    return Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))


def _claim(result, cid):
    return next(c for c in result.corpus.claims if c.id == cid)


def _oracles():
    return profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public"))


def test_true_region_claim_licenses_on_computed_delta_beta():
    c = region_delta_beta_claim("c-true", threshold=0.10)
    result = run_cycle(_corpus(c), _ADAPTERS, _CTX,
                       adapter_registry=methyl_independent_registry(), oracles=_oracles(),
                       capability_registry=CAPABILITY_CELLS)
    assert _claim(result, "c-true").status.value == "licensed"


def test_negative_control_region_does_not_license():
    c = region_delta_beta_claim("c-ctrl", region_probes=_CONTROL, region=_CONTROL_REGION, threshold=0.10)
    result = run_cycle(_corpus(c), _ADAPTERS, _CTX,
                       adapter_registry=methyl_independent_registry(), oracles=_oracles(),
                       capability_registry=CAPABILITY_CELLS)
    assert _claim(result, "c-ctrl").status.value != "licensed"


def test_apparatus_tier_caps_strength_to_0_6():
    c = region_delta_beta_claim("c-cap", threshold=0.10, strength=_STR)
    result = run_cycle(_corpus(c), _ADAPTERS, _CTX,
                       adapter_registry=methyl_independent_registry(), oracles=_oracles(),
                       capability_registry=CAPABILITY_CELLS)
    lic = _claim(result, "c-cap")
    assert lic.status.value == "licensed"
    assert lic.strength.magnitude == 0.6
    assert lic.strength.world_contact == 0.6
    assert lic.strength.evidence_against_null == 0.6


def test_air_gap_holds_non_independent_pair_pending():
    c = region_delta_beta_claim("c-dep", threshold=0.10)
    same_owner = AdapterRegistry(credentials=(
        AdapterCredential(identity="methyl-meandiff-beta", owner="same", implementation_hash="h1"),
        AdapterCredential(identity="methyl-hodges-lehmann", owner="same", implementation_hash="h2"),
    ))
    result = run_cycle(_corpus(c), _ADAPTERS, _CTX, adapter_registry=same_owner, oracles=_oracles(),
                       capability_registry=CAPABILITY_CELLS)
    assert _claim(result, "c-dep").status.value == "pending"


def test_subjectless_claim_resolves_out_of_domain_to_zero_strength():
    c = region_delta_beta_claim("c-nosub", threshold=0.10, strength=_STR, with_subject=False)
    result = run_cycle(_corpus(c), _ADAPTERS, _CTX,
                       adapter_registry=methyl_independent_registry(), oracles=_oracles(),
                       capability_registry=CAPABILITY_CELLS)
    lic = _claim(result, "c-nosub")
    assert lic.strength.magnitude == 0.0
