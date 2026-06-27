import pytest
from polymer_grammar.capability import (
    build_evaluation_plan, validate_claim_shape, validate_claim_conformance,
    CapabilityParamError, CapabilityRegistry, criterion_target_ok,
    ConformanceReason as R, SubjectRequirement, DataRefKind, OracleRequirement, ParamCodec,
)
from polymer_grammar.operations import (
    Comparator, SatisfactionCriterion, OperationNode, ComputeGraph, EvaluationPlan,
    DataHandle, NodeRef, ProducedLeafSpec, MeasurementBasis,
)
from polymer_grammar.claim import Claim
from polymer_grammar.status import Status, PendingReason
from polymer_grammar.leaf import CategoricalLeaf, ExistenceLeaf
from polymer_grammar.subject import GenomicRegion

_Q = ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED)

def _crit(threshold=1.0):
    return SatisfactionCriterion(comparator=Comparator.GT, threshold=threshold)

def _claim(cell, plan=None, **over):
    plan = plan or build_evaluation_plan(cell, params={"a": "v"}, data_ref="dose_response", criterion=_crit())
    base = dict(id="c1", title="t", pattern=cell.pattern, leaves=(CategoricalLeaf(ontology_term="x"),),
                status=Status.PENDING, pending_reason=PendingReason.UNTESTED, evaluation_plan=plan)
    base.update(over)
    return Claim(**base)

# ---- build_evaluation_plan ----
def test_build_single_node(make_cell):
    plan = build_evaluation_plan(make_cell(), params={"a": "v"}, data_ref="dose_response", criterion=_crit())
    n = plan.graph.nodes[0]
    assert len(plan.graph.nodes) == 1 and n.id == "n0" and plan.graph.terminal == "n0"
    assert n.params == (("a", "v"),) and n.oracle_ref == "o"

@pytest.mark.parametrize("kwargs", [
    {"params": {}}, {"params": {"a": "v", "z": "1"}},
])
def test_build_param_errors(make_cell, kwargs):
    with pytest.raises(CapabilityParamError):
        build_evaluation_plan(make_cell(), data_ref="dose_response", criterion=_crit(), **kwargs)

def test_build_disallowed_comparator(make_cell):
    with pytest.raises(CapabilityParamError):
        build_evaluation_plan(make_cell(), params={"a": "v"}, data_ref="dose_response",
                              criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=1.0))

def test_build_bad_data_ref(make_cell):
    with pytest.raises(CapabilityParamError):
        build_evaluation_plan(make_cell(data_ref_kind=DataRefKind.SE_CONTRACT),
                              params={"a": "v"}, data_ref="nope", criterion=_crit())

def test_build_rejects_empty_csv_and_nonfinite_float(make_cell):
    # valid-domain compatibility: noncanonical params the LEGACY builders serialized now fail fast.
    csv_cell = make_cell(param_schema=(ParamCodec(name="a", codec="csv"),))
    with pytest.raises(CapabilityParamError):
        build_evaluation_plan(csv_cell, params={"a": ""}, data_ref="dose_response", criterion=_crit())  # ",".join(())
    float_cell = make_cell(param_schema=(ParamCodec(name="a", codec="float"),))
    for bad in ("nan", "inf"):
        with pytest.raises(CapabilityParamError):
            build_evaluation_plan(float_cell, params={"a": bad}, data_ref="dose_response", criterion=_crit())

def test_build_oracle_required_missing(make_cell):
    with pytest.raises(CapabilityParamError):
        build_evaluation_plan(make_cell(oracle=OracleRequirement(required=True)),
                              params={"a": "v"}, data_ref="dose_response", criterion=_crit(), oracle_ref=None)

def test_criterion_target_helper():
    assert criterion_target_ok("threshold", _crit())
    assert not criterion_target_ok("reference_leaf", _crit())

# ---- validate_claim_shape: positive ----
def test_conformant_claim_passes(make_cell):
    cell = make_cell()
    assert validate_claim_shape(_claim(cell), cell).ok

