"""The expression::absence adapters — two independent upper-summary legs over a healthy-tissue atlas."""
from __future__ import annotations

import pytest
from polymer_grammar import DataHandle, MeasurementBasis, OperationNode, ProducedLeafSpec

from polymer_claims import contracts as _c
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract


def _mini_atlas(tmp_path):
    # One target across five "tissues" (samples); worst tissue = 45 TPM. Groups are irrelevant to
    # the safety veto (the adapter summarises over ALL samples), so the labels are inert here.
    tpm = {"TARGETG": {"t1": 1.0, "t2": 0.5, "t3": 2.0, "t4": 45.0, "t5": 0.2}}
    grp = {"t1": "fusion_pos", "t2": "fusion_neg", "t3": "fusion_pos", "t4": "fusion_neg", "t5": "fusion_pos"}
    karyo = {k: "" for k in grp}
    build_fusion_expr_contract(tpm, grp, karyo, genes=["TARGETG"], out_dir=tmp_path)
    _c.clear_contract_cache()
    return "se:tcga_laml_fusion_expr@1"


def _node(ref, gene):
    return OperationNode(
        id="n", impl="expression::absence",
        inputs=(DataHandle(ref=ref),),
        params=(("gene", gene), ("group_col", "Sample_Group")),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )


def test_tissue_values_reads_all_samples_ignoring_groups(tmp_path):
    from polymer_claims.expression_absence_adapters import _tissue_values
    ref = _mini_atlas(tmp_path)
    with _c.using_contract_root(tmp_path):
        vals = _tissue_values(_node(ref, "TARGETG"))
    assert sorted(vals) == [0.2, 0.5, 1.0, 2.0, 45.0]


def test_max_leg_returns_the_worst_tissue(tmp_path):
    from polymer_claims.expression_absence_adapters import ExpressionAbsenceMaxAdapter
    ref = _mini_atlas(tmp_path)
    with _c.using_contract_root(tmp_path):
        v = ExpressionAbsenceMaxAdapter().execute(_node(ref, "TARGETG"), (), None)
    assert v.value == pytest.approx(45.0)


def test_rankq_leg_returns_a_high_quantile_upper_summary(tmp_path):
    from polymer_claims.expression_absence_adapters import ExpressionAbsenceRankQAdapter
    ref = _mini_atlas(tmp_path)
    with _c.using_contract_root(tmp_path):
        v = ExpressionAbsenceRankQAdapter().execute(_node(ref, "TARGETG"), (), None)
    # q99 of {0.2,0.5,1,2,45} interpolates near the top of the tail: high, but below the raw max.
    assert 40.0 < v.value <= 45.0


def test_the_two_legs_are_registry_independent():
    # The air-gap: distinct owner AND implementation_hash, so no SelfLicensingError on agreement.
    from polymer_claims.expression_absence_adapters import expression_absence_registry
    creds = expression_absence_registry().credentials
    assert len({c.owner for c in creds}) == 2
    assert len({c.implementation_hash for c in creds}) == 2


def test_wrong_impl_is_rejected(tmp_path):
    from polymer_claims.expression_absence_adapters import _tissue_values
    ref = _mini_atlas(tmp_path)
    with _c.using_contract_root(tmp_path):
        bad = _node(ref, "TARGETG").model_copy(update={"impl": "expression::floor"})
        with pytest.raises(ValueError, match="cannot execute impl"):
            _tissue_values(bad)
