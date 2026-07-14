"""§9 — invariance-consistency check: the first consumer of Pattern.invariance_group/scale.

Read-only, advisory (NOT wired to the gate). Cross-checks the pattern's declared scale-class against
the Stevens scale-type of the measurement space(s) the claim reads (B1 registry), catching the
ordinal-as-metric error. Umbrella-side; grammar/protocol untouched; Corpus 4.
"""
from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    ComputeGraph,
    DataHandle,
    EvaluationPlan,
    MeasurementBasis,
    OperationNode,
    PatternRef,
    ProducedLeafSpec,
    SatisfactionCriterion,
    Status,
)

from polymer_claims.invariance import (
    InvarianceVerdict,
    ScaleClass,
    admit_by_invariance,
    invariance_ok,
    invariance_report,
)

_METRIC_PATTERN = PatternRef(id="adjusted_effect", version="v1")     # scale=standardized -> METRIC
_ORDINAL_PATTERN = PatternRef(id="mechanistic_law", version="v1")    # scale=ordinal_relation -> ORDINAL


def _plan(ref: str) -> EvaluationPlan:
    node = OperationNode(
        id="n0", impl="builtin::const", inputs=(DataHandle(ref=ref),),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    return EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=0.05),
    )


def _claim(cid, pattern, *, ref=None) -> Claim:
    return Claim(
        id=cid, title=cid, pattern=pattern,
        leaves=(CategoricalLeaf(ontology_term=f"t-{cid}"),),
        status=Status.CONJECTURED,
        evaluation_plan=(_plan(ref) if ref is not None else None),
    )


def test_metric_pattern_over_ratio_space_is_coherent():
    # adjusted_effect (metric) reading gdsc_pharmaco (RATIO methylation + drug-response spaces)
    rep = invariance_report(_claim("c", _METRIC_PATTERN, ref="se:gdsc_pharmaco@1"))
    assert rep.pattern_scale_class is ScaleClass.METRIC
    assert rep.verdict is InvarianceVerdict.COHERENT
    assert invariance_ok(_claim("c", _METRIC_PATTERN, ref="se:gdsc_pharmaco@1"))


def test_ordinal_pattern_over_metric_space_is_incoherent():
    # mechanistic_law (ordinal) reading a RATIO expression space -> the ordinal-as-metric error
    rep = invariance_report(_claim("c", _ORDINAL_PATTERN, ref="se:tcga_laml_fusion_expr@1"))
    assert rep.pattern_scale_class is ScaleClass.ORDINAL
    assert "metric" in rep.space_scale_classes
    assert rep.verdict is InvarianceVerdict.INCOHERENT
    assert not invariance_ok(_claim("c", _ORDINAL_PATTERN, ref="se:tcga_laml_fusion_expr@1"))


def test_no_measurement_space_is_unchecked_not_failed():
    rep = invariance_report(_claim("c", _METRIC_PATTERN))  # no data_ref
    assert rep.verdict is InvarianceVerdict.UNCHECKED  # declared, nothing to cross-check
    assert invariance_ok(_claim("c", _METRIC_PATTERN))


def test_admit_by_invariance_refuses_incoherent_admits_the_rest():
    from polymer_grammar import RelationKind, Tier, make_relation_claim

    coherent = _claim("coh", _METRIC_PATTERN, ref="se:gdsc_pharmaco@1")       # metric/metric -> COHERENT
    incoherent = _claim("inc", _ORDINAL_PATTERN, ref="se:tcga_laml_fusion_expr@1")  # ordinal/metric -> INCOHERENT
    unchecked = _claim("unc", _METRIC_PATTERN)                                 # no ref -> UNCHECKED
    relation = make_relation_claim(
        "rel", ["a"], ["b"], Tier.BIOLOGICAL, RelationKind.COHERES, 0.5, rationale="r",
    )  # relations are never invariance-gated

    admitted, refused = admit_by_invariance([coherent, incoherent, unchecked, relation])
    assert {c.id for c in admitted} == {"coh", "unc", "rel"}
    assert [c.id for c, _ in refused] == ["inc"]
    assert refused[0][1].verdict is InvarianceVerdict.INCOHERENT


def test_admit_by_invariance_byte_identical_when_nothing_incoherent():
    # today's shape: all-coherent/unchecked -> nothing refused -> claims list passes through unchanged
    claims = [_claim("a", _METRIC_PATTERN, ref="se:gdsc_pharmaco@1"), _claim("b", _METRIC_PATTERN)]
    admitted, refused = admit_by_invariance(claims)
    assert [c.id for c in admitted] == ["a", "b"] and refused == []


def test_registered_patterns_all_declare_invariance_metadata():
    # every catalogued pattern declares BOTH scale and invariance_group (the precondition is stated)
    from polymer_grammar import get_pattern
    for pid in ("adjusted_effect", "reported_quantity", "mechanistic_law", "bounded_absence"):
        pat = get_pattern(pid, "v1")
        assert pat.scale and pat.invariance_group
