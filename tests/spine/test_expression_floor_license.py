"""Task 4: e2e license test for the expression-floor spine + ACTB control + floor-robustness sweep.
Mirrors tests/pharmaco/test_pharmaco_license.py. Synthetic contract: RUNX1T1 planted strong
(fusion+ >> 13, fusion- ~= 0) -> LICENSED; ACTB high in BOTH groups (~3000, clears floor everywhere,
no discrimination gap) -> NOT LICENSED (the load-bearing proof the floor-criterion and the
discrimination e-value stayed mechanistically separate)."""
from __future__ import annotations

from polymer_claims import contracts as _c
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract
from polymer_grammar import FDRLedger, Status
from polymer_protocol import Corpus


def _contract(tmp_path):
    # 12 fusion+ samples (not 8): the betting e-value needs enough fusion+ replicates to clear the
    # e-LOND first-test discovery bar (~32.9); 8 samples lands at e~27 (just short), 12 lands at
    # e~175 (comfortably clears). Values start at 95 (not 80) so the mean/HL (~100.5) still clears
    # the robustness sweep's highest floor (90 TPM). Strengthening the fixture, not the criterion.
    pos = {f"p{i}": 95.0 + i for i in range(12)}
    neg = {f"n{i}": 0.0 + 0.01 * i for i in range(40)}
    fusion = {**{k: "fusion_pos" for k in pos}, **{k: "fusion_neg" for k in neg}}
    tpm = {
        "RUNX1T1": {**pos, **neg},
        "ACTB":    {k: 3000.0 for k in fusion},   # high in BOTH -> clears 13 everywhere, no gap
    }
    build_fusion_expr_contract(tpm, fusion, {k: "" for k in fusion},
                               genes=["RUNX1T1", "ACTB"], out_dir=tmp_path)
    _c.clear_contract_cache()
    return "se:tcga_laml_fusion_expr@1"


def test_signal_licenses_reproduced_housekeeping_pending(tmp_path):
    from polymer_claims.expression_floor_populate import preregister, license_batch, check_controls, propose_spine_claims
    ref = _contract(tmp_path)
    with _c.using_contract_root(tmp_path):
        claims = propose_spine_claims(ref)                    # [floor-RUNX1T1, floor-ACTB]
        corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
        out = license_batch(corpus, claims, ref=ref)
    by = out.by_id()
    assert by["floor-RUNX1T1"].status is Status.LICENSED
    assert by["floor-ACTB"].status is not Status.LICENSED    # clears floor but no discrimination
    rep = check_controls(out, positive="floor-RUNX1T1", negative="floor-ACTB")
    assert rep["ok"] is True


def test_floor_robustness_sweep(tmp_path):
    from polymer_claims.expression_floor_populate import preregister, license_batch, propose_spine_claims
    ref = _contract(tmp_path)
    for floor in (1.0, 5.0, 13.0, 50.0, 90.0):
        with _c.using_contract_root(tmp_path):
            claims = propose_spine_claims(ref, floor=floor)
            corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
            out = license_batch(corpus, claims, ref=ref)
        assert out.by_id()["floor-RUNX1T1"].status is Status.LICENSED, f"floor={floor} flipped the verdict"
