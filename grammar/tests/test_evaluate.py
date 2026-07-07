import pytest

from polymer_grammar.evaluate import (
    ExecValue,
    IdentityAdapter,
    ReferenceAdapter,
    SelfLicensingError,
    evaluate,
    verify,
)
from polymer_grammar.leaf import CategoricalLeaf, MeasurementBasis, QuantityLeaf
from polymer_grammar.licensing import MaterializationContext, SatisfactionVerdict
from polymer_grammar.operations import (
    ComputeGraph,
    Comparator,
    EvaluationPlan,
    NodeRef,
    OperationNode,
    ProducedLeafSpec,
    SatisfactionCriterion,
)
from polymer_grammar.units import Dimension


def _ctx():
    return MaterializationContext(
        id="m1", api_version="0.9.x", data_version="db@2026-06-02"
    )


def _q():
    return ProducedLeafSpec(
        leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED
    )


def test_exec_value_holds_scalar():
    assert ExecValue(value=1.5).value == 1.5
    assert ExecValue(value=None).value is None


def test_self_licensing_error_exists():
    assert issubclass(SelfLicensingError, Exception)
    err = SelfLicensingError("writer must not be the verifier")
    assert "verifier" in str(err)


def test_const_impl_agrees_across_two_implementations():
    node = OperationNode(
        id="a", impl="builtin::const", params=(("value", "0.03"),), produces=_q()
    )
    a = IdentityAdapter()
    b = ReferenceAdapter()
    assert a.identity != b.identity
    va = a.execute(node, (), _ctx())
    vb = b.execute(node, (), _ctx())
    assert va.value == vb.value == 0.03


def test_mean_impl_computed_independently_agrees():
    node = OperationNode(
        id="a", impl="builtin::mean", params=(("vector", "1,2,3,4"),), produces=_q()
    )
    va = IdentityAdapter().execute(node, (), _ctx())
    vb = ReferenceAdapter().execute(node, (), _ctx())
    assert va.value == vb.value == 2.5


def test_perturbed_reference_adapter_disagrees():
    node = OperationNode(
        id="a", impl="builtin::const", params=(("value", "0.03"),), produces=_q()
    )
    vb = ReferenceAdapter(perturb=1.0).execute(node, (), _ctx())
    assert vb.value == 1.03


def test_identity_impl_passes_through_upstream_with_dimension():
    from polymer_grammar.units import Dimension

    node = OperationNode(id="a", impl="builtin::identity", produces=_q())
    up = (ExecValue(value=2.0, dimension=Dimension.base("length")),)
    va = IdentityAdapter().execute(node, up, _ctx())
    vb = ReferenceAdapter().execute(node, up, _ctx())
    assert va.value == vb.value == 2.0
    assert va.dimension == vb.dimension == Dimension.base("length")


def test_identity_impl_falls_back_to_param_when_no_upstream():
    node = OperationNode(
        id="a", impl="builtin::identity", params=(("value", "0.5"),), produces=_q()
    )
    va = IdentityAdapter().execute(node, (), _ctx())
    vb = ReferenceAdapter().execute(node, (), _ctx())
    assert va.value == vb.value == 0.5


def _plan(impl="builtin::const", params=(("value", "0.03"),), criterion=None):
    node = OperationNode(id="a", impl=impl, params=params, produces=_q())
    if criterion is None:
        criterion = SatisfactionCriterion(comparator=Comparator.LT, threshold=0.05)
    return EvaluationPlan(graph=ComputeGraph(nodes=(node,), terminal="a"), criterion=criterion)


def test_evaluate_satisfied_below_threshold():
    res = evaluate(_plan(), _ctx(), IdentityAdapter())
    assert res.verdict == SatisfactionVerdict.SATISFIED
    assert res.terminal.value == 0.03
    assert res.status == "complete"
    assert res.adapter_identity == "identity"


def test_evaluate_refuted_above_threshold():
    res = evaluate(_plan(params=(("value", "0.9"),)), _ctx(), IdentityAdapter())
    assert res.verdict == SatisfactionVerdict.REFUTED


def test_evaluate_undetermined_on_node_error():
    res = evaluate(_plan(impl="builtin::nope"), _ctx(), IdentityAdapter())
    assert res.verdict == SatisfactionVerdict.UNDETERMINED
    assert res.status == "error"
    assert res.nodes[0].error is not None


def test_evaluate_records_drift_against_expected_param():
    plan = _plan(params=(("value", "0.03"), ("expected", "0.03")))
    res = evaluate(plan, _ctx(), IdentityAdapter())
    assert res.nodes[0].drift is not None
    assert res.nodes[0].drift.within_tolerance is True


def test_evaluate_wraps_typed_leaf():
    res = evaluate(_plan(), _ctx(), IdentityAdapter())
    assert isinstance(res.nodes[0].produced, QuantityLeaf)
    assert res.nodes[0].produced.value == 0.03


