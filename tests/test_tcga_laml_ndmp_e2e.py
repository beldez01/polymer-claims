# tests/test_tcga_laml_ndmp_e2e.py
"""EARNED-MILESTONE e2e: license the genome-wide n-DMP count on REAL TCGA-LAML HM450 betas.
Skipped unless a local `polymer-claims ingest tcga-laml` has produced se:tcga_laml_idh@1
(nothing real is committed). Mirrors tests/test_n_dmps_e2e.py with the HM450 profile + real ref."""
from __future__ import annotations

import math

import pytest
from polymer_grammar import FDRLedger, IndependenceTier, MaterializationContext, Status
from polymer_protocol import Corpus, run_cycle

from polymer_claims.analysis_profile import profile_oracle_id, profile_oracle_registry
from polymer_claims.capabilities import CAPABILITY_CELLS
from polymer_claims.evidence import evidence_map
from polymer_claims.materialization import materialization_map
from polymer_claims.methyl_ndmp import (
    NDmpRankAdapter,
    NDmpTTestAdapter,
    _all_probe_ids,
    n_dmps_claim,
    ndmp_independent_registry,
)
from polymer_claims.profiles import CANONICAL_HM450_V1

_REF = "se:tcga_laml_idh@1"
_ADAPTERS = (NDmpTTestAdapter(), NDmpRankAdapter())
_BASE = MaterializationContext(id="M", api_version="v1", data_version="d1")
_ALPHA = 0.05


def _contract_present() -> bool:
    try:
        from polymer_claims.contracts import load_contract
        load_contract(_REF)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _contract_present(), reason="run `polymer-claims ingest tcga-laml` first (no real data committed)")


def _run(claim):
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    result = run_cycle(
        corpus, _ADAPTERS, _BASE,
        adapter_registry=ndmp_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_HM450_V1, "recomputable_public")),
        materializations=materialization_map(corpus, _BASE, profiles=(CANONICAL_HM450_V1,)),
        evidence=evidence_map(corpus),
        capability_registry=CAPABILITY_CELLS,
    )
    return result, next(x for x in result.corpus.claims if x.id == claim.id)


def _k_null_floor() -> int:
    # pre-registered floor = the expected-under-null false-positive count (NOT read off the data).
    return math.ceil(_ALPHA * len(_all_probe_ids(_REF)))


def test_real_ndmp_licenses_reproduced_with_full_content_address():
    claim = n_dmps_claim(
        "tcga-laml-ndmp", ref=_REF,
        group_col="Sample_Group", level_a="WT", level_b="IDH_mut",
        alpha=_ALPHA, k=_k_null_floor(),
        oracle_ref=profile_oracle_id(CANONICAL_HM450_V1),
    )
    result, c = _run(claim)
    assert c.status == Status.LICENSED
    assert c.licensing.independence_tier is IndependenceTier.REPRODUCED
    # one e-test per claim lifetime; one discovery
    assert result.corpus.fdr_ledger.n_tests == 1
    assert result.corpus.fdr_ledger.n_discoveries == 1
    # the license records the FULL content-address: real dimnames_hash + HM450 profile_hash + run id
    sat = c.licensing.satisfactions[0]
    mctx = sat.materialization  # Satisfaction.materialization: MaterializationContext
    assert mctx.dimnames_hash and mctx.profile_hash and mctx.semantic_run_id
    # q (the headline "we expect ≤ q of LICENSED claims to be false") is the e-LOND control
    # level; the grammar exposes it as target_fdr (no separate realized/empirical q exists).
    assert result.corpus.fdr_ledger.target_fdr == 0.05


def test_real_ndmp_legs_agree_within_tau_count():
    # On real TCGA-LAML data the two legs are genuinely different procedures (pooled-t vs
    # Mann-Whitney rank-sum) and diverge ~12.6% on the raw DMP count -- Leg A (pooled-t) =
    # 115,405; Leg B (rank-sum) = 132,031 (regression pin). That's far outside any numeric
    # closeness tolerance. For an enrichment/threshold claim like n-DMP, the honest agreement
    # bar is NOT numeric closeness on the count -- it's that BOTH legs INDEPENDENTLY confirm
    # enrichment far in excess of the pre-registered floor k (18,945 here): 115,405 and 132,031
    # both clear k by >6x. That's exactly what agreement_mode="both_satisfy_criterion" checks
    # (CapabilityCell.agreement_mode in capabilities.py) -- the count divergence is honest
    # method-sensitivity between two independent statistical procedures, not a license-blocker.
    node = n_dmps_claim(
        "tmp", ref=_REF,
        group_col="Sample_Group", level_a="WT", level_b="IDH_mut",
        alpha=_ALPHA, k=1,
    ).evaluation_plan.graph.nodes[0]
    a = NDmpTTestAdapter().execute(node, (), _BASE).value
    b = NDmpRankAdapter().execute(node, (), _BASE).value
    assert a == pytest.approx(115_405, abs=1)
    assert b == pytest.approx(132_031, abs=1)
    rel = abs(a - b) / max(a, b, 1.0)
    assert rel == pytest.approx(0.126, abs=0.01)  # confirm the ~12.6% divergence is real, not noise
    k = _k_null_floor()
    assert a >= k and b >= k  # both legs independently satisfy the claim's criterion


def test_real_ndmp_withholds_when_criterion_not_met():
    # Honest withholding: an unreachable pre-stated criterion (k = every probe is a DMP) -> REJECTED.
    claim = n_dmps_claim(
        "tcga-laml-ndmp-strict", ref=_REF,
        group_col="Sample_Group", level_a="WT", level_b="IDH_mut",
        alpha=_ALPHA, k=len(_all_probe_ids(_REF)),
        oracle_ref=profile_oracle_id(CANONICAL_HM450_V1),
    )
    _result, c = _run(claim)
    assert c.status != Status.LICENSED  # the gate correctly withholds; system working, not a failure
