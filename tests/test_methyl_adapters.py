from __future__ import annotations

import pytest
from polymer_grammar import Comparator, DataHandle, MaterializationContext, MeasurementBasis, OperationNode, ProducedLeafSpec, Status

from polymer_claims.methyl_adapters import RegionLmCoefAdapter, RegionMeanDiffAdapter, methyl_independent_registry, region_delta_beta_claim

_CTX = MaterializationContext(id="M1", api_version="v1", data_version="epicv2_casectrl_demo@1")
_SIGNAL = ("cg00000001", "cg00000002", "cg00000003", "cg00000004", "cg00000005")
_CONTROL = ("cg00000006", "cg00000007", "cg00000008", "cg00000009", "cg00000010")


def _node(probes=_SIGNAL, ref="se:epicv2_casectrl_demo@1"):
    return OperationNode(
        id="n0", impl="methyl::region_delta_beta",
        inputs=(DataHandle(ref=ref),),
        params=(
            ("region_probes", ",".join(probes)),
            ("group_col", "Sample_Group"),
            ("level_a", "level1"),
            ("level_b", "level2"),
        ),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )


def test_signal_region_delta_is_planted_shift():
    md = RegionMeanDiffAdapter().execute(_node(), (), _CTX).value
    assert abs(md - 0.20) < 1e-9


def test_two_legs_agree_exactly():
    node = _node()
    md = RegionMeanDiffAdapter().execute(node, (), _CTX).value
    lm = RegionLmCoefAdapter().execute(node, (), _CTX).value
    assert abs(md - lm) < 1e-9


def test_control_region_delta_is_zero():
    md = RegionMeanDiffAdapter().execute(_node(probes=_CONTROL), (), _CTX).value
    assert abs(md) < 1e-9


def test_identities_distinct():
    assert RegionMeanDiffAdapter().identity == "methyl-meandiff-beta"
    assert RegionLmCoefAdapter().identity == "methyl-lm-coef"
    assert RegionMeanDiffAdapter().identity != RegionLmCoefAdapter().identity


def test_missing_region_probe_raises():
    with pytest.raises(Exception):
        RegionMeanDiffAdapter().execute(_node(probes=("cg99999999",)), (), _CTX)


def test_unsupported_impl_raises():
    bad = OperationNode(id="n0", impl="builtin::const", params=(("value", "1"),),
                        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED))
    with pytest.raises(Exception):
        RegionLmCoefAdapter().execute(bad, (), _CTX)


def test_claim_carries_oracle_ref_subject_and_criterion():
    c = region_delta_beta_claim("c0")
    node = c.evaluation_plan.graph.nodes[0]
    assert node.oracle_ref == "canonical_epicv2_hg38_v1@1"
    assert node.impl == "methyl::region_delta_beta"
    assert c.subject is not None and c.subject.kind == "genomic_region"
    assert c.status == Status.PENDING and c.strength is None
    crit = c.evaluation_plan.criterion
    assert crit.comparator == Comparator.GT and crit.threshold == 0.10


def test_claim_can_omit_subject_for_the_precondition_probe():
    c = region_delta_beta_claim("c-nosub", with_subject=False)
    assert c.subject is None


def test_independent_registry_has_two_distinct_owners():
    reg = methyl_independent_registry()
    owners = {cr.owner for cr in reg.credentials}
    ids = {cr.identity for cr in reg.credentials}
    assert ids == {"methyl-meandiff-beta", "methyl-lm-coef"}
    assert len(owners) == 2