# ---- validate_claim_shape: never raises on degenerate graphs ----
@pytest.mark.parametrize("inputs", [(), (DataHandle(ref="dose_response"), DataHandle(ref="x"))])
def test_degenerate_inputs_return_not_raise(make_cell, inputs):
    cell = make_cell()
    node = OperationNode(id="n0", impl="x::y", inputs=inputs, params=(("a", "v"),), oracle_ref="o", produces=_Q)
    plan = EvaluationPlan(graph=ComputeGraph(nodes=(node,), terminal="n0"), criterion=_crit())
    res = validate_claim_shape(_claim(cell, plan=plan), cell)   # must return, not raise
    assert R.GRAPH_SHAPE_MISMATCH in res.reasons

def test_two_node_graph_is_graph_shape_mismatch(make_cell):
    # A NodeRef is only valid inside an acyclic MULTI-node graph; V1 requires exactly one node.
    cell = make_cell()
    n0 = OperationNode(id="n0", impl="x::y", inputs=(DataHandle(ref="dose_response"),),
                       params=(("a", "v"),), oracle_ref="o", produces=_Q)
    n1 = OperationNode(id="n1", impl="x::y", inputs=(NodeRef(node_id="n0"),),
                       params=(("a", "v"),), oracle_ref="o", produces=_Q)
    plan = EvaluationPlan(graph=ComputeGraph(nodes=(n0, n1), terminal="n1"), criterion=_crit())
    res = validate_claim_shape(_claim(cell, plan=plan), cell)
    assert R.GRAPH_SHAPE_MISMATCH in res.reasons and not res.ok

# ---- validate_claim_shape: one negative case per fatal reason ----
def _mutant_plan(impl="x::y", params=(("a", "v"),), produces=_Q, terminal="n0", ref="dose_response"):
    node = OperationNode(id="n0", impl=impl, inputs=(DataHandle(ref=ref),), params=params, oracle_ref="o", produces=produces)
    return EvaluationPlan(graph=ComputeGraph(nodes=(node,), terminal=terminal), criterion=_crit())

def test_each_fatal_reason(make_cell):
    cell = make_cell()
    cases = {
        R.OPERATION_IMPL_MISMATCH: _claim(cell, plan=_mutant_plan(impl="other::impl")),
        R.OUTPUT_TYPE_MISMATCH: _claim(cell, plan=_mutant_plan(
            produces=ProducedLeafSpec(leaf_kind="categorical"))),
        R.PARAM_UNKNOWN: _claim(cell, plan=_mutant_plan(params=(("a", "v"), ("z", "1")))),
        R.PARAM_MISSING: _claim(cell, plan=_mutant_plan(params=(("b", "v"),))),
        R.PARAM_DUPLICATE: _claim(cell, plan=_mutant_plan(params=(("a", "1"), ("a", "2")))),
        R.PATTERN_MISMATCH: _claim(cell, pattern=cell.pattern.model_copy(update={"id": "zzz"})),
        R.LEAF_SHAPE_MISMATCH: _claim(cell, leaves=(ExistenceLeaf(state="observed"),)),
        R.SUBJECT_FORBIDDEN_PRESENT: _claim(
            cell, subject=GenomicRegion(id="r", display="r", assembly="hg38", chrom="chr1", start=1, end=2)),
    }
    for reason, claim in cases.items():
        assert reason in validate_claim_shape(claim, cell).reasons, reason