def test_evaluate_reference_leaf_comparison_with_dimension_mismatch():
    node = OperationNode(
        id="a", impl="builtin::const", params=(("value", "1.0"),),
        produces=ProducedLeafSpec(
            leaf_kind="quantity", measurement_basis=MeasurementBasis.FUNDAMENTAL,
            unit="m", dimension=Dimension.base("length"),
        ),
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="a"),
        criterion=SatisfactionCriterion(comparator=Comparator.GE, reference_leaf_index=0),
    )
    ref_leaf = QuantityLeaf(
        value=0.5, unit="s", measurement_basis=MeasurementBasis.FUNDAMENTAL,
        dimension=Dimension.base("time"),
    )
    res = evaluate(plan, _ctx(), IdentityAdapter(), claim_leaves=(ref_leaf,))
    assert res.verdict == SatisfactionVerdict.UNDETERMINED


def test_evaluate_reference_leaf_comparison_satisfied():
    node = OperationNode(
        id="a", impl="builtin::const", params=(("value", "2.0"),), produces=_q()
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="a"),
        criterion=SatisfactionCriterion(comparator=Comparator.GT, reference_leaf_index=0),
    )
    ref_leaf = QuantityLeaf(value=1.0, measurement_basis=MeasurementBasis.DERIVED, formula="x")
    res = evaluate(plan, _ctx(), IdentityAdapter(), claim_leaves=(ref_leaf,))
    assert res.verdict == SatisfactionVerdict.SATISFIED


def test_evaluate_never_raises_on_unwrappable_adapter_output():
    class BadAdapter:
        identity = "bad"
        def execute(self, node, upstream, ctx):
            return ExecValue(value="not_a_number")  # bad for a quantity node

    res = evaluate(_plan(), _ctx(), BadAdapter())
    assert res.nodes[0].error is not None
    assert res.verdict == SatisfactionVerdict.UNDETERMINED


def test_evaluate_partial_status_when_nonterminal_errors_but_terminal_resolves():
    bad = OperationNode(id="bad", impl="builtin::nope", produces=_q())
    good = OperationNode(
        id="t", impl="builtin::const", params=(("value", "0.03"),), produces=_q()
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(bad, good), terminal="t"),
        criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=0.05),
    )
    res = evaluate(plan, _ctx(), IdentityAdapter())
    assert res.status == "partial"
    assert res.verdict == SatisfactionVerdict.SATISFIED
    assert any(n.error for n in res.nodes)


def test_evaluate_multinode_chain_threads_upstream():
    a = OperationNode(id="a", impl="builtin::const", params=(("value", "0.02"),), produces=_q())
    b = OperationNode(id="b", impl="builtin::identity", inputs=(NodeRef(node_id="a"),), produces=_q())
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(a, b), terminal="b"),
        criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=0.05),
    )
    res = evaluate(plan, _ctx(), IdentityAdapter())
    assert res.terminal.value == 0.02
    assert res.status == "complete"


def test_evaluate_drift_out_of_tolerance_flags_false():
    plan = _plan(params=(("value", "0.03"), ("expected", "0.05")))
    res = evaluate(plan, _ctx(), IdentityAdapter())
    assert res.nodes[0].drift.within_tolerance is False


def test_evaluate_str_vs_numeric_threshold_is_undetermined():
    class StrAdapter:
        identity = "str"
        def execute(self, node, upstream, ctx):
            return ExecValue(value="HGNC:11998")

    node = OperationNode(id="a", impl="x", produces=ProducedLeafSpec(leaf_kind="categorical"))
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="a"),
        criterion=SatisfactionCriterion(comparator=Comparator.NE, threshold=42.0),
    )
    res = evaluate(plan, _ctx(), StrAdapter())
    assert res.verdict == SatisfactionVerdict.UNDETERMINED


def test_evaluate_string_equality_satisfied_via_reference_leaf():
    class StrAdapter:
        identity = "str"
        def execute(self, node, upstream, ctx):
            return ExecValue(value="HGNC:11998")

    node = OperationNode(id="a", impl="x", produces=ProducedLeafSpec(leaf_kind="categorical"))
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="a"),
        criterion=SatisfactionCriterion(comparator=Comparator.EQ, reference_leaf_index=0),
    )
    ref = CategoricalLeaf(ontology_term="HGNC:11998")
    res = evaluate(plan, _ctx(), StrAdapter(), claim_leaves=(ref,))
    assert res.verdict == SatisfactionVerdict.SATISFIED


def test_verify_mints_satisfaction_on_agreement():
    ve = verify(_plan(), _ctx(), (IdentityAdapter(), ReferenceAdapter()))
    assert ve.agreement is True
    assert ve.satisfaction is not None
    assert ve.satisfaction.verdict == SatisfactionVerdict.SATISFIED
    assert ve.satisfaction.materialization.id == "m1"


