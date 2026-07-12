"""Capability registry (V1) — the three reductions as registered CapabilityCells + trust bindings.
Cells are pure descriptors; trust bindings (below) resolve concrete registries lazily."""
from __future__ import annotations

from polymer_grammar.capability import (
    CapabilityCell, CapabilityRegistry, DataRefKind, OracleRequirement, ParamCodec, SubjectRequirement,
)
from polymer_grammar.operations import Comparator, MeasurementBasis, ProducedLeafSpec
from polymer_grammar.pattern import PatternRef

from .analysis_profile import profile_oracle_id
from .benchmark_capability import EVAL_BENCHMARK_ADVANTAGE_CELL  # noqa: E402 (breaks cycle safely)
from .expression_floor_patterns import EXPRESSION_FLOOR
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
    eligible_adapter_identities=("methyl-meandiff-beta", "methyl-hodges-lehmann"),
    oracle=OracleRequirement(default_oracle_id=_METHYL_ORACLE, required=True),
    data_ref_kind=DataRefKind.SE_CONTRACT, claim_leaf_kinds=("categorical",), criterion_target="threshold",
    # region-Δβ's two legs (group mean-difference vs Hodges–Lehmann location-shift) are
    # genuinely different estimators that can clear a threshold claim's criterion by different
    # amounts on skewed betas — the honest agreement bar is "both legs independently satisfy the
    # claim's criterion", not numeric closeness on the point estimate. See
    # CapabilityCell.agreement_mode / evaluate._check_agreement.
    agreement_mode="both_satisfy_criterion",
)

N_DMPS_CELL = CapabilityCell(
    capability_id="methyl::n_dmps", capability_version="v1", operation_impl="methyl::n_dmps",
    title="n differentially-methylated probes", pattern=_PATTERN,
    subject=SubjectRequirement(mode="required", kind="genomic_region"),
    param_schema=(_STR(name="probes", codec="csv"), _STR(name="group_col", codec="string"),
                  _STR(name="level_a", codec="string"), _STR(name="level_b", codec="string"),
                  _STR(name="alpha", codec="float")),
    produced=_Q, allowed_comparators=_ALL_CMP,
    eligible_adapter_identities=("methyl-ndmp-ttest", "methyl-ndmp-rank"),
    oracle=OracleRequirement(default_oracle_id=_METHYL_ORACLE, required=True),
    data_ref_kind=DataRefKind.SE_CONTRACT, claim_leaf_kinds=("categorical",), criterion_target="threshold",
    # n-DMP's two legs (pooled t-test vs Mann-Whitney rank-sum) are genuinely different
    # statistical procedures that can clear an enrichment threshold by very different amounts —
    # this is an enrichment/threshold claim, so the honest agreement bar is "both legs
    # independently satisfy the claim's criterion" (both counts >= k), not numeric closeness on
    # the integer count. See CapabilityCell.agreement_mode / evaluate._check_agreement.
    agreement_mode="both_satisfy_criterion",
)

PHARMACO_ASSOC_CELL = CapabilityCell(
    capability_id="pharmaco::assoc", capability_version="v1", operation_impl="pharmaco::assoc",
    title="marker->drug tissue-adjusted association", pattern=_PATTERN,
    subject=SubjectRequirement(mode="required", kind="composite"),
    param_schema=(_STR(name="marker", codec="string"), _STR(name="drug", codec="string"),
                  _STR(name="group_col", codec="string")),
    produced=_Q, allowed_comparators=_ALL_CMP,
    eligible_adapter_identities=("pharmaco-meandiff", "pharmaco-rank"),
    oracle=OracleRequirement(default_oracle_id="gdsc_pharmaco_apparatus", required=True),
    data_ref_kind=DataRefKind.SE_CONTRACT, claim_leaf_kinds=("categorical",),
    criterion_target="threshold", agreement_mode="both_satisfy_criterion",
)

EXPRESSION_FLOOR_CELL = CapabilityCell(
    capability_id="expression::floor", capability_version="v1", operation_impl="expression::floor",
    title="group expression clears a floor", pattern=EXPRESSION_FLOOR,
    subject=SubjectRequirement(mode="required", kind="gene_or_protein"),
    param_schema=(_STR(name="gene", codec="string"), _STR(name="group_col", codec="string"),
                  _STR(name="level_a", codec="string"), _STR(name="level_b", codec="string")),
    produced=_Q, allowed_comparators=_ALL_CMP,
    eligible_adapter_identities=("expr-floor-mean", "expr-floor-hl"),
    oracle=OracleRequirement(default_oracle_id="expression_floor_apparatus", required=True),
    data_ref_kind=DataRefKind.SE_CONTRACT, claim_leaf_kinds=("quantity",),
    criterion_target="reference_leaf", agreement_mode="both_satisfy_criterion",
)

