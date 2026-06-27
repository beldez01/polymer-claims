import pytest
from polymer_grammar.capability import (
    CapabilityCell, ParamCodec, SubjectRequirement, OracleRequirement, DataRefKind,
)
from polymer_grammar.operations import Comparator, ProducedLeafSpec, MeasurementBasis
from polymer_grammar.pattern import PatternRef

@pytest.fixture
def make_cell():
    def _make(**over):
        base = dict(
            capability_id="x::y", capability_version="v1", operation_impl="x::y", title="t",
            pattern=PatternRef(id="adjusted_effect", version="v1"),
            subject=SubjectRequirement(mode="forbidden"),
            param_schema=(ParamCodec(name="a", codec="string"),),
            produced=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
            allowed_comparators=(Comparator.GT,),
            eligible_adapter_identities=("p", "q"),
            oracle=OracleRequirement(default_oracle_id="o", required=True),
            data_ref_kind=DataRefKind.OPAQUE,
            claim_leaf_kinds=("categorical",), criterion_target="threshold",
        )
        base.update(over)
        return CapabilityCell(**base)
    return _make
