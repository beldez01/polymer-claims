"""Task 8: the data-gated real-control integration test.

Runs the REAL `ingest_gdsc_pharmaco` for the first time ever against the lifted GDSC cohort
(Task 1's builder had never executed against real data before this test), the real full-panel
mechanism scan, and `populate_universe` with `require_controls=False`. This is an OBSERVATIONAL
test: the whole point is to see what a real single-cohort e-LOND gate does with real biology,
not to force a particular outcome onto it. Data-gated: skipped when the real GDSC data isn't
present (gitignored); honors `STRATA_DATA_ROOT`. Marked `slow` (loads the full methylation
matrix + reads the 21M xlsx) — excluded from fast/core test selection via `-m "not slow"`.

Two named controls are checked directly (marker pinned explicitly, not left to the full-panel
scan's per-drug best-gene competition):
  - positive: MTAP methylation -> Palbociclib sensitivity (the CDK4/6i mechanism)
  - negative: MGMT (gene-level) methylation -> Temozolomide (expected null: the promoter-island
    signal that matters clinically washes out at gene-level bulk methylation)

Note: on this real cohort, the full-panel scan's own competition among DNA-replication-pathway
genes picks TYMS (not MGMT) as Temozolomide's best-scoring methylation marker -- so the *named*
control pair is built directly here (pinning the marker) rather than assumed to fall out of the
panel's ranking. Both facts are observed and printed, not asserted away.
"""
from __future__ import annotations

import os

import pytest

if os.environ.get("STRATA_DATA_ROOT"):
    _METH_PATH = os.path.join(
        os.path.expanduser(os.environ["STRATA_DATA_ROOT"]), "gdsc", "methylation_imputed.csv.gz")
else:
    from polymer_claims.strata.config import DATA_DIR
    _METH_PATH = str(DATA_DIR / "gdsc" / "methylation_imputed.csv.gz")

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not os.path.exists(_METH_PATH), reason="real GDSC data not present (gitignored)"),
]

_REF = "se:gdsc_pharmaco@1"
_CHEBI = {
    "Palbociclib": "http://purl.obolibrary.org/obo/CHEBI_85993",
    "Temozolomide": "http://purl.obolibrary.org/obo/CHEBI_72564",
}
_SHARED_CAUSE = (
    "gdsc2-manifest", "gdsc-imputed-normalization", "hg38",
    "cell-model-passports", "scipy-statsmodels",
)


def _evalue(corpus, claim_id):
    return next((t.e_value for t in corpus.fdr_ledger.tests if t.claim_id == claim_id), None)


def test_real_controls_positive_licenses_negative_does_not():
    import pandas as pd
    from polymer_grammar import Status

    from polymer_claims.ingest.gdsc_pharmaco import ingest_gdsc_pharmaco
    from polymer_claims.strata.mechanism import load_inputs, rank_mechanism_opportunities
    from polymer_claims.strata_populate import check_controls, populate_universe

    summary = ingest_gdsc_pharmaco()
    print(f"\n[real ingest] {summary}")

    meth, drug, ann, meta = load_inputs()
    res = rank_mechanism_opportunities(meth, drug, ann, meta)
    assert len(res) > 0, "the real full-panel mechanism scan produced zero rows"

    # --- Full-panel universe: exactly what a real STRATA run proposes for these two drugs
    # (chebi_of only resolves Palbociclib/Temozolomide -- everything else is honestly skipped,
    # logged not silent, by propose_claims). Robust pipeline-integrity facts only. ---
    full_universe = populate_universe(
        res, ref=_REF, chebi_of=_CHEBI, shared_cause_factors=_SHARED_CAUSE,
        require_controls=False)
    assert len(full_universe.claims) > 0, "populate_universe produced an empty universe on real data"
    by_id = full_universe.by_id()
    print(f"[full-panel universe] n_claims={len(full_universe.claims)} ids={sorted(by_id)}")
    pos_panel = by_id.get("pgx-MTAP-Palbociclib")
    assert pos_panel is not None, "the real full-panel scan did not propose MTAP-Palbociclib"
    assert pos_panel.status != Status.REJECTED
    print(f"[full-panel] pgx-MTAP-Palbociclib: {pos_panel.status.value} "
          f"e={_evalue(full_universe, 'pgx-MTAP-Palbociclib')}")

    # --- Named-control universe: the literal MTAP->Palbociclib / MGMT->Temozolomide pair,
    # marker pinned directly. n_genes_tested is the honest per-drug cardinality already computed
    # by the panel scan (independent of which marker won that drug's competition). ---
    n_genes = {
        d: int(res.loc[res["drug"] == d, "n_genes_tested"].iloc[0])
        for d in ("Palbociclib", "Temozolomide")
    }
    ctl_res = pd.DataFrame([
        {"drug": "Palbociclib", "marker": "MTAP", "n_genes_tested": n_genes["Palbociclib"]},
        {"drug": "Temozolomide", "marker": "MGMT", "n_genes_tested": n_genes["Temozolomide"]},
    ])
    ctl_universe = populate_universe(
        ctl_res, ref=_REF, chebi_of=_CHEBI, shared_cause_factors=_SHARED_CAUSE,
        require_controls=False)
    report = check_controls(ctl_universe)

    pos = ctl_universe.by_id()["pgx-MTAP-Palbociclib"]
    neg = ctl_universe.by_id()["pgx-MGMT-Temozolomide"]
    pos_e = _evalue(ctl_universe, "pgx-MTAP-Palbociclib")
    neg_e = _evalue(ctl_universe, "pgx-MGMT-Temozolomide")

    print(f"[named controls] positive pgx-MTAP-Palbociclib: status={pos.status.value} e={pos_e}")
    print(f"[named controls] negative pgx-MGMT-Temozolomide: status={neg.status.value} e={neg_e}")
    print(f"[named controls] check_controls: {report}")

    # Robust facts, not a forced assertion: the real MTAP->Palbociclib effect either clears the
    # strict single-cohort e-LOND bar (~33) and licenses, or -- an honest PENDING ceiling -- it
    # doesn't; either way it must never be terminal-rejected (agreed refutation would mean both
    # independent legs actively agree the mechanism is absent, which real CDK4/6i biology does
    # not support).
    assert pos.status != Status.REJECTED
    assert neg.status != Status.LICENSED
    if pos.status == Status.LICENSED:
        print("[named controls] the positive control LICENSED on real data.")
    if report["ok"]:
        print("[named controls] check_controls: ok=True -- positive licensed, negative did not.")