def test_comparator_criterion_target_and_leaf_count(make_cell):
    cell = make_cell()  # allows only GT; criterion_target="threshold"; one categorical leaf
    node = OperationNode(id="n0", impl="x::y", inputs=(DataHandle(ref="dose_response"),),
                         params=(("a", "v"),), oracle_ref="o", produces=_Q)
    bad_cmp = EvaluationPlan(graph=ComputeGraph(nodes=(node,), terminal="n0"),
                             criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=1.0))
    assert R.COMPARATOR_NOT_ALLOWED in validate_claim_shape(_claim(cell, plan=bad_cmp), cell).reasons
    ref_crit = EvaluationPlan(graph=ComputeGraph(nodes=(node,), terminal="n0"),
                              criterion=SatisfactionCriterion(comparator=Comparator.GT, reference_leaf_index=0))
    assert R.CRITERION_TARGET_MISMATCH in validate_claim_shape(_claim(cell, plan=ref_crit), cell).reasons
    # wrong leaf COUNT (two where one expected)
    res = validate_claim_shape(_claim(cell, leaves=(CategoricalLeaf(ontology_term="x"),
                                                    CategoricalLeaf(ontology_term="y"))), cell)
    assert R.LEAF_SHAPE_MISMATCH in res.reasons

def test_malformed_param_and_data_ref_and_subject_kind(make_cell):
    cell = make_cell(param_schema=(ParamCodec(name="a", codec="float"),),
                     data_ref_kind=DataRefKind.SE_CONTRACT,
                     subject=SubjectRequirement(mode="required", kind="cohort"))
    node = OperationNode(id="n0", impl="x::y", inputs=(DataHandle(ref="se:bad@x"),),
                         params=(("a", "5e-2"),), oracle_ref="o", produces=_Q)
    plan = EvaluationPlan(graph=ComputeGraph(nodes=(node,), terminal="n0"), criterion=_crit())
    sub = GenomicRegion(id="r", display="r", assembly="hg38", chrom="chr1", start=1, end=2)
    res = validate_claim_shape(_claim(cell, plan=plan, subject=sub), cell)
    assert {R.PARAM_MALFORMED, R.DATA_REF_KIND_MISMATCH, R.SUBJECT_KIND_MISMATCH} <= set(res.reasons)

def test_subject_required_missing_and_oracle_required_missing(make_cell):
    cell = make_cell(subject=SubjectRequirement(mode="required", kind="genomic_region"),
                     oracle=OracleRequirement(required=True))
    node = OperationNode(id="n0", impl="x::y", inputs=(DataHandle(ref="dose_response"),),
                         params=(("a", "v"),), oracle_ref=None, produces=_Q)
    plan = EvaluationPlan(graph=ComputeGraph(nodes=(node,), terminal="n0"), criterion=_crit())
    res = validate_claim_shape(_claim(cell, plan=plan, subject=None), cell)
    assert {R.SUBJECT_REQUIRED_MISSING, R.ORACLE_REQUIRED_MISSING} <= set(res.reasons)

def test_multi_reason_report_when_node_absent(make_cell):
    # wrong leaf + wrong pattern still reported even though the plan node is degenerate
    cell = make_cell()
    node = OperationNode(id="bad", impl="x::y", inputs=(DataHandle(ref="dose_response"),),
                         params=(("a", "v"),), oracle_ref="o", produces=_Q)
    plan = EvaluationPlan(graph=ComputeGraph(nodes=(node,), terminal="bad"), criterion=_crit())
    res = validate_claim_shape(
        _claim(cell, plan=plan, pattern=cell.pattern.model_copy(update={"id": "zz"}),
               leaves=(ExistenceLeaf(state="observed"),)), cell)
    assert {R.GRAPH_SHAPE_MISMATCH, R.PATTERN_MISMATCH, R.LEAF_SHAPE_MISMATCH} <= set(res.reasons)

# ---- registry wrapper ----
def test_conformance_wrapper(make_cell):
    cell = make_cell()
    reg = CapabilityRegistry(cells=(cell,))
    assert validate_claim_conformance(_claim(cell), reg, "x::y", "v1").ok
    assert validate_claim_conformance(_claim(cell), reg, "nope", "v1").reasons == (R.CAPABILITY_NOT_REGISTERED,)

def test_exports():
    import polymer_grammar as g
    assert hasattr(g, "CapabilityCell") and hasattr(g, "build_evaluation_plan")
