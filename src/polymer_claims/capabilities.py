"""Capability registry (V1) — the three reductions as registered CapabilityCells + trust bindings.
Cells are pure descriptors; trust bindings (below) resolve concrete registries lazily."""
from __future__ import annotations

from polymer_grammar.capability import (
    CapabilityCell, CapabilityRegistry, DataRefKind, OracleRequirement, ParamCodec, SubjectRequirement,
)
from polymer_grammar.operations import Comparator, MeasurementBasis, ProducedLeafSpec
from polymer_grammar.pattern import PatternRef

from .analysis_profile import profile_oracle_id
from .profiles import CANONICAL_EPICV2_V1

_Q = ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED)
_PATTERN = PatternRef(id="adjusted_effect", version="v1")
_ALL_CMP = (Comparator.LT, Comparator.LE, Comparator.EQ, Comparator.NE, Comparator.GE, Comparator.GT)
_METHYL_ORACLE = profile_oracle_id(CANONICAL_EPICV2_V1)
_STR = ParamCodec  # alias for brevity below


class CapabilityNotFound(KeyError):
    """Raised by bind() for an unknown (capability_id, capability_version)."""


MEAN_DIFF_CELL = CapabilityCell(
    capability_id="stats::mean_diff", capability_version="v1", operation_impl="stats::mean_diff",
    title="two-group mean difference", pattern=_PATTERN, subject=SubjectRequirement(mode="forbidden"),
    param_schema=(_STR(name="value_col", codec="string"), _STR(name="group_col", codec="string"),
                  _STR(name="group_a", codec="string"), _STR(name="group_b", codec="string")),
    produced=_Q, allowed_comparators=_ALL_CMP,
    eligible_adapter_identities=("stats-pure", "stats-stdlib"),
    oracle=OracleRequirement(default_oracle_id="dose_response_apparatus", required=True),
    data_ref_kind=DataRefKind.OPAQUE, claim_leaf_kinds=("categorical",), criterion_target="threshold",
)

REGION_DELTA_BETA_CELL = CapabilityCell(
    capability_id="methyl::region_delta_beta", capability_version="v1",
    operation_impl="methyl::region_delta_beta", title="region differential methylation",
    pattern=_PATTERN, subject=SubjectRequirement(mode="required", kind="genomic_region"),
    param_schema=(_STR(name="region_probes", codec="csv"), _STR(name="group_col", codec="string"),
                  _STR(name="level_a", codec="string"), _STR(name="level_b", codec="string")),
    produced=_Q, allowed_comparators=_ALL_CMP,
    eligible_adapter_identities=("methyl-meandiff-beta", "methyl-lm-coef"),
    oracle=OracleRequirement(default_oracle_id=_METHYL_ORACLE, required=True),
    data_ref_kind=DataRefKind.SE_CONTRACT, claim_leaf_kinds=("categorical",), criterion_target="threshold",
)

N_DMPS_CELL = CapabilityCell(
    capability_id="methyl::n_dmps", capability_version="v1", operation_impl="methyl::n_dmps",
    title="n differentially-methylated probes", pattern=_PATTERN,
    subject=SubjectRequirement(mode="required", kind="genomic_region"),
    param_schema=(_STR(name="probes", codec="csv"), _STR(name="group_col", codec="string"),
                  _STR(name="level_a", codec="string"), _STR(name="level_b", codec="string"),
                  _STR(name="alpha", codec="float")),
    produced=_Q, allowed_comparators=_ALL_CMP,
    eligible_adapter_identities=("methyl-ndmp-ttest", "methyl-ndmp-ols"),
    oracle=OracleRequirement(default_oracle_id=_METHYL_ORACLE, required=True),
    data_ref_kind=DataRefKind.SE_CONTRACT, claim_leaf_kinds=("categorical",), criterion_target="threshold",
)

CAPABILITY_CELLS = CapabilityRegistry(cells=(MEAN_DIFF_CELL, REGION_DELTA_BETA_CELL, N_DMPS_CELL))
