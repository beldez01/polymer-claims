"""e2e license test for the expression::absence safety-veto spine (Ch2 GTEx safety atlas).

Synthetic atlas: SAFEG absent across every tissue -> LICENSED (safe). ACTB broadly expressed
(3000 TPM) -> NOT LICENSED (the max leg's LE criterion vetoes). SPIKE absent except one high tissue
-> NOT LICENSED (the worst-tissue veto — the load-bearing safety property). Mirrors
tests/spine/test_expression_floor_license.py.
"""
from __future__ import annotations

from polymer_grammar import FDRLedger, Status
from polymer_protocol import Corpus

from polymer_claims import contracts as _c
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract

_CEILING = 13.0


def _atlas(tmp_path):
    tissues = [f"t{i}" for i in range(40)]
    tpm = {
        "SAFEG": {t: 0.01 * i for i, t in enumerate(tissues)},        # absent everywhere (~0-0.4 TPM)
        "ACTB":  {t: 3000.0 for t in tissues},                        # broadly expressed -> vetoed
        "SPIKE": {t: (3000.0 if i == 7 else 0.05) for i, t in enumerate(tissues)},  # one hot tissue
    }
    grp = {t: "healthy" for t in tissues}
    build_fusion_expr_contract(tpm, grp, {t: "" for t in tissues},
                               genes=["SAFEG", "ACTB", "SPIKE"], out_dir=tmp_path)
    _c.clear_contract_cache()
    return "se:tcga_laml_fusion_expr@1"


def test_absent_target_licenses_expressed_target_vetoed(tmp_path):
    from polymer_claims.expression_absence_populate import (
        check_controls, license_batch, preregister, propose_safety_claims,
    )
    ref = _atlas(tmp_path)
    with _c.using_contract_root(tmp_path):
        claims = propose_safety_claims(ref, ceiling=_CEILING)
        corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
        out = license_batch(corpus, claims, ref=ref)
    by = out.by_id()
    assert by["absence-SAFEG"].status is Status.LICENSED
    assert by["absence-ACTB"].status is not Status.LICENSED       # broadly expressed -> not safe
    rep = check_controls(out, positive="absence-SAFEG", negative="absence-ACTB")
    assert rep["ok"] is True


def test_single_high_tissue_vetoes_the_target(tmp_path):
    from polymer_claims.expression_absence_adapters import expression_absence_claim
    from polymer_claims.expression_absence_populate import license_batch, preregister
    ref = _atlas(tmp_path)
    with _c.using_contract_root(tmp_path):
        claims = [expression_absence_claim("absence-SPIKE", ref=ref, gene="SPIKE",
                                           ceiling=_CEILING, search_cardinality=1)]
        corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
        out = license_batch(corpus, claims, ref=ref)
    # Absent in 39/40 tissues, but one tissue at 3000 TPM -> max > ceiling -> the veto fires.
    assert out.by_id()["absence-SPIKE"].status is not Status.LICENSED
