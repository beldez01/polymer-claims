"""all_mechanism_markers: the VOLUME path — mirrors rank_mechanism_opportunities's per-drug
mechanism gene set/min_lines/columns exactly, but emits one row per (drug, gene) sensitivity-
direction eval instead of collapsing to the single best marker per drug."""
from __future__ import annotations

import pandas as pd

from polymer_claims.strata.mechanism import all_mechanism_markers, rank_mechanism_opportunities

_TISSUES = ("a", "b", "c")
_N_PER_TISSUE = 20  # >= MIN_TISSUE_N so every tissue survives eval_gene's per-tissue filter


def _synthetic_inputs():
    lines, tissue_of, meth_g1, meth_g2, auc = [], {}, {}, {}, {}
    for t in _TISSUES:
        for i in range(_N_PER_TISSUE):
            ln = f"{t}{i}"
            lines.append(ln)
            tissue_of[ln] = t
            m = i / (_N_PER_TISSUE - 1)          # 0.0 .. 1.0, evenly spaced within the tissue
            meth_g1[ln] = m
            meth_g2[ln] = m
            auc[ln] = 1.0 - 0.6 * m               # high methylation -> lower AUC -> sensitivity

    meth = pd.DataFrame({"G1": meth_g1, "G2": meth_g2})
    meth.index.name = "COSMIC_ID"

    drug = pd.DataFrame({
        "COSMIC_ID": lines,
        "drug_name": ["D1"] * len(lines),
        "auc": [auc[ln] for ln in lines],
    })

    ann = pd.DataFrame({"tissue": tissue_of})
    ann.index.name = "COSMIC_ID"

    meta = pd.DataFrame([
        {"DRUG_NAME": "D1", "PUTATIVE_TARGET": "G1, G2", "PATHWAY_NAME": "Unknown pathway"},
    ])
    return meth, drug, ann, meta


def test_all_mechanism_markers_emits_one_row_per_drug_gene():
    meth, drug, ann, meta = _synthetic_inputs()

    res = all_mechanism_markers(meth, drug, ann, meta, min_lines=50)

    assert len(res) == 2                              # both G1 and G2 are sensitivity-direction hits
    assert set(res["drug"]) == {"D1"}
    assert set(res["marker"]) == {"G1", "G2"}
    assert (res["r_adj"] < 0).all()
    assert (res["n_genes_tested"] == 2).all()          # honest per-drug cardinality, shared across rows
    assert list(res.columns) == [
        "drug", "pathway", "marker", "level", "r_adj", "rho_pooled",
        "p_adj", "retained", "within_sig", "n_tissues", "n_genes_tested",
    ]


def test_all_mechanism_markers_columns_match_rank_mechanism_opportunities():
    meth, drug, ann, meta = _synthetic_inputs()

    best = rank_mechanism_opportunities(meth, drug, ann, meta, min_lines=50)
    full = all_mechanism_markers(meth, drug, ann, meta, min_lines=50)

    assert list(best.columns) == list(full.columns)
    # the single best row rank_mechanism_opportunities kept must be present among the full rows
    assert len(best) == 1
    best_row = best.iloc[0]
    match = full[(full["drug"] == best_row["drug"]) & (full["marker"] == best_row["marker"])]
    assert len(match) == 1
    assert match.iloc[0]["r_adj"] == best_row["r_adj"]
