# grammar/tests/test_commitment.py
import pytest

from polymer_grammar.commitment import commitment_hash
from polymer_grammar.leaf import CategoricalLeaf, MeasurementBasis
from polymer_grammar.operations import (
    ComputeGraph, Comparator, EvaluationPlan, OperationNode, ProducedLeafSpec, SatisfactionCriterion,
)
from polymer_grammar.pattern import PatternRef
from polymer_grammar.status import Status
from polymer_grammar.claim import Claim

_PATTERN = PatternRef(id="adjusted_effect", version="v1")   # field is `id` (matches conftest _PATTERN)


def _plan(value: float, threshold: float, comparator=Comparator.GT, region=("cg1", "cg2")):
    node = OperationNode(
        id="n0", impl="builtin::const",
        params=(("value", str(value)), ("region", ",".join(region))),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    return EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=comparator, threshold=threshold),
    )


def _claim(cid, plan):
    return Claim(id=cid, title=cid, pattern=_PATTERN,
                 leaves=(CategoricalLeaf(ontology_term="t"),), status=Status.CONJECTURED,
                 evaluation_plan=plan)


def test_hash_is_deterministic_and_prefixed():
    h1 = commitment_hash(_claim("c", _plan(0.2, 0.10)))
    h2 = commitment_hash(_claim("c", _plan(0.2, 0.10)))
    assert h1 == h2 and h1.startswith("sha256:")


def test_hash_independent_of_claim_id():
    # the commitment is the PLAN, not the id
    assert commitment_hash(_claim("a", _plan(0.2, 0.10))) == commitment_hash(_claim("b", _plan(0.2, 0.10)))


def test_hash_changes_on_threshold_region_or_comparator():
    base = commitment_hash(_claim("c", _plan(0.2, 0.10)))
    assert commitment_hash(_claim("c", _plan(0.2, 0.20))) != base          # threshold
    assert commitment_hash(_claim("c", _plan(0.2, 0.10, region=("cg1",)))) != base  # region
    assert commitment_hash(_claim("c", _plan(0.2, 0.10, comparator=Comparator.LT))) != base  # comparator


def test_hash_requires_a_plan():
    no_plan = Claim(id="c", title="c", pattern=_PATTERN,
                    leaves=(CategoricalLeaf(ontology_term="t"),), status=Status.CONJECTURED)
    with pytest.raises(ValueError):
        commitment_hash(no_plan)
