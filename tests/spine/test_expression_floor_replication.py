"""Phase 2d-iii — the expression-floor §2E replication builder: cohort-B air-gap + product e-value,
gated by error-independence (disjoint shared_cause_factors)."""
from __future__ import annotations

import pytest

from polymer_claims import contracts as _c
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract


def _build(out_dir, stem, *, hi=True):
    pos = {f"{stem}p{i}": (90.0 if hi else 0.1) + i for i in range(8)}
    neg = {f"{stem}n{i}": 0.0 + 0.01 * i for i in range(30)}
    fusion = {**{k: "fusion_pos" for k in pos}, **{k: "fusion_neg" for k in neg}}
    build_fusion_expr_contract({"RUNX1T1": {**pos, **neg}}, fusion, {k: "" for k in fusion},
                               genes=["RUNX1T1"], out_dir=out_dir, uid_stem=f"{stem}_fx")
    return f"se:{stem}_fx@1"


def _claim_and_corpus(ref_a):
    from polymer_protocol.corpus import Corpus
    from polymer_grammar import FDRLedger
    from polymer_claims.expression_floor_adapters import expression_floor_claim
    claim = expression_floor_claim("floor-X", ref=ref_a, gene="RUNX1T1", floor=13.0, tissue="AML",
                                   search_cardinality=1)
    return Corpus(fdr_ledger=FDRLedger(target_fdr=0.05), claims=(claim,))


def _run(tmp_path, *, factors_a, factors_b):
    from polymer_grammar import MaterializationContext
    from polymer_claims.expression_floor_replication import build_expr_replication_inputs
    ref_a = _build(tmp_path, "acoh")
    ref_b = _build(tmp_path, "bcoh")           # both cohorts strong (fusion+ well above 13)
    _c.clear_contract_cache()
    corpus = _claim_and_corpus(ref_a)
    base = MaterializationContext(id="M", api_version="v1", data_version="d1")
    with _c.using_contract_root(tmp_path):
        return build_expr_replication_inputs(corpus, base, bindings={"floor-X": ref_b},
                                             factors_a=factors_a, factors_b=factors_b)


def test_disjoint_strong_cohortB_counts_and_multiplies(tmp_path):
    ri = _run(tmp_path, factors_a=("acoh-adult",), factors_b=("bcoh-peds",))
    assert "floor-X" in ri.replications                       # cohort B air-gapped -> counts
    assert ri.evidence["floor-X"] > 1.0                       # independent -> product e1*e2


def test_overlapping_factors_do_not_multiply(tmp_path):
    disjoint = _run(tmp_path / "d", factors_a=("adult",), factors_b=("peds",))
    overlap = _run(tmp_path / "o", factors_a=("shared",), factors_b=("shared",))  # Jaccard 1.0
    # cohort B still air-gaps (present in replications), but the e-value is NOT multiplied when the
    # cohorts share cause -> overlap keeps e1 alone, strictly less than the disjoint product.
    assert "floor-X" in overlap.replications
    assert overlap.evidence["floor-X"] < disjoint.evidence["floor-X"]


def test_empty_factors_rejected(tmp_path):
    with pytest.raises(ValueError, match="non-empty"):
        _run(tmp_path, factors_a=(), factors_b=("peds",))
