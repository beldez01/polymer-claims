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

# ---------------------------------------------------------------------------
# Phase 5 — typed trust bindings
# ---------------------------------------------------------------------------
from pydantic import model_validator  # noqa: E402
from polymer_protocol import AdapterRegistry, OracleRegistry  # noqa: E402
from polymer_grammar.base import _Model  # noqa: E402
from polymer_grammar.capability import ConformanceReason, ConformanceResult, ConformanceWarning  # noqa: E402


class CapabilityTrustBinding(_Model):
    adapter_registry: AdapterRegistry
    oracle_registry: OracleRegistry
    trust_profile: str

    @model_validator(mode="after")
    def _check(self) -> "CapabilityTrustBinding":
        if not self.trust_profile.strip():
            raise ValueError("trust_profile must be nonempty")
        return self


def _bindings() -> "dict[tuple[str, str], CapabilityTrustBinding]":
    # Lazy imports break the cells<->adapters cycle.
    from .analysis_profile import profile_oracle_registry
    from .exec_adapters import apparatus_oracle_registry, independent_registry
    from .methyl_adapters import methyl_independent_registry
    from .methyl_ndmp import ndmp_independent_registry

    methyl_oracles = profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public"))
    return {
        ("stats::mean_diff", "v1"): CapabilityTrustBinding(
            adapter_registry=independent_registry(), oracle_registry=apparatus_oracle_registry(),
            trust_profile="bundled-dose-response-apparatus"),
        ("methyl::region_delta_beta", "v1"): CapabilityTrustBinding(
            adapter_registry=methyl_independent_registry(), oracle_registry=methyl_oracles,
            trust_profile="bundled-recomputable-public"),
        ("methyl::n_dmps", "v1"): CapabilityTrustBinding(
            adapter_registry=ndmp_independent_registry(), oracle_registry=methyl_oracles,
            trust_profile="bundled-recomputable-public"),
    }


def bind(capability_id: str, capability_version: str = "v1") -> CapabilityTrustBinding:
    if CAPABILITY_CELLS.resolve(capability_id, capability_version) is None:
        raise CapabilityNotFound(f"{capability_id}@{capability_version} not registered")
    binding = _bindings().get((capability_id, capability_version))
    if binding is None:
        raise CapabilityNotFound(f"no trust binding for {capability_id}@{capability_version}")
    return binding


def validate_trust_binding(
    cell: CapabilityCell, adapter_registry: AdapterRegistry, oracle_registry: OracleRegistry,
) -> ConformanceResult:
    from polymer_protocol.adapter_registry import adapters_independent

    reasons: list[ConformanceReason] = []
    warnings: list[ConformanceWarning] = []
    creds = []
    for ident in cell.eligible_adapter_identities:
        cred = adapter_registry.resolve(ident)
        if cred is None:
            warnings.append(ConformanceWarning.BINDING_ADAPTER_MISSING)
        elif not cred.trusted:
            warnings.append(ConformanceWarning.BINDING_ADAPTER_UNTRUSTED)
        else:
            creds.append(cred)
    if not any(adapters_independent(creds[i], creds[j])
               for i in range(len(creds)) for j in range(i + 1, len(creds))):
        reasons.append(ConformanceReason.BINDING_NO_INDEPENDENT_PAIR)
    if cell.oracle.required:
        oid = cell.oracle.default_oracle_id
        if oid is not None:
            if not any(d.oracle_id == oid for d in oracle_registry.dossiers):
                reasons.append(ConformanceReason.BINDING_ORACLE_MISSING)
        else:
            warnings.append(ConformanceWarning.BINDING_ORACLE_SATISFIABILITY_UNKNOWN)
    return ConformanceResult(reasons=_dedup_local(reasons), warnings=_dedup_local(warnings))


def _dedup_local(items: list) -> tuple:
    seen, out = set(), []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return tuple(out)