CAPABILITY_CELLS = CapabilityRegistry(cells=(
    MEAN_DIFF_CELL, REGION_DELTA_BETA_CELL, N_DMPS_CELL, EVAL_BENCHMARK_ADVANTAGE_CELL,
    PHARMACO_ASSOC_CELL, EXPRESSION_FLOOR_CELL,
))

# ---------------------------------------------------------------------------
# Phase 5 — typed trust bindings
# ---------------------------------------------------------------------------
from pydantic import Field, model_validator  # noqa: E402
from polymer_protocol import AdapterRegistry, OracleRegistry  # noqa: E402
from polymer_grammar.base import _Model  # noqa: E402
from polymer_grammar.capability import ConformanceReason, ConformanceResult, ConformanceWarning  # noqa: E402
from polymer_grammar.executor_credential import (  # noqa: E402
    ExecutorDescriptorRegistry, ExecutorTrustRegistry,
)
from polymer_grammar.evidence_policy import EvidencePolicyRegistry  # noqa: E402


class CapabilityTrustBinding(_Model):
    adapter_registry: AdapterRegistry
    oracle_registry: OracleRegistry
    trust_profile: str
    # V2.0 evidence-licensed capability fields.
    # Empty-registry defaults so the three pre-existing bindings construct unchanged (9th-review #9).
    evidence_policy_registry: EvidencePolicyRegistry = Field(
        default_factory=EvidencePolicyRegistry
    )
    executor_descriptor_registry: ExecutorDescriptorRegistry = Field(
        default_factory=ExecutorDescriptorRegistry
    )
    executor_trust_registry: ExecutorTrustRegistry = Field(
        default_factory=ExecutorTrustRegistry
    )

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
    from .pharmaco_adapters import pharmaco_independent_registry, pharmaco_oracle_registry

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
        ("eval::benchmark_advantage", "v1"): _benchmark_binding(),
        ("pharmaco::assoc", "v1"): CapabilityTrustBinding(
            adapter_registry=pharmaco_independent_registry(),
            oracle_registry=pharmaco_oracle_registry(),
            trust_profile="gdsc-pharmaco-recomputable-public"),
    }


def _benchmark_binding() -> "CapabilityTrustBinding":
    """Build the trust binding for eval::benchmark_advantage@v1 from the module-level kit."""
    from polymer_grammar.oracle import ApplicabilityDomain, OracleDossier, ValidationTier
    from polymer_protocol import AdapterRegistry
    from polymer_protocol.adapter_registry import AdapterCredential

    from .benchmark_capability import _BENCHMARK_KIT
    from .adapter_identity import implementation_hash_for_callable

    kit = _BENCHMARK_KIT

    # Adapter credential: one entry for "benchmark-model" (the executor's predictor identity)
    from ._fixtures.benchmark_dgp import DGPModelAdapter
    _model = DGPModelAdapter()
    _model.identity = "benchmark-model"
    benchmark_adapter_registry = AdapterRegistry(credentials=(
        AdapterCredential(
            identity="benchmark-model",
            owner="polymer-claims-dgp-v1",
            implementation_hash=implementation_hash_for_callable(_model.predict),
            trusted=True,
        ),
    ))

    # Oracle registry: unbounded apparatus (ApplicabilityDomain() has empty subject_kinds = unbounded)
    benchmark_oracle_registry = OracleRegistry(dossiers=(
        OracleDossier(
            oracle_id="benchmark_eval_apparatus",
            validation_tier=ValidationTier.BENCHMARKED,
            applicability_domain=ApplicabilityDomain(),  # empty = unbounded
        ),
    ))

    return CapabilityTrustBinding(
        adapter_registry=benchmark_adapter_registry,
        oracle_registry=benchmark_oracle_registry,
        trust_profile="bundled-benchmark-dgp-v1",
        evidence_policy_registry=kit.policy_registry,
        executor_descriptor_registry=kit.descriptor_registry,
        executor_trust_registry=kit.trust_registry,
    )


def bind(capability_id: str, capability_version: str = "v1") -> CapabilityTrustBinding:
    if CAPABILITY_CELLS.resolve(capability_id, capability_version) is None:
        raise CapabilityNotFound(f"{capability_id}@{capability_version} not registered")
    binding = _bindings().get((capability_id, capability_version))
    if binding is None:
        raise CapabilityNotFound(f"no trust binding for {capability_id}@{capability_version}")
    return binding


