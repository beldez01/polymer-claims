"""Task 6: license the batch via run_cycle at the REPRODUCED tier.

A synthetic gdsc_pharmaco contract carries two (marker, drug) pairs in ONE cohort:
- pgx-G1-D1: a STRONG planted signal (high-meth lines sensitive in both tissues, ~0.5 AUC gap)
  -> e-value >> the e-LOND first-test threshold (~32.9) AND both independent legs satisfy the
  criterion -> LICENSED. Single cohort -> IndependenceTier.REPRODUCED.
- pgx-G2-D2: a WEAK residue (tiny ~0.02 AUC gap): both legs still satisfy the GT-0 criterion (so
  it is NOT terminal-rejected via agreed refutation), but the e-value stays well below the
  discovery threshold -> stays PENDING (residue).

Tier-trap regression: with shared_cause_factors=() the signal's tier must NOT be REPLICATED — a
single-cohort license never launders to REPLICATED, and empty factors must never mint it either.
"""
from __future__ import annotations

import pandas as pd
from polymer_grammar import FDRLedger, Status
from polymer_grammar.licensing import IndependenceTier
from polymer_protocol import Corpus

from polymer_claims import contracts
from polymer_claims.ingest.gdsc_pharmaco import build_pharmaco_contract
from polymer_claims.strata_populate import license_batch, preregister, propose_claims

_REF = "se:gdsc_pharmaco@1"
_CHEBI = {
    "D1": "http://purl.obolibrary.org/obo/CHEBI_1",
    "D2": "http://purl.obolibrary.org/obo/CHEBI_2",
}
_SHARED_CAUSE = (
    "gdsc2-manifest", "gdsc-imputed-normalization", "hg38",
    "cell-model-passports", "scipy-statsmodels",
)


def _build_contract(out_dir):
    """Two markers, two drugs, 40 lines across two tissues. G1~D1 strong; G2~D2 weak residue."""
    lines = [f"L{i}" for i in range(40)]
    tissue = {ln: ("a" if i < 20 else "b") for i, ln in enumerate(lines)}
    meth = {ln: (0.1 if i % 2 == 0 else 0.9) for i, ln in enumerate(lines)}
    betas = {"G1": dict(meth), "G2": dict(meth)}
    # signal: high-meth (odd) lines are sensitive (AUC 0.4), low-meth (even) resistant (AUC 0.9)
    auc_d1 = {ln: (0.9 if i % 2 == 0 else 0.4) for i, ln in enumerate(lines)}
    # residue: same split direction but a tiny 0.02 gap -> both legs satisfy, e-value stays low
    auc_d2 = {ln: (0.71 if i % 2 == 0 else 0.69) for i, ln in enumerate(lines)}
    aucs = {"D1": auc_d1, "D2": auc_d2}
    return build_pharmaco_contract(
        betas, aucs, tissue, genes=["G1", "G2"], drugs=["D1", "D2"], out_dir=out_dir)


def _propose():
    res = pd.DataFrame([
        {"drug": "D1", "marker": "G1", "n_genes_tested": 5},
        {"drug": "D2", "marker": "G2", "n_genes_tested": 5},
    ])
    return propose_claims(res, ref=_REF, chebi_of=_CHEBI)


def _run(tmp_path, shared_cause_factors):
    _build_contract(tmp_path)
    contracts.clear_contract_cache()
    with contracts.using_contract_root(tmp_path):
        claims = _propose()
        corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
        out = license_batch(
            corpus, claims, ref=_REF, shared_cause_factors=shared_cause_factors)
    contracts.clear_contract_cache()
    return out


def test_signal_licenses_reproduced_null_pending(tmp_path):
    out = _run(tmp_path, _SHARED_CAUSE)
    by_id = {c.id: c for c in out.claims}

    signal = by_id["pgx-G1-D1"]
    residue = by_id["pgx-G2-D2"]

    assert signal.status == Status.LICENSED
    assert residue.status == Status.PENDING          # residue, NOT terminal-rejected
    assert residue.status != Status.REJECTED

    lic = signal.licensing
    assert lic is not None
    assert lic.independence_tier == IndependenceTier.REPRODUCED


def test_empty_shared_cause_never_mints_replicated(tmp_path):
    out = _run(tmp_path, ())
    signal = {c.id: c for c in out.claims}["pgx-G1-D1"]
    assert signal.status == Status.LICENSED
    # tier-trap: empty factors must never launder a single-cohort license to REPLICATED.
    assert signal.licensing.independence_tier != IndependenceTier.REPLICATED