def test_verify_rejects_single_adapter():
    with pytest.raises(SelfLicensingError):
        verify(_plan(), _ctx(), (IdentityAdapter(),))


def test_verify_rejects_same_identity_pair():
    with pytest.raises(SelfLicensingError):
        verify(_plan(), _ctx(), (IdentityAdapter(), IdentityAdapter()))


def test_verify_no_satisfaction_on_value_disagreement():
    ve = verify(_plan(), _ctx(), (IdentityAdapter(), ReferenceAdapter(perturb=1.0)))
    assert ve.agreement is False
    assert ve.satisfaction is None
    assert ve.disagreement is not None


def test_verify_no_satisfaction_when_agreed_but_refuted():
    ve = verify(
        _plan(params=(("value", "0.9"),)),
        _ctx(),
        (IdentityAdapter(), ReferenceAdapter()),
    )
    assert ve.agreement is True
    assert ve.satisfaction is None  # agreed verdict is REFUTED, not SATISFIED


def test_evaluate_public_api_is_exported():
    import polymer_grammar as pg

    for name in (
        "evaluate", "verify", "Adapter", "ExecValue", "EvaluationResult",
        "VerifiedEvaluation", "NodeEvaluation", "Drift", "IdentityAdapter",
        "ReferenceAdapter", "SelfLicensingError",
    ):
        assert hasattr(pg, name), name


def test_verify_agreement_on_undetermined_does_not_mint():
    # Both adapters fail the same node -> both UNDETERMINED -> they "agree" but nothing mints.
    ve = verify(_plan(impl="builtin::nope"), _ctx(), (IdentityAdapter(), ReferenceAdapter()))
    assert ve.results[0].verdict == SatisfactionVerdict.UNDETERMINED
    assert ve.agreement is True
    assert ve.satisfaction is None


# ---------------------------------------------------------------------------
# Per-capability agreement_mode override (CapabilityCell.agreement_mode's grammar-level
# mechanism; n-DMP threads "both_satisfy_criterion" through in the umbrella).
# ---------------------------------------------------------------------------


class _ConstCountAdapter:
    """Toy adapter that always reports a fixed terminal count, regardless of the node — exercises
    the agreement-mode mechanism in isolation, independent of any real capability."""

    def __init__(self, identity: str, value: float) -> None:
        self.identity = identity
        self._value = value

    def execute(self, node, upstream, ctx) -> ExecValue:
        return ExecValue(value=self._value)


def _count_plan(threshold: float = 0.0) -> EvaluationPlan:
    node = OperationNode(id="a", impl="builtin::const", params=(("value", "0.0"),), produces=_q())
    criterion = SatisfactionCriterion(comparator=Comparator.GE, threshold=threshold)
    return EvaluationPlan(graph=ComputeGraph(nodes=(node,), terminal="a"), criterion=criterion)


def test_verify_both_satisfy_criterion_agrees_despite_large_magnitude_gap():
    # threshold k=10: 100 and 500 both clear it by very different amounts (80% relative gap,
    # far beyond any numeric tolerance) -- both_satisfy_criterion mode agrees anyway, because
    # BOTH legs' own verdicts are independently SATISFIED (100>=10 and 500>=10); there is no
    # numeric-closeness requirement in this mode.
    ve = verify(
        _count_plan(threshold=10.0), _ctx(),
        (_ConstCountAdapter("a1", 100.0), _ConstCountAdapter("a2", 500.0)),
        agreement_mode="both_satisfy_criterion",
    )
    assert ve.agreement is True
    assert ve.satisfaction is not None


def test_verify_both_satisfy_criterion_disagrees_when_only_one_leg_clears_threshold():
    # threshold k=10: leg a1's 5.0 REFUTES (5 < 10) while leg a2's 20.0 SATISFIES (20 >= 10) --
    # the two legs' own verdicts genuinely disagree, so even under both_satisfy_criterion mode
    # (no numeric-closeness check) agreement fails and nothing is minted.
    ve = verify(
        _count_plan(threshold=10.0), _ctx(),
        (_ConstCountAdapter("a1", 5.0), _ConstCountAdapter("a2", 20.0)),
        agreement_mode="both_satisfy_criterion",
    )
    assert ve.agreement is False
    assert ve.satisfaction is None


def test_verify_default_mode_preserves_tight_numeric_bound():
    # No override (agreement_mode="tight_numeric", the default) -> the OLD global tight bound
    # (abs 1e-9 OR rel 1e-6) still applies byte-identically: a difference that both independently
    # satisfy the (GE 0) criterion, but that lies outside the tight bound, must still disagree.
    ve = verify(
        _count_plan(), _ctx(),
        (_ConstCountAdapter("a1", 100.0), _ConstCountAdapter("a2", 100.001)),
    )
    assert ve.agreement is False
