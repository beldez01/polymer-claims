from __future__ import annotations


def test_expression_floor_claim_builds_with_floor_leaf():
    from polymer_claims.expression_floor_adapters import expression_floor_claim
    from polymer_grammar import QuantityLeaf, Status
    c = expression_floor_claim("floor-RUNX1T1", ref="se:tcga_laml_fusion_expr@1",
                               gene="RUNX1T1", floor=13.0, tissue="AML", search_cardinality=1)
    leaf = c.leaves[0]
    assert isinstance(leaf, QuantityLeaf) and leaf.value == 13.0 and leaf.low == 13.0
    assert c.status is Status.PENDING
    assert c.evaluation_plan.criterion.reference_leaf_index == 0


def test_cell_registered_and_reference_leaf_criterion():
    from polymer_claims.capabilities import EXPRESSION_FLOOR_CELL, CAPABILITY_CELLS
    assert EXPRESSION_FLOOR_CELL.criterion_target == "reference_leaf"
    assert EXPRESSION_FLOOR_CELL.claim_leaf_kinds == ("quantity",)
    assert EXPRESSION_FLOOR_CELL.agreement_mode == "both_satisfy_criterion"
    assert CAPABILITY_CELLS.resolve("expression::floor", "v1") is not None


def test_criterion_fires_as_plain_ge(tmp_path):
    # A QuantityLeaf(value=13, dimension=None) + ExecValue(value=x, dimension=None) compares as x>=13.
    from polymer_grammar.evaluate import _apply_criterion, ExecValue, SatisfactionVerdict
    from polymer_grammar import SatisfactionCriterion, Comparator, QuantityLeaf, MeasurementBasis
    leaf = QuantityLeaf(value=13.0, low=13.0, measurement_basis=MeasurementBasis.DERIVED,
                        formula="x>=f")
    crit = SatisfactionCriterion(comparator=Comparator.GE, reference_leaf_index=0)
    assert _apply_criterion(crit, ExecValue(value=94.0), (leaf,)) is SatisfactionVerdict.SATISFIED
    assert _apply_criterion(crit, ExecValue(value=0.02), (leaf,)) is SatisfactionVerdict.REFUTED
