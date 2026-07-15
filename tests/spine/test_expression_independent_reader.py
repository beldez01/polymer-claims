"""Independent leg-B contract reader (audit F3) — genuine data-reading independence.

Leg B reads via `independent_feature_row` (own parser + a TSV<->manifest sample-set integrity check),
so a row/orientation/alignment bug in the shared `_load_betas` can't corrupt both legs identically.
"""
from __future__ import annotations

import pytest
from polymer_grammar import DataHandle, MeasurementBasis, OperationNode, ProducedLeafSpec

from polymer_claims import contracts as _c
from polymer_claims.expression_independent_reader import independent_feature_row
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract


def _contract(tmp_path):
    tpm = {"RUNX1T1": {"p1": 90.0, "p2": 100.0, "n1": 0.0, "n2": 0.2}}
    fusion = {"p1": "fusion_pos", "p2": "fusion_pos", "n1": "fusion_neg", "n2": "fusion_neg"}
    build_fusion_expr_contract(tpm, fusion, {k: "" for k in fusion}, genes=["RUNX1T1"], out_dir=tmp_path)
    _c.clear_contract_cache()
    return "se:tcga_laml_fusion_expr@1"


def _node(ref):
    return OperationNode(
        id="n", impl="expression::floor", inputs=(DataHandle(ref=ref),),
        params=(("gene", "RUNX1T1"), ("group_col", "Sample_Group"),
                ("level_a", "fusion_pos"), ("level_b", "fusion_neg")),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED))


def test_independent_read_keys_by_sample_name(tmp_path):
    ref = _contract(tmp_path)
    with _c.using_contract_root(tmp_path):
        row, group_of = independent_feature_row(_node(ref), "RUNX1T1")
    assert row == {"p1": 90.0, "p2": 100.0, "n1": 0.0, "n2": 0.2}   # keyed by NAME, not position
    assert group_of["p1"] == "fusion_pos" and group_of["n1"] == "fusion_neg"


def test_leg_a_and_leg_b_agree_on_a_correct_contract(tmp_path):
    from polymer_claims.expression_floor_adapters import _expr_split, _expr_split_independent
    ref = _contract(tmp_path)
    with _c.using_contract_root(tmp_path):
        node = _node(ref)
        a_pos, a_neg = _expr_split(node)                 # shared loader
        b_pos, b_neg = _expr_split_independent(node)     # independent loader
    assert sorted(a_pos) == sorted(b_pos) and sorted(a_neg) == sorted(b_neg)


def test_integrity_check_catches_tsv_manifest_mismatch(tmp_path):
    # Tamper the betas.tsv header so its columns no longer match the manifest col_data samples — the
    # exact orientation/alignment bug class the shared loader would silently mis-zip. Leg B must raise.
    ref = _contract(tmp_path)
    betas = tmp_path / "tcga_laml_fusion_expr.betas.tsv"
    lines = betas.read_text().splitlines()
    header = lines[0].split("\t")
    header[1] = "WRONG_SAMPLE"                            # rename a column away from the manifest
    lines[0] = "\t".join(header)
    betas.write_text("\n".join(lines) + "\n")
    _c.clear_contract_cache()
    with _c.using_contract_root(tmp_path):  # noqa: SIM117
        with pytest.raises(ValueError, match="integrity"):
            independent_feature_row(_node(ref), "RUNX1T1")
