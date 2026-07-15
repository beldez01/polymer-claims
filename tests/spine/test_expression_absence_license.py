"""e2e license test for the expression::absence safety-veto spine (Ch2 GTEx safety atlas).

Synthetic atlas: SAFEG absent across every tissue -> LICENSED (safe). ACTB broadly expressed
(3000 TPM) -> NOT LICENSED (the max leg's LE criterion vetoes). SPIKE absent except one high tissue
-> NOT LICENSED (the worst-tissue veto — the load-bearing safety property). Mirrors
tests/spine/test_expression_floor_license.py.
"""
from __future__ import annotations

from polymer_grammar import FDRLedger, PendingReason, Status
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
    # AUDIT finding 1: the refuted claim must NOT become a live FDR discovery (else it inflates the
    # e-LOND budget). The worst-tissue-aware e-value returns 0 -> discovery=False.
    spike_test = next(t for t in out.fdr_ledger.tests if t.claim_id == "absence-SPIKE")
    assert spike_test.discovery is False
    assert out.fdr_ledger.n_discoveries == 0


def test_truncated_contract_surfaces_as_execution_error(tmp_path):
    # AUDIT (final): a corrupt/truncated contract must report EXECUTION_ERROR, not masquerade as an
    # UNTESTED claim that hides the data corruption.
    ref = _atlas(tmp_path)
    betas = tmp_path / "tcga_laml_fusion_expr.betas.tsv"        # _atlas builds under this uid
    lines = betas.read_text().splitlines()
    lines[1] = "\t".join(lines[1].split("\t")[:-1])             # drop the last cell of the first gene row
    betas.write_text("\n".join(lines) + "\n")
    _c.clear_contract_cache()
    from polymer_claims.expression_absence_adapters import expression_absence_claim
    from polymer_claims.expression_absence_populate import license_batch, preregister
    with _c.using_contract_root(tmp_path):
        claims = [expression_absence_claim("absence-SAFEG", ref=ref, gene="SAFEG",
                                           ceiling=_CEILING, search_cardinality=1)]
        out = license_batch(preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims), claims, ref=ref)
    c = out.by_id()["absence-SAFEG"]
    assert c.status is not Status.LICENSED
    assert c.pending_reason is PendingReason.EXECUTION_ERROR
