"""Phase 2e — the CBF 2x2 fusion-marker family + cross-fusion specificity (planted 3-group fixtures).

The family licenses via REPLICATION: with 5 pre-registered claims the e-LOND bars are front-loaded
(32.9, 131, 296, ...), so single-cohort e-values clear only the first; the two-cohort product clears all.
"""
from __future__ import annotations

from polymer_grammar import FDRLedger, IndependenceTier, QuantityLeaf, Status
from polymer_protocol import Corpus

from polymer_claims import contracts as _c
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract
from polymer_claims.expression_floor_adapters import expression_floor_claim
from polymer_claims.expression_floor_populate import (
    preregister, license_batch, license_replicated, check_controls, propose_cbf_family_claims,
)


def _cbf_contract(out_dir, stem):
    """t821 (RUNX1T1 high, MN1 low), inv16 (MN1 high, RUNX1T1 low), other (both low); ACTB high all."""
    grp = {}
    tpm = {"RUNX1T1": {}, "MN1": {}, "ACTB": {}}
    for i in range(10):
        grp[f"{stem}t{i}"] = "t821"
        tpm["RUNX1T1"][f"{stem}t{i}"] = 90.0 + i
        tpm["MN1"][f"{stem}t{i}"] = 2.0
        grp[f"{stem}i{i}"] = "inv16"
        tpm["RUNX1T1"][f"{stem}i{i}"] = 0.1
        tpm["MN1"][f"{stem}i{i}"] = 90.0 + i
    for i in range(20):
        grp[f"{stem}o{i}"] = "other"
        tpm["RUNX1T1"][f"{stem}o{i}"] = 0.05
        tpm["MN1"][f"{stem}o{i}"] = 2.0
    for k in grp:
        tpm["ACTB"][k] = 3000.0
    build_fusion_expr_contract(tpm, grp, {k: "" for k in grp}, genes=["RUNX1T1", "MN1", "ACTB"],
                               out_dir=out_dir, uid_stem=f"{stem}_cbf")
    return f"se:{stem}_cbf@1"


def test_family_builds():
    claims = propose_cbf_family_claims("se:x@1")
    assert [c.id for c in claims] == [
        "floor-RUNX1T1-t821-vs-other", "floor-MN1-inv16-vs-other",
        "floor-RUNX1T1-t821-vs-inv16", "floor-MN1-inv16-vs-t821", "floor-ACTB-inv16-vs-other"]
    for c in claims:
        assert c.status is Status.PENDING   # recompute claims are PENDING until run_cycle licenses
        assert isinstance(c.leaves[0], QuantityLeaf) and c.leaves[0].value == 13.0 and c.leaves[0].low == 13.0


def test_planted_family_licenses_replicated_with_specificity(tmp_path):
    ref_a = _cbf_contract(tmp_path, "acoh")
    ref_b = _cbf_contract(tmp_path, "bcoh")
    _c.clear_contract_cache()
    with _c.using_contract_root(tmp_path):
        claims = propose_cbf_family_claims(ref_a)
        corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
        out = license_replicated(corpus, claims, ref_a=ref_a, ref_b=ref_b,
                                 factors_a=("adult-aml",), factors_b=("peds-aml",))
    by = out.by_id()
    for cid in ("floor-RUNX1T1-t821-vs-other", "floor-MN1-inv16-vs-other",
                "floor-RUNX1T1-t821-vs-inv16", "floor-MN1-inv16-vs-t821"):
        c = by[cid]
        assert c.status is Status.LICENSED, f"{cid} did not license"
        assert c.licensing.independence_tier is IndependenceTier.REPLICATED
    assert by["floor-ACTB-inv16-vs-other"].status is not Status.LICENSED   # control
    assert check_controls(out, positive="floor-MN1-inv16-vs-other",
                          negative="floor-ACTB-inv16-vs-other")["ok"] is True


def test_specificity_reverse_claim_does_not_license(tmp_path):
    ref = _cbf_contract(tmp_path, "one")
    _c.clear_contract_cache()
    with _c.using_contract_root(tmp_path):
        # RUNX1T1 is HIGH in t821, ~0 in inv16 — so "high in inv16 vs t821" must NOT license (criterion fails).
        reverse = expression_floor_claim("floor-RUNX1T1-inv16-vs-t821", ref=ref, gene="RUNX1T1",
                                         floor=13.0, tissue="AML", level_a="inv16", level_b="t821",
                                         search_cardinality=1)
        corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), [reverse])
        out = license_batch(corpus, [reverse], ref=ref)
    assert out.by_id()["floor-RUNX1T1-inv16-vs-t821"].status is not Status.LICENSED
