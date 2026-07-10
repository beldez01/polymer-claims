"""Task 7: the control instrument + publish guard.

check_controls is a READ-ONLY instrument, not a gate — verified by asserting no claim's status
changes across a call. populate_universe wires propose -> preregister -> license_batch ->
check_controls end-to-end and raises ControlCheckFailed when require_controls=True and the
positive control did not license."""
from __future__ import annotations

import pandas as pd
import pytest
from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    FDRLedger,
    PatternRef,
    PendingReason,
    Status,
)
from polymer_protocol import Corpus

from polymer_claims import contracts
from polymer_claims.ingest.gdsc_pharmaco import build_pharmaco_contract
from polymer_claims.strata_populate import (
    ControlCheckFailed,
    check_controls,
    populate_universe,
)

_REF = "se:gdsc_pharmaco@1"
_CHEBI = {"Palbociclib": "http://purl.obolibrary.org/obo/CHEBI_85993"}
_SHARED_CAUSE = (
    "gdsc2-manifest", "gdsc-imputed-normalization", "hg38",
    "cell-model-passports", "scipy-statsmodels",
)


def _build_weak_positive_contract(out_dir):
    """MTAP~Palbociclib as a weak residue (tiny AUC gap): both legs still satisfy the GT-0
    criterion (not terminal-rejected) but the e-value stays well below the discovery threshold,
    so the claim stays PENDING and the positive control never licenses. Mirrors the residue
    construction in test_strata_license.py."""
    lines = [f"L{i}" for i in range(40)]
    tissue = {ln: ("a" if i < 20 else "b") for i, ln in enumerate(lines)}
    meth = {ln: (0.1 if i % 2 == 0 else 0.9) for i, ln in enumerate(lines)}
    betas = {"MTAP": dict(meth)}
    auc = {ln: (0.71 if i % 2 == 0 else 0.69) for i, ln in enumerate(lines)}
    return build_pharmaco_contract(
        betas, {"Palbociclib": auc}, tissue,
        genes=["MTAP"], drugs=["Palbociclib"], out_dir=out_dir)


def test_publish_guard_raises_when_positive_control_fails(tmp_path):
    _build_weak_positive_contract(tmp_path)
    contracts.clear_contract_cache()
    res = pd.DataFrame([
        {"drug": "Palbociclib", "marker": "MTAP", "n_genes_tested": 5},
    ])
    try:
        with contracts.using_contract_root(tmp_path), pytest.raises(ControlCheckFailed):
            populate_universe(
                res, ref=_REF, chebi_of=_CHEBI,
                shared_cause_factors=_SHARED_CAUSE, require_controls=True)
    finally:
        contracts.clear_contract_cache()


def test_check_controls_changes_no_status():
    pattern = PatternRef(id="adjusted_effect", version="v1")
    licensed = Claim(
        id="pgx-MTAP-Palbociclib", title="MTAP ~ Palbociclib", pattern=pattern,
        leaves=(CategoricalLeaf(ontology_term="pharmacogenomic_association"),),
        status=Status.LICENSED)
    residue = Claim(
        id="pgx-MGMT-Temozolomide", title="MGMT ~ Temozolomide", pattern=pattern,
        leaves=(CategoricalLeaf(ontology_term="pharmacogenomic_association"),),
        status=Status.PENDING, pending_reason=PendingReason.UNTESTED)
    corpus = Corpus(claims=(licensed, residue), fdr_ledger=FDRLedger(target_fdr=0.05))

    before = {c.id: c.status for c in corpus.claims}
    report = check_controls(corpus)
    after = {c.id: c.status for c in corpus.claims}

    assert before == after   # instrument, not a gate
    assert report == {"ok": True, "positive_licensed": True, "negative_licensed": False}