def validate_trust_binding(
    cell: CapabilityCell,
    adapter_registry: AdapterRegistry,
    oracle_registry: OracleRegistry,
    *,
    evidence_policy_registry: "EvidencePolicyRegistry | None" = None,
    executor_descriptor_registry: "ExecutorDescriptorRegistry | None" = None,
    executor_trust_registry: "ExecutorTrustRegistry | None" = None,
) -> ConformanceResult:
    vp = cell.verification_policy
    if vp is not None and vp.execution == "single":
        return _validate_single_mode(
            cell, adapter_registry, oracle_registry,
            evidence_policy_registry=evidence_policy_registry,
            executor_descriptor_registry=executor_descriptor_registry,
            executor_trust_registry=executor_trust_registry,
        )
    return _validate_recompute_pair_mode(cell, adapter_registry, oracle_registry)


def _validate_recompute_pair_mode(
    cell: CapabilityCell,
    adapter_registry: AdapterRegistry,
    oracle_registry: OracleRegistry,
) -> ConformanceResult:
    """Existing recompute-pair logic (unchanged)."""
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


def _validate_single_mode(
    cell: CapabilityCell,
    adapter_registry: AdapterRegistry,
    oracle_registry: OracleRegistry,
    *,
    evidence_policy_registry: "EvidencePolicyRegistry | None",
    executor_descriptor_registry: "ExecutorDescriptorRegistry | None",
    executor_trust_registry: "ExecutorTrustRegistry | None",
) -> ConformanceResult:
    """Single-mode trust binding validation (evidence-licensed capability).

    Skips the independent-pair requirement.  Requires:
    - EvidencePolicy resolvable from evidence_policy_registry and digest-verified.
    - ExecutorDescriptor resolvable via policy.executor_descriptor_ref.
    - ExecutorTrustEntry resolvable and trusted is True.
    - Descriptor's predictor component identity ∈ cell.eligible_adapter_identities.
    - Oracle id present in oracle_registry (unbounded apparatus; no subject in_domain check).
    """
    vp = cell.verification_policy
    reasons: list[ConformanceReason] = []
    warnings: list[ConformanceWarning] = []

    # Adapter credential warnings (informational only; no pair required in single mode)
    for ident in cell.eligible_adapter_identities:
        cred = adapter_registry.resolve(ident)
        if cred is None:
            warnings.append(ConformanceWarning.BINDING_ADAPTER_MISSING)
        elif not cred.trusted:
            warnings.append(ConformanceWarning.BINDING_ADAPTER_UNTRUSTED)

    # Oracle existence (unbounded apparatus — no subject in_domain check)
    if cell.oracle.required:
        oid = cell.oracle.default_oracle_id
        if oid is not None:
            if not any(d.oracle_id == oid for d in oracle_registry.dossiers):
                reasons.append(ConformanceReason.BINDING_ORACLE_MISSING)
        else:
            warnings.append(ConformanceWarning.BINDING_ORACLE_SATISFIABILITY_UNKNOWN)

    # Evidence policy: resolvable + digest-verified
    policy = None
    if (
        vp is None
        or vp.evidence_policy_ref is None
        or evidence_policy_registry is None
    ):
        reasons.append(ConformanceReason.BINDING_NO_INDEPENDENT_PAIR)
    else:
        policy = evidence_policy_registry.resolve(vp.evidence_policy_ref)
        if policy is None or policy.content_hash != vp.evidence_policy_ref:
            reasons.append(ConformanceReason.BINDING_NO_INDEPENDENT_PAIR)
            policy = None  # can't continue executor checks without a valid policy

    # Executor descriptor: resolvable via policy.executor_descriptor_ref
    descriptor = None
    if policy is not None:
        if executor_descriptor_registry is None:
            reasons.append(ConformanceReason.BINDING_NO_INDEPENDENT_PAIR)
        else:
            descriptor = executor_descriptor_registry.resolve(policy.executor_descriptor_ref)
            if descriptor is None:
                reasons.append(ConformanceReason.BINDING_NO_INDEPENDENT_PAIR)

    # Trust entry: resolvable and trusted
    if descriptor is not None:
        if executor_trust_registry is None:
            reasons.append(ConformanceReason.BINDING_NO_INDEPENDENT_PAIR)
        else:
            entry = executor_trust_registry.resolve(descriptor.content_hash)
            if entry is None or not entry.trusted:
                reasons.append(ConformanceReason.BINDING_NO_INDEPENDENT_PAIR)

    # Predictor identity eligibility: descriptor.predictor.identity ∈ cell.eligible_adapter_identities
    if descriptor is not None:
        predictor_comp = next(
            (c for c in descriptor.components if c.role == "predictor"), None
        )
        if (
            predictor_comp is None
            or predictor_comp.identity not in cell.eligible_adapter_identities
        ):
            reasons.append(ConformanceReason.BINDING_NO_INDEPENDENT_PAIR)

    return ConformanceResult(reasons=_dedup_local(reasons), warnings=_dedup_local(warnings))


def _dedup_local(items: list) -> tuple:
    seen, out = set(), []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return tuple(out)
