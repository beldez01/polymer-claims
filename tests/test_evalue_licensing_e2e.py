# tests/test_evalue_licensing_e2e.py
from __future__ import annotations

from polymer_grammar import FDRLedger, MaterializationContext, Status
from polymer_protocol import Corpus, run_cycle

from polymer_claims.analysis_profile import profile_oracle_registry
from polymer_claims.evidence import evidence_map
from polymer_claims.methyl_adapters import (
    RegionLmCoefAdapter, RegionMeanDiffAdapter, methyl_independent_registry, region_delta_beta_claim,
)
from polymer_claims.profiles import CANONICAL_EPICV2_V1

_ADAPTERS = (RegionMeanDiffAdapter(), RegionLmCoefAdapter())
_BASE = MaterializationContext(id="M", api_version="v1", data_version="d1")
_POWERED = "se:epicv2_casectrl_powered@1"
_STRONG = ("cg00000001", "cg00000002", "cg00000003", "cg00000004", "cg00000005")
_WEAK = ("cg00000006", "cg00000007", "cg00000008", "cg00000009", "cg00000010")


def _run(claim):
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    return run_cycle(
        corpus, _ADAPTERS, _BASE,
        adapter_registry=methyl_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
        evidence=evidence_map(corpus),
    )


def test_well_powered_region_licenses_via_e_discovery():
    claim = region_delta_beta_claim("c-strong", ref=_POWERED, region_probes=_STRONG, threshold=0.10)
    result = _run(claim)
    c = next(x for x in result.corpus.claims if x.id == "c-strong")
    assert c.status == Status.LICENSED
    assert result.corpus.fdr_ledger.n_discoveries == 1


def test_point_significant_but_weak_evidence_is_blocked():
    # THE RIGOR MONEY-SHOT: point estimate (~0.12) CLEARS the 0.10 criterion (SATISFIED + agreed +
    # grounded -> would license under the old 3-way gate), but the severe-test e-value is below the
    # e-LOND bar, so the 4-way gate withholds the license. Corpus error control working.
    claim = region_delta_beta_claim("c-weak", ref=_POWERED, region_probes=_WEAK, threshold=0.10)
    result = _run(claim)
    c = next(x for x in result.corpus.claims if x.id == "c-weak")
    assert c.status != Status.LICENSED
    assert result.corpus.fdr_ledger.n_tests == 1
    assert result.corpus.fdr_ledger.n_discoveries == 0
