"""Phase 2d-iii — end-to-end two-cohort REPLICATED license through run_cycle (planted fixtures)."""
from __future__ import annotations

import pytest

from polymer_grammar import FDRLedger, IndependenceTier, Status
from polymer_protocol import Corpus

from polymer_claims import contracts as _c
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract
from polymer_claims.expression_floor_adapters import expression_floor_claim
from polymer_claims.expression_floor_populate import (
    preregister, license_replicated, check_controls,
)


def _build(out_dir, stem):
    pos = {f"{stem}p{i}": 80.0 + i for i in range(10)}          # RUNX1T1 fusion+ well above 13
    neg = {f"{stem}n{i}": 0.0 + 0.01 * i for i in range(40)}
    fusion = {**{k: "fusion_pos" for k in pos}, **{k: "fusion_neg" for k in neg}}
    tpm = {"RUNX1T1": {**pos, **neg}, "ACTB": {k: 3000.0 for k in fusion}}  # ACTB high in BOTH
    build_fusion_expr_contract(tpm, fusion, {k: "" for k in fusion},
                               genes=["RUNX1T1", "ACTB"], out_dir=out_dir, uid_stem=f"{stem}_fx")
    return f"se:{stem}_fx@1"


def _claims(ref_a):
    return [
        expression_floor_claim("floor-RUNX1T1", ref=ref_a, gene="RUNX1T1", floor=13.0, tissue="AML",
                               search_cardinality=1),
        expression_floor_claim("floor-ACTB", ref=ref_a, gene="ACTB", floor=13.0, tissue="AML",
                               search_cardinality=1),
    ]


def test_two_cohort_disjoint_licenses_at_replicated(tmp_path):
    ref_a, ref_b = _build(tmp_path, "acoh"), _build(tmp_path, "bcoh")
    _c.clear_contract_cache()
    with _c.using_contract_root(tmp_path):
        claims = _claims(ref_a)
        corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
        out = license_replicated(corpus, claims, ref_a=ref_a, ref_b=ref_b,
                                 factors_a=("adult-aml",), factors_b=("peds-aml",))
    by = out.by_id()
    runx = by["floor-RUNX1T1"]
    assert runx.status is Status.LICENSED
    assert runx.licensing.independence_tier is IndependenceTier.REPLICATED
    # ACTB control: clears the floor in both cohorts but ~0 discrimination -> not licensed.
    assert by["floor-ACTB"].status is not Status.LICENSED
    assert check_controls(out, positive="floor-RUNX1T1", negative="floor-ACTB")["ok"] is True
    # ONE e-LOND test per claim (the product is one test, not two).
    assert out.fdr_ledger.n_discoveries == 1


def test_shared_cause_does_not_replicate(tmp_path):
    ref_a, ref_b = _build(tmp_path, "acoh"), _build(tmp_path, "bcoh")
    _c.clear_contract_cache()
    with _c.using_contract_root(tmp_path):
        claims = _claims(ref_a)
        corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
        out = license_replicated(corpus, claims, ref_a=ref_a, ref_b=ref_b,
                                 factors_a=("shared",), factors_b=("shared",))  # Jaccard 1.0
    # overlap ⇒ no e-value multiply ⇒ not REPLICATED (single-cohort e alone may still clear -> REPRODUCED,
    # or stay PENDING; either way NOT the REPLICATED tier).
    assert out.by_id()["floor-RUNX1T1"].licensing is None or \
        out.by_id()["floor-RUNX1T1"].licensing.independence_tier is not IndependenceTier.REPLICATED


def test_empty_factors_rejected(tmp_path):
    ref_a, ref_b = _build(tmp_path, "acoh"), _build(tmp_path, "bcoh")
    _c.clear_contract_cache()
    with _c.using_contract_root(tmp_path):
        claims = _claims(ref_a)
        corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
        with pytest.raises(ValueError, match="non-empty"):
            license_replicated(corpus, claims, ref_a=ref_a, ref_b=ref_b,
                               factors_a=(), factors_b=("peds",))
